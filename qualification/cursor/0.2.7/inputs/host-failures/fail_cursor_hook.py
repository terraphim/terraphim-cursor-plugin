"""Disposable failure injector for actual native Cursor host qualification."""
import json
import os
from pathlib import Path
import signal
import sys
import time
import uuid

from observe_cursor_event import sanitise


def main():
    mode, directory = sys.argv[1:]
    if mode not in {"crash", "timeout", "empty", "nonzero"}:
        raise ValueError("unknown test mode")
    output = Path(directory)
    if not output.is_dir() or output.is_symlink() or output.stat().st_mode & 0o077:
        raise ValueError("private directory required")
    raw = sys.stdin.buffer.read(1024 * 1024 + 1)
    if len(raw) > 1024 * 1024:
        raise ValueError("oversized event")
    record = sanitise(json.loads(raw))
    record.update(failureMode=mode, observedUnixNs=time.time_ns(), pid=os.getpid())
    destination = output / (str(uuid.uuid4()) + ".json")
    fd = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as stream:
        json.dump(record, stream, indent=2)
        stream.flush()
        os.fsync(stream.fileno())
    if mode == "crash":
        os.kill(os.getpid(), signal.SIGKILL)
    if mode == "timeout":
        time.sleep(18)
    if mode == "nonzero":
        return 7
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
