"""Prepare finite, inactive public native inputs; never activate hooks or replay events."""

from pathlib import Path
import datetime
import importlib.util
import json
import os
import shlex
import subprocess
import sys
import time

sys.dont_write_bytecode = True
EVIDENCE = Path(__file__).resolve().parent
VALIDATION = EVIDENCE.parents[1]
HELPERS_PATH = VALIDATION / "hook-inputs/prepare.py"
spec = importlib.util.spec_from_file_location("existing_hook_preparation", HELPERS_PATH)
helpers = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helpers)
PROJECT = helpers.PROJECT
INPUTS = PROJECT / "qualification-inputs/warning-fixed-cases"
COMPILER = INPUTS / "compiler"
PYTHON = Path("/opt/homebrew/Caskroom/miniconda/base/bin/python3.12")
UNBOUND_ADAPTER = "/__ADMITTED_WARNING_FIXED_MAIN_CI_CANDIDATE__/integrations/cursor/hook_adapter.py"
EXPECTED_CANDIDATE = helpers.BASE / "__pending_warning_fixed_main_candidate__"


def protected_files():
    paths = [PROJECT / "brief.md", PROJECT / "validate_brief.py"]
    for directory in [PROJECT / ".cursor", PROJECT / "corpus", PROJECT / "outputs", helpers.PACKAGE]:
        paths.extend(p for p in directory.rglob("*") if p.is_file())
    return {str(p): helpers.identity(p) for p in paths}


def main():
    assert not INPUTS.exists(), "Never overwrite existing case inputs"
    before = protected_files()
    configs_before = {str(PROJECT / ".cursor" / name): (PROJECT / ".cursor" / name).exists() for name in ("hooks.json", "mcp.json")}
    assert not any(configs_before.values()), "Parent C09-clean fixture must stay inactive"
    assert helpers.identity(helpers.AGENT)["sha256"] == helpers.AGENT_SHA
    assert list((PROJECT / ".terraphim").iterdir()) == []
    helpers.private_directory(INPUTS)
    helpers.private_directory(COMPILER)
    cases = [
        {"name": "success", "output": "native-rewrite-warning-fixed.json", "evidence": True, "rewrite": True},
        {"name": "rewrite-off", "output": "native-rewrite-off-warning-fixed.json", "evidence": True, "rewrite": False},
        {"name": "denied-completion", "output": None, "evidence": True, "rewrite": True},
        {"name": "guard-original", "output": None, "evidence": True, "rewrite": True},
        {"name": "capture-off", "output": "native-capture-off-warning-fixed.json", "evidence": False, "rewrite": True},
        {"name": "parallel", "output": None, "evidence": True, "rewrite": False},
        {"name": "missing-completion", "output": "native-missing-post-warning-fixed.json", "evidence": True, "rewrite": True},
    ]
    report = {
        "startedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "status": "PREPARING_INACTIVE_UNBOUND_INPUTS",
        "source": "Existing hook-inputs prepare.py helpers and released-agent compiler workflow",
        "helperScript": helpers.identity(HELPERS_PATH),
        "agent": helpers.identity(helpers.AGENT),
        "expectedMainCommit": "PENDING_PARENT_ADMISSION",
        "expectedCandidatePath": str(EXPECTED_CANDIDATE),
        "candidateBinding": "PENDING_PARENT_ADMISSION_OF_ORIGINAL_MAIN_CI_ARCHIVE",
        "nativeAcceptance": "NOT_RUN",
        "cases": [],
    }
    for case in cases:
        name = case["name"]
        compiler = COMPILER / name
        destination = INPUTS / name
        helpers.private_directory(compiler)
        helpers.private_directory(compiler / ".terraphim")
        helpers.settings(compiler / "settings")
        helpers.private_directory(destination)
        helpers.settings(destination / "settings")
        helpers.private_directory(destination / "receipts")
        if case["output"]:
            original = f"python3 validate_brief.py --chek --output outputs/{case['output']}"
            corrected = original.replace("--chek", "--check")
            native_commands = [original]
        elif name in {"denied-completion", "guard-original"}:
            original = "printf '%s\\n' 'reviewed warning-fixed guard probe'"
            corrected = "printf '%s\\n' 'rm -rf /'"
            native_commands = [corrected if name == "guard-original" else original]
        else:
            original = "python3 -c 'import time; time.slep(1.7)'"
            corrected = "python3 -c 'import time; time.sleep(1.7)'"
            native_commands = [corrected, "python3 -c 'import time; time.sleep(0.2)'"]
        row = {
            "name": name, "nativeCommands": native_commands,
            "compiledOriginal": original, "compiledReplacement": corrected,
            "preparationCommands": [], "nativeStatus": "NOT_RUN",
        }
        report["cases"].append(row)
        env = {key: os.environ[key] for key in ("HOME", "USER", "LOGNAME", "LANG") if key in os.environ}
        env.update(PATH="/usr/bin:/bin:/usr/sbin:/sbin", TERRAPHIM_SETTINGS_PATH=str(compiler / "settings"))

        def run(label, args):
            argv = [str(helpers.AGENT), *map(str, args)]
            started = time.monotonic()
            result = subprocess.run(argv, cwd=compiler, env=env, capture_output=True, timeout=45)
            row["preparationCommands"].append({
                "label": label, "argv": argv, "cwd": str(compiler),
                "exitCode": result.returncode, "elapsedSeconds": time.monotonic() - started,
                "stdoutBytes": len(result.stdout), "stdoutSha256": helpers.digest(result.stdout),
                "stderrBytes": len(result.stderr), "stderrSha256": helpers.digest(result.stderr),
            })
            assert result.returncode == 0, f"{name}/{label}: actual compiler failed"
            return result.stdout

        guard = compiler / "guard-rules.json"
        run("empty-compile", ["learn", "compile", "--output", guard])
        assert json.loads(guard.read_bytes())["data"] == {}
        added = run("add-explicit-rule", [
            "learn", "correction", "add", "--original", original, "--corrected", corrected,
            "--correction-type", "tool-preference", "--context",
            "Reviewed isolated new-candidate native validation input; not executed during preparation.",
        ])
        notes = [line.removeprefix("Captured correction: ") for line in added.decode().splitlines()
                 if line.startswith("Captured correction: ")]
        assert len(notes) == 1
        note = Path(notes[0])
        assert note.resolve().is_relative_to(compiler / ".terraphim")
        rules = compiler / "compiled-corrections.json"
        run("compile", ["learn", "compile", "--output", rules])
        mapping = json.loads(rules.read_bytes())["data"]
        assert list(mapping) == [original]
        assert mapping[original]["nterm"] == corrected
        assert mapping[original]["display_value"] == corrected
        for path in [guard, rules]:
            target = destination / path.name
            target.write_bytes(path.read_bytes())
            target.chmod(0o600)
        (destination / "actual-correction.md").write_bytes(note.read_bytes())
        roles = json.loads((helpers.PACKAGE / "integrations/cursor/examples/role-config.json.example").read_bytes())
        for role, path in [("cursor-corrections", destination / rules.name), ("cursor-guard", destination / guard.name)]:
            roles["roles"][role]["kg"]["automata_path"]["Local"] = str(path)
        helpers.write_json(destination / "role-config.json", roles)
        policy = json.loads((helpers.PACKAGE / "integrations/cursor/policy.json.example").read_bytes())
        policy["projectRoot"] = str(PROJECT)
        policy["agent"] = {"path": str(helpers.AGENT), "sha256": helpers.AGENT_SHA}
        for key, path in [("roleConfig", destination / "role-config.json"),
                          ("compiledRules", destination / rules.name), ("guardRules", destination / guard.name)]:
            policy[key] = {"path": str(path), "sha256": helpers.identity(path)["sha256"]}
        policy["startupSettings"] = {
            "directory": str(destination / "settings"),
            "settingsSha256": helpers.identity(destination / "settings/settings.toml")["sha256"],
        }
        policy["rewriteEnabled"] = case["rewrite"]
        policy["captureFailures"] = False
        outputs = [str(PROJECT / "outputs" / case["output"])] if case["output"] else []
        policy["evidence"] = {"enabled": False}
        if case["evidence"]:
            policy["evidence"] = {"enabled": True, "directory": str(destination / "receipts"), "outputFiles": outputs}
        helpers.write_json(destination / "policy.json", policy)
        policy_hash = helpers.identity(destination / "policy.json")["sha256"]
        events = ["preToolUse"] if name == "missing-completion" else ["preToolUse", "postToolUse", "postToolUseFailure"]
        hooks = {"version": 1, "hooks": {}}
        for event in events:
            argv = [str(PYTHON), UNBOUND_ADAPTER, "--policy", str(destination / "policy.json"),
                    "--policy-sha256", policy_hash, "--event", event]
            hooks["hooks"][event] = [{"command": shlex.join(argv), "matcher": "Shell", "timeout": 15, "failClosed": True}]
        helpers.write_json(destination / "hooks.entries.UNBOUND.json.example", hooks)
        assert all(not Path(output).exists() for output in outputs)
        assert not list((destination / "receipts").iterdir())
        row.update({
            "policy": helpers.identity(destination / "policy.json"),
            "unboundHookTemplate": helpers.identity(destination / "hooks.entries.UNBOUND.json.example"),
            "manualSelectedOutputPaths": outputs,
            "receiptDirectory": str(destination / "receipts"), "receiptDirectoryEmpty": True,
            "captureFailures": False, "evidenceEnabled": case["evidence"],
            "hooksIncluded": events, "targetCommandsExecuted": False,
            "compiledRuleNote": helpers.identity(destination / "actual-correction.md"),
        })
    after = protected_files()
    report.update({
        "status": "PASS_INACTIVE_INPUT_PREPARATION_UNBOUND",
        "finishedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "preExistingProtectedFiles": before,
        "concurrentProtectedChangesObserved": [path for path in sorted(set(before) | set(after)) if before.get(path) != after.get(path)],
        "preparationWroteOnly": [str(INPUTS), str(EVIDENCE)],
        "activeConfigurationWritten": False, "hookEventsReplayed": False,
        "activeConfigExistenceBefore": configs_before,
        "activeConfigExistenceAfter": {path: Path(path).exists() for path in configs_before},
        "homeAndCodexHomeChanged": False,
        "projectDiscoveryStillEmpty": not list((PROJECT / ".terraphim").iterdir()),
    })
    assert report["projectDiscoveryStillEmpty"]
    assert report["activeConfigExistenceBefore"] == report["activeConfigExistenceAfter"]
    helpers.write_json(EVIDENCE / "preparation-receipt.json", report)
    print(json.dumps({"status": report["status"], "cases": len(cases),
                      "actualCompilerCommands": sum(len(c["preparationCommands"]) for c in report["cases"]),
                      "concurrentProtectedChangesObserved": report["concurrentProtectedChangesObserved"]}))


if __name__ == "__main__":
    main()
