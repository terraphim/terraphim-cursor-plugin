#!/usr/bin/env python3
"""Exercise C-05 using unchanged released clients and fresh explicit stores.

This is an evidence harness, not a plugin or a native Cursor acceptance claim.
Each invocation refuses an existing root. It never sets HOME/CODEX_HOME.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import time

AGENT_SHA256 = "bff31dc42d6d1a99bf51291039d7719c6a48c2326e582e5e24eaa1eaf11e17ec"
GREP_SHA256 = "95491857b6a115ce7f4ec2a9d24bd0f7b8efcc1a52bd1403b34a62dd704012ab"
CONTENT = "Risk requires a Decision: approve a second supplier as the mitigation."
TAG = "public-project-brief"
ORIGINAL = "python3 validate_brief.py --chek --output outputs/native-rewrite.json"
CORRECTED = "python3 validate_brief.py --check --output outputs/native-rewrite.json"
BRIEF = b"# Public project brief\n\nRisk: supplier delays require a backup plan.\nDecision: approve a second supplier.\n"
VALIDATOR = '''"""Harmless public validator; no model or network operation."""
import argparse
import hashlib
import json
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("--check", action="store_true", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source = Path(__file__).with_name("brief.md")
    data = source.read_bytes()
    text = data.decode("utf-8")
    if "Risk" not in text or "Decision" not in text:
        parser.error("brief requires Risk and Decision")
    result = {"source": source.name, "sha256": hashlib.sha256(data).hexdigest(),
              "bytes": len(data), "riskOccurrences": text.count("Risk"),
              "decisionOccurrences": text.count("Decision")}
    with args.output.open("x") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\\n")

if __name__ == "__main__":
    main()
'''


def digest(data):
    return hashlib.sha256(data).hexdigest()


def file_identity(path):
    data = path.read_bytes()
    return {"path": str(path), "bytes": len(data), "sha256": digest(data)}


def write_json(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False)
        stream.write("\n")


def assert_released_binary(path, expected):
    if path.is_symlink() or not path.is_file() or not os.access(path, os.X_OK):
        raise ValueError("Release binary must be an executable regular file")
    identity = file_identity(path)
    if identity["sha256"] != expected:
        raise ValueError("Release executable digest mismatch")
    return identity


def qualify(root, agent, grep, output_name="native-rewrite.json"):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,100}\.json", output_name):
        raise ValueError("Output name must be a bounded plain JSON filename")
    original = ORIGINAL.replace("native-rewrite.json", output_name)
    corrected = CORRECTED.replace("native-rewrite.json", output_name)
    if not root.is_absolute() or root.exists() or root.is_symlink():
        raise ValueError("Choose a fresh nonexistent absolute qualification root")
    if root.parent.resolve() != root.parent:
        raise ValueError("Qualification parent must be canonical, without symlink components")
    agent_id = assert_released_binary(agent, AGENT_SHA256)
    grep_id = assert_released_binary(grep, GREP_SHA256)
    python = Path(shutil.which("python3") or "").resolve(strict=True)
    if not python.is_file():
        raise ValueError("python3 is unavailable")
    root.mkdir(mode=0o700)
    project, output = root / "project", root / "outputs"
    settings, memory = root / "settings", root / "memory"
    for path in (project, output, settings, memory, project / ".terraphim",
                 project / "outputs", settings / "data", settings / "dashmap"):
        path.mkdir(mode=0o700)
    (project / "brief.md").write_bytes(BRIEF)
    (project / "validate_brief.py").write_text(VALIDATOR, encoding="utf-8")
    settings_file = settings / "settings.toml"
    settings_file.write_text(
        'server_hostname = "127.0.0.1:8000"\n'
        'api_endpoint = "http://localhost:8000/api"\ninitialized = "true"\n'
        f'default_data_path = {json.dumps(str(settings / "data"))}\n'
        '[profiles.dashmap]\ntype = "dashmap"\n'
        f'root = {json.dumps(str(settings / "dashmap"))}\n', encoding="utf-8")
    settings_file.chmod(0o600)
    inputs = [file_identity(p) for p in (project / "brief.md", project / "validate_brief.py", settings_file)]
    # Inherit original identity values unchanged; admit no provider/storage overrides.
    env = {k: os.environ[k] for k in ("HOME", "USER", "LOGNAME", "LANG") if k in os.environ}
    env.update({"PATH": str(python.parent) + ":/usr/bin:/bin:/usr/sbin:/sbin",
                "TERRAPHIM_SETTINGS_PATH": str(settings)})
    receipt = {
        "status": "RUNNING", "startedAt": datetime.now(timezone.utc).isoformat(),
        "scope": "Fresh released CLI component execution; not native Cursor or hook activation",
        "requirements": ["C-05/CUR-05"], "host": platform.platform(),
        "root": str(root), "binaryInputs": {"agent": agent_id, "grep": grep_id},
        "python": file_identity(python), "inputs": inputs, "commands": [],
        "storage": {"settingsDirectory": str(settings), "backend": "dashmap",
                    "memoryDataOverride": str(memory), "learningProject": str(project / ".terraphim"),
                    "homeAndCodexHomeModified": False,
                    "inheritedEnvironmentNames": sorted(k for k in env if k != "TERRAPHIM_SETTINGS_PATH"),
                    "memoryOverrideUsedOnlyForMemoryCommands": True},
        "privacy": "Only public fixture argv/status and explicitly selected CLI/learning/output files; no environment values or general diagnostic logs",
    }

    def run(name, argv, *, memory_mode=False, selected_stdout=None, expected=0):
        child_env = dict(env)
        if memory_mode:
            child_env["TERRAPHIM_DEFAULT_DATA_PATH"] = str(memory)
        row = {"name": name, "argv": [str(x) for x in argv], "cwd": str(project),
               "startedAt": datetime.now(timezone.utc).isoformat(), "memoryOverride": memory_mode}
        receipt["commands"].append(row)
        started = time.monotonic()
        try:
            result = subprocess.run(row["argv"], cwd=project, env=child_env,
                                    capture_output=True, timeout=45, check=False)
        except subprocess.TimeoutExpired as exc:
            row.update({"status": "TIMEOUT", "elapsedSeconds": time.monotonic() - started,
                        "stdoutSha256": digest(exc.stdout or b""), "stderrSha256": digest(exc.stderr or b"")})
            raise AssertionError(f"{name} exceeded 45-second qualification limit") from exc
        row.update({"exitCode": result.returncode, "elapsedSeconds": time.monotonic() - started,
                    "stdoutBytes": len(result.stdout), "stdoutSha256": digest(result.stdout),
                    "stderrBytes": len(result.stderr), "stderrSha256": digest(result.stderr)})
        if selected_stdout:
            selected = output / selected_stdout
            selected.write_bytes(result.stdout)
            row["selectedOutput"] = file_identity(selected)
        if result.returncode != expected:
            raise AssertionError(f"{name}: expected exit {expected}, observed {result.returncode}; diagnostics digests retained")
        return result

    def agent_run(name, args, **kwargs):
        return run(name, [agent, *args], **kwargs)

    def reported_path(data, prefix):
        matches = [line[len(prefix):] for line in data.decode("utf-8").splitlines() if line.startswith(prefix)]
        assert len(matches) == 1, "Expected one actual CLI-created file path"
        path = Path(matches[0])
        assert path.resolve().is_relative_to(project / ".terraphim"), "Learning escaped explicit project"
        assert path.is_file() and not path.is_symlink()
        return path

    try:
        assert agent_run("agent-version", ["--version"], selected_stdout="agent-version.txt").stdout.strip() == b"terraphim-agent 1.21.20"
        assert run("grep-version", [grep, "--version"], selected_stdout="grep-version.txt").stdout.strip() == b"terraphim-grep 1.21.20"
        baseline = json.loads(agent_run("memory-baseline", ["--format", "json", "memory", "list"],
            memory_mode=True, selected_stdout="memory-baseline.json").stdout)
        assert baseline["status"] == "ok" and baseline["count"] == 0 and baseline["items"] == []
        captured = json.loads(agent_run("memory-capture", ["--format", "json", "memory", "capture",
            "--content", CONTENT, "--provenance-tag", TAG], memory_mode=True,
            selected_stdout="captured-memory.json").stdout)
        assert captured["status"] == "ok"
        memory_id = captured["memory_id"]
        shown = json.loads(agent_run("memory-show-new-process", ["memory", "show", memory_id, "--json"],
            memory_mode=True, selected_stdout="saved-memory.json").stdout)
        assert shown["status"] == "ok" and shown["id"] == memory_id
        assert shown["memory_item"]["id"] == memory_id and shown["memory_item"]["content"] == CONTENT
        assert shown["memory_item"]["tags"] == ["provenance:" + TAG]
        store = memory / "terraphim/evolution/cli-agent.json"
        json.loads(store.read_text())
        assert memory_id in store.read_text() and CONTENT in store.read_text()
        assert not (project / ".terraphim/learnings").exists()

        actual_failure = run("actual-validator-failure", ["/bin/sh", "-c", original], expected=2)
        assert b"--check" in actual_failure.stderr and b"required" in actual_failure.stderr
        assert not (project / "outputs" / output_name).exists()
        capture = agent_run("learn-capture", ["learn", "capture", "--error", actual_failure.stderr.decode("utf-8"),
            "--exit-code", str(actual_failure.returncode), original], selected_stdout="learning-path.txt")
        learning = reported_path(capture.stdout, "Captured learning: ")
        before = learning.read_bytes()
        (output / "learning-before-annotation.md").write_bytes(before)
        assert original in before.decode() and "source: Project" in before.decode() and "exit_code: 2" in before.decode()
        learning_id = re.search(r"^id: ([^\n]+)$", before.decode(), re.M).group(1)
        query = agent_run("learn-query", ["learn", "query", original, "--exact"], selected_stdout="learning-query.txt")
        assert b"[P] [cmd]" in query.stdout and original.encode() in query.stdout and b"(exit: 2)" in query.stdout
        assert re.search(r"^id: ([^\n]+)$", learning.read_text(), re.M).group(1) == learning_id
        agent_run("annotate-failure", ["learn", "correct", learning_id, "--correction", corrected])
        annotated = learning.read_bytes()
        (output / "learning-after-annotation.md").write_bytes(annotated)
        assert corrected in annotated.decode() and before != annotated
        before_compiled = output / "compiled-before-rule.json"
        agent_run("compile-annotation-only", ["learn", "compile", "--output", before_compiled])
        assert json.loads(before_compiled.read_text())["data"] == {}
        rule_result = agent_run("add-explicit-reviewed-rule", ["learn", "correction", "add", "--original", original,
            "--corrected", corrected, "--correction-type", "tool-preference", "--context",
            "Reviewed public validator fixture: the required option is --check; keep the chosen output path unchanged."],
            selected_stdout="correction-path.txt")
        rule = reported_path(rule_result.stdout, "Captured correction: ")
        assert original in rule.read_text() and corrected in rule.read_text()
        after_compiled = output / "compiled-reviewed-corrections.json"
        agent_run("compile-reviewed-rule", ["learn", "compile", "--output", after_compiled])
        mappings = json.loads(after_compiled.read_text())["data"]
        assert len(mappings) == 1 and original in mappings
        exact_replacement = mappings[original]["display_value"]
        assert exact_replacement == corrected
        kg = output / "reviewed-kg"
        agent_run("export-reviewed-kg", ["learn", "export-kg", "--output", kg])
        notes = sorted(kg.glob("*.md"))
        assert len(notes) == 1
        note = notes[0].read_text()
        assert "synonyms:: " + original in note and corrected in note
        run("execute-exact-compiled-replacement", ["/bin/sh", "-c", exact_replacement])
        actual_file = project / "outputs" / output_name
        actual = json.loads(actual_file.read_text())
        assert actual == {"source": "brief.md", "sha256": digest(BRIEF), "bytes": len(BRIEF),
                          "riskOccurrences": 1, "decisionOccurrences": 1}
        assert (project / "brief.md").read_bytes() == BRIEF
        assert settings_file.read_bytes() and file_identity(settings_file) == inputs[2]
        assert assert_released_binary(agent, AGENT_SHA256) == agent_id
        assert assert_released_binary(grep, GREP_SHA256) == grep_id
        receipt.update({"status": "PASS", "memoryId": memory_id, "memoryContent": CONTENT,
            "memoryTag": "provenance:" + TAG, "actualMemoryStore": file_identity(store),
            "learningId": learning_id, "actualLearningPath": str(learning), "actualCorrectionPath": str(rule),
            "annotationOnlyCompiledCount": 0, "explicitRuleCompiledCount": len(mappings),
            "originalCommand": original, "exactCompiledExecutedReplacement": exact_replacement,
            "failureExit": actual_failure.returncode, "validatorOutput": actual,
            "activation": False, "nativeCursor": "NOT_RUN"})
    except Exception as exc:
        receipt.update({"status": "FAIL", "failureType": type(exc).__name__, "failure": str(exc)})
        raise
    finally:
        receipt["finishedAt"] = datetime.now(timezone.utc).isoformat()
        receipt["files"] = [file_identity(p) for p in sorted(root.rglob("*")) if p.is_file()]
        receipt["harness"] = file_identity(Path(__file__).resolve())
        write_json(root / "receipt.json", receipt)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--agent", required=True, type=Path)
    parser.add_argument("--grep", required=True, type=Path)
    parser.add_argument("--output-name", default="native-rewrite.json")
    args = parser.parse_args()
    result = qualify(args.root, args.agent, args.grep, args.output_name)
    print(json.dumps({"status": result["status"], "receipt": str(args.root / "receipt.json"),
                      "commands": len(result["commands"]), "nativeCursor": "NOT_RUN"}))


if __name__ == "__main__":
    main()
