"""Disposable native host-response probe; deliberately not a Terraphim adapter."""
import json
import os
from pathlib import Path
import sys
import time
import uuid

PROJECT = "/private/tmp/terraphim-cursor-validation-20261016/public-project"
COMMANDS = {
    "no-output": "python3 validate_brief.py --check --output outputs/native-host-no-output.json",
    "malformed-response": "python3 validate_brief.py --check --output outputs/native-host-malformed-response.json",
}


def main():
    mode, destination = sys.argv[1:]
    if mode not in COMMANDS:
        raise ValueError("unknown probe mode")
    directory = Path(destination)
    if not directory.is_dir() or directory.is_symlink() or directory.stat().st_mode & 0o077:
        raise ValueError("private existing directory required")
    raw = sys.stdin.buffer.read(1024 * 1024 + 1)
    if len(raw) > 1024 * 1024:
        raise ValueError("oversized event")
    event = json.loads(raw)
    if (event.get("hook_event_name") != "preToolUse"
        or event.get("tool_name") != "Shell"
        or event.get("cwd") != PROJECT
        or event.get("tool_input", {}).get("command") != COMMANDS[mode]):
        raise ValueError("not the explicitly prepared public probe")
    record = {key: event[key] for key in (
        "hook_event_name", "cursor_version", "conversation_id", "generation_id",
        "tool_use_id", "tool_name", "cwd",
    ) if key in event}
    record.update(command=COMMANDS[mode], failureMode=mode, observedUnixNs=time.time_ns(),
                  injectedExitCode=0, injectedResponse="empty" if mode == "no-output" else "invalid JSON")
    target = directory / (str(uuid.uuid4()) + ".json")
    descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w") as stream:
        json.dump(record, stream, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    if mode == "malformed-response":
        sys.stdout.write("this is deliberately invalid hook JSON\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
