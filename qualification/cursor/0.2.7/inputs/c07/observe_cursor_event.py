"""Disposable native-host probe; never retain transcripts or general tool output."""
import json
import os
from pathlib import Path
import sys
import time
import uuid


def shape(value, depth=0):
    """Record field types, with numeric process exits as the only result values."""
    if depth > 6:
        return "depth_limit"
    if isinstance(value, dict):
        return {
            key: child if key in {"exitCode", "exit_code", "code"} and type(child) is int
            else shape(child, depth + 1)
            for key, child in value.items()
        }
    if isinstance(value, list):
        return [shape(child, depth + 1) for child in value[:4]]
    return type(value).__name__


def sanitise(event):
    """Keep correlation IDs, public commands, status and shape without output text."""
    result = {key: event[key] for key in (
        "hook_event_name", "cursor_version", "conversation_id", "generation_id",
        "tool_use_id", "tool_name", "cwd", "workspace_roots",
    ) if key in event}
    tool_input = event.get("tool_input", {})
    result["inputShape"] = shape(tool_input)
    if isinstance(tool_input, dict) and isinstance(tool_input.get("command"), str):
        result["command"] = tool_input["command"]
    result["outerShape"] = shape(event)
    if isinstance(event.get("tool_output"), str):
        try:
            result["resultShape"] = shape(json.loads(event["tool_output"]))
        except (ValueError, RecursionError):
            result["resultShape"] = "not_json"
    return result


def main():
    raw = sys.stdin.buffer.read(1024 * 1024 + 1)
    if len(raw) > 1024 * 1024:
        raise ValueError("oversized event")
    event = json.loads(raw)
    output = Path(sys.argv[1])
    if not output.is_dir() or output.is_symlink() or output.stat().st_mode & 0o077:
        raise ValueError("private existing observation directory required")
    record = sanitise(event)
    record["observedUnixNs"] = time.time_ns()
    path = output / (str(uuid.uuid4()) + ".json")
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w") as stream:
        json.dump(record, stream, indent=2)
        stream.write("\n")
    print(json.dumps({"permission": "allow"} if event.get("hook_event_name") == "preToolUse" else {}))


if __name__ == "__main__":
    main()
