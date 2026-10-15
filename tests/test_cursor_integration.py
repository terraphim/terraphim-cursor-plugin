"""Cursor admission tests use actual files/processes; released CLI tests are explicit."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "cursor_hook_adapter", ROOT / "integrations/cursor/hook_adapter.py"
)
assert SPEC and SPEC.loader
A = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(A)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class JsonContracts(unittest.TestCase):
    def test_actual_json_boundaries(self):
        self.assertEqual(A.decode_json(b'{"a":[1,true,null]}'), {"a": [1, True, None]})
        for raw in [
            b"{}{}",
            b'{"a":1,"a":2}',
            b'{"a":NaN}',
            b'{"a":1e999}',
            b"[]",
            b"\xff",
            b"{",
        ]:
            with self.subTest(raw=raw), self.assertRaises(A.Refusal):
                A.decode_json(raw)
        self.assertEqual(A.decode_json(b"{}" + b" " * (A.MAX_BYTES - 2)), {})
        with self.assertRaises(A.Refusal):
            A.decode_json(b"{}" + b" " * (A.MAX_BYTES - 1))
        nested = {}
        for _ in range(31):
            nested = {"a": nested}
        self.assertEqual(A.decode_json(json.dumps(nested).encode()), nested)
        with self.assertRaisesRegex(A.Refusal, "json_depth"):
            A.decode_json(json.dumps({"a": nested}).encode())

    def test_command_limits_are_utf8_bytes(self):
        self.assertEqual(A.command("x" * 16384), "x" * 16384)
        for value in ["", True, "x" * 16385, "東" * 5462, "x\x00y"]:
            with self.subTest(value=type(value)), self.assertRaises(A.Refusal):
                A.command(value)

    def test_full_extra_tool_input_preserved_and_outer_metadata_excluded(self):
        tool = {
            "command": "printf ok",
            "working_directory": "/project",
            "nested": {"flag": True},
        }
        envelope = A.cli_envelope(tool)
        self.assertEqual(envelope, {"tool_name": "Bash", "tool_input": tool})
        output = copy.deepcopy(envelope)
        output["tool_input"]["command"] = "printf corrected"
        output["warnings"] = ["actual CLI may include a warning"]
        self.assertEqual(A.agent_command(output, tool), "printf corrected")
        output["tool_input"]["nested"]["flag"] = 1
        with self.assertRaises(A.Refusal):
            A.agent_command(output, tool)

    def test_deny_envelope_and_unexpected_outputs(self):
        denial = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": "bounded",
            }
        }
        with self.assertRaisesRegex(A.Refusal, "agent_denied"):
            A.agent_command(denial, {"command": "printf ok"})
        for value in [
            {},
            {"tool_name": "Other", "tool_input": {"command": "x"}},
            {"tool_name": "Bash", "tool_input": {"command": "x"}, "extra": 1},
        ]:
            with self.subTest(value=value), self.assertRaises(A.Refusal):
                A.agent_command(value, {"command": "x"})

    def test_display_value_is_only_exact_attribution(self):
        data = {
            "printf old": {
                "id": 1,
                "nterm": "printf new",
                "display_value": "printf New",
                "pinned": False,
            }
        }
        self.assertEqual(
            A.attributed_command(data, "printf old", "printf New"), "printf New"
        )
        for original, result in [
            ("printf OLD", "printf New"),
            ("printf old extra", "printf New"),
            ("printf old", "printf new"),
        ]:
            with self.subTest(original=original), self.assertRaises(A.Refusal):
                A.attributed_command(data, original, result)
        for bad in [{"id": True}, {"display_value": None}, {"extra": 3}]:
            value = copy.deepcopy(data)
            value["printf old"].update(bad)
            with self.assertRaises(A.Refusal):
                A.validate_rules({"name": "rules", "data": value}, empty=False)

    def test_misrouted_event_is_refused_before_policy(self):
        with self.assertRaisesRegex(A.Refusal, "event_mismatch"):
            A.handle_event(
                {"hook_event_name": "postToolUse", "tool_name": "Shell"},
                "preToolUse",
                "/absent",
                "0" * 64,
            )

    def test_non_shell_passes_without_policy_or_process(self):
        self.assertEqual(
            A.handle_event({"tool_name": "Read"}, "preToolUse", "/absent", "0" * 64),
            {"permission": "allow"},
        )
        self.assertEqual(
            A.handle_event({"tool_name": "Read"}, "postToolUse", "/absent", "0" * 64),
            {},
        )
        with self.assertRaises(A.Refusal):
            A.handle_event({}, "preToolUse", "/absent", "0" * 64)


class FilesAndProcesses(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="cursor-adapter-")
        self.root = Path(self.temp.name).resolve()

    def tearDown(self):
        self.temp.cleanup()

    def test_receipt_selected_file_size_and_terminal_conflict(self):
        evidence = self.root / "evidence"
        evidence.mkdir(mode=0o700)
        store = A.ReceiptStore(evidence, "a" * 64)
        event = {
            "conversation_id": "c",
            "generation_id": "g",
            "tool_use_id": "too-large",
        }
        output = self.root / "large"
        record = store.begin(event, "printf x", [str(output)], {})
        store.applied(record, "printf x")
        output.write_bytes(b"x" * (A.MAX_BYTES + 1))
        with self.assertRaises(A.Refusal):
            store.complete(event, "printf x", 0)
        before = store.path(event).read_bytes()
        with self.assertRaises(A.Refusal):
            store.complete(event, "printf x", 0)
        self.assertEqual(store.path(event).read_bytes(), before)

    def test_symlinks_and_traversal_refused(self):
        target = self.root / "data"
        target.write_bytes(b"actual")
        (self.root / "link").symlink_to(target)
        self.assertEqual(A.read_regular(str(target)), b"actual")
        for path in [
            str(self.root / "link"),
            str(self.root) + "/./data",
            str(self.root) + "/../data",
        ]:
            with self.subTest(path=path), self.assertRaises(A.Refusal):
                A.read_regular(path)

    def test_environment_drops_injection_provider_and_storage_overrides(self):
        parent = {
            "HOME": "/home/original",
            "PATH": "/unsafe",
            "OPENROUTER_API_KEY": "not-a-secret-test-marker",
            "TERRAPHIM_DEFAULT_DATA_PATH": "/outside",
            "LD_PRELOAD": "/outside",
            "USER": "private-name",
        }
        env = A.child_environment(str(self.root), parent)
        self.assertEqual(env["HOME"], parent["HOME"])
        self.assertEqual(env["TERRAPHIM_SETTINGS_PATH"], str(self.root))
        self.assertNotIn("USER", env)
        self.assertNotIn("OPENROUTER_API_KEY", env)
        self.assertNotIn("TERRAPHIM_DEFAULT_DATA_PATH", env)
        self.assertNotIn("LD_PRELOAD", env)
        self.assertNotEqual(env["PATH"], "/unsafe")

    def test_real_os_process_input_output_and_nonzero(self):
        self.assertEqual(
            A.run_child(
                ["/bin/cat"], b"actual bytes", self.root, {"PATH": "/usr/bin:/bin"}, 2
            ),
            b"actual bytes",
        )
        with self.assertRaisesRegex(A.Refusal, "agent_exit"):
            A.run_child(
                ["/usr/bin/false"], b"", self.root, {"PATH": "/usr/bin:/bin"}, 2
            )

    def test_real_timeout_and_output_overflow(self):
        start = time.monotonic()
        with self.assertRaisesRegex(A.Refusal, "agent_timeout"):
            A.run_child(
                ["/bin/sleep", "2"], b"", self.root, {"PATH": "/usr/bin:/bin"}, 0.15
            )
        self.assertLess(time.monotonic() - start, 1.5)
        with self.assertRaisesRegex(A.Refusal, "agent_output_limit"):
            A.run_child(["/usr/bin/yes"], b"", self.root, {"PATH": "/usr/bin:/bin"}, 2)

    def test_real_blocked_stdin_is_bounded(self):
        with self.assertRaisesRegex(A.Refusal, "agent_timeout"):
            A.run_child(
                ["/bin/sleep", "2"],
                b"x" * A.MAX_BYTES,
                self.root,
                {"PATH": "/usr/bin:/bin"},
                0.15,
            )

    def test_receipts_do_not_persist_general_output_and_require_fresh_selected_file(
        self,
    ):
        evidence = self.root / "evidence"
        evidence.mkdir(mode=0o700)
        out = self.root / "selected.txt"
        event = {
            "conversation_id": "conversation",
            "generation_id": "generation",
            "tool_use_id": "tool",
        }
        store = A.ReceiptStore(evidence, "a" * 64)
        rec = store.begin(event, "printf original", [str(out)], {"agent": "b" * 64})
        store.applied(rec, "printf applied")
        out.write_text("actual output\n")
        done = store.complete(event, "printf applied", 0)
        self.assertEqual(done["state"], "completed")
        self.assertEqual(done["artifacts"][0]["sha256"], digest(out))
        self.assertNotIn("stdout", json.dumps(done))
        self.assertEqual(store.complete(event, "printf applied", 0), done)
        with self.assertRaises(A.Refusal):
            store.begin(event, "duplicate", [], {})
        before = store.path(event).read_bytes()
        with self.assertRaises(A.Refusal):
            store.complete(event, "foreign command", 0)
        self.assertEqual(store.path(event).read_bytes(), before)

    def test_collision_foreign_and_lock_conflicts_never_overwrite(self):
        evidence = self.root / "evidence"
        evidence.mkdir(mode=0o700)
        store = A.ReceiptStore(evidence, "a" * 64)
        event = {
            "conversation_id": "c",
            "generation_id": "g",
            "tool_use_id": "../unsafe",
        }
        out = self.root / "selected.txt"
        out.write_text("existing")
        with self.assertRaises(A.Refusal):
            store.begin(event, "x", [str(out)], {})
        self.assertEqual(out.read_text(), "existing")
        rec = store.begin(event, "x", [], {})
        self.assertEqual(store.path(event).parent, evidence)
        lock = store.path(event).with_suffix(".lock")
        lock.write_text("busy")
        lock.chmod(0o600)
        before = store.path(event).read_bytes()
        with self.assertRaises(A.Refusal):
            store.applied(rec, "x")
        self.assertEqual(store.path(event).read_bytes(), before)
        self.assertEqual(A.decode_json(before)["state"], "prepared")

    def test_unrelated_evidence_content_is_refused(self):
        evidence = self.root / "evidence"
        evidence.mkdir(mode=0o700)
        (evidence / "unrelated.txt").write_text("preserve")
        with self.assertRaises(A.Refusal):
            A.ReceiptStore(evidence, "a" * 64)
        self.assertEqual((evidence / "unrelated.txt").read_text(), "preserve")

    def test_missing_selected_output_is_incomplete_not_success(self):
        evidence = self.root / "evidence"
        evidence.mkdir(mode=0o700)
        store = A.ReceiptStore(evidence, "a" * 64)
        event = {"conversation_id": "c", "generation_id": "g", "tool_use_id": "t"}
        rec = store.begin(event, "printf x", [str(self.root / "absent")], {})
        store.applied(rec, "printf x")
        with self.assertRaises(A.Refusal):
            store.complete(event, "printf x", 0)
        self.assertEqual(store.read(store.key(event))["state"], "incomplete")

    def test_post_without_pre_creates_no_marker_or_record(self):
        evidence = self.root / "evidence"
        evidence.mkdir(mode=0o700)
        with self.assertRaises(A.Refusal):
            A.ReceiptStore(evidence, "a" * 64, create=False)
        self.assertEqual(list(evidence.iterdir()), [])

    def test_selected_output_symlink_is_incomplete(self):
        evidence = self.root / "evidence"
        evidence.mkdir(mode=0o700)
        store = A.ReceiptStore(evidence, "a" * 64)
        event = {"conversation_id": "c", "generation_id": "g", "tool_use_id": "t"}
        out = self.root / "selected"
        actual = self.root / "other"
        actual.write_text("retain")
        rec = store.begin(event, "printf x", [str(out)], {})
        store.applied(rec, "printf x")
        out.symlink_to(actual)
        with self.assertRaises(A.Refusal):
            store.complete(event, "printf x", 0)
        self.assertEqual(store.read(store.key(event))["state"], "incomplete")
        self.assertEqual(actual.read_text(), "retain")

    def test_killed_partial_write_does_not_hide_existing_recovery_records(self):
        evidence = self.root / "evidence"
        evidence.mkdir(mode=0o700)
        store = A.ReceiptStore(evidence, "a" * 64)
        event = {"conversation_id": "c", "generation_id": "g", "tool_use_id": "partial"}
        record = store.begin(event, "printf original", [], {})
        temporary = evidence / (store.key(event) + "." + "b" * 32 + ".tmp")
        child = subprocess.run(
            [
                sys.executable,
                "-c",
                'import os,signal,sys; f=open(sys.argv[1],"wb"); os.chmod(sys.argv[1],0o600); f.write(b"{partial"); f.flush(); os.fsync(f.fileno()); os.kill(os.getpid(),signal.SIGKILL)',
                str(temporary),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=5,
        )
        self.assertEqual(child.returncode, -9)
        before = {p.name: p.read_bytes() for p in evidence.iterdir()}
        recovered = A.ReceiptStore(evidence, "a" * 64, create=False).unfinished()
        self.assertTrue(
            any(row.get("recordId") == record["recordId"] for row in recovered)
        )
        self.assertTrue(
            any(row.get("reason") == "interrupted_atomic_write" for row in recovered)
        )
        self.assertEqual(before, {p.name: p.read_bytes() for p in evidence.iterdir()})

    def test_unfinished_inspection_preserves_crashed_and_terminal_bytes(self):
        evidence = self.root / "evidence"
        evidence.mkdir(mode=0o700)
        store = A.ReceiptStore(evidence, "a" * 64)
        e1 = {"conversation_id": "c", "generation_id": "g", "tool_use_id": "first"}
        e2 = {**e1, "tool_use_id": "second"}
        e3 = {**e1, "tool_use_id": "third"}
        r1 = store.begin(e1, "printf first", [], {})
        r2 = store.begin(e2, "printf second", [], {})
        store.applied(r2, "printf second")
        r3 = store.begin(e3, "printf third", [], {})
        store.transition(r3, "denied", reason="test_denial")
        before = {p.name: p.read_bytes() for p in evidence.iterdir()}
        rows = store.unfinished()
        self.assertEqual(
            {row["recordId"] for row in rows}, {r1["recordId"], r2["recordId"]}
        )
        self.assertEqual({row["effectiveState"] for row in rows}, {"incomplete"})
        self.assertEqual(before, {p.name: p.read_bytes() for p in evidence.iterdir()})

    def test_observed_success_shape_parser_has_no_failure_inference(self):
        event = {
            "cursor_version": "3.24.18",
            "hook_event_name": "postToolUse",
            "tool_output": '{"output":"not retained","exitCode":0}',
        }
        self.assertEqual(A.qualified_success(event, "postToolUse"), 0)
        for change in [
            {"cursor_version": "unknown"},
            {"tool_output": '{"output":"not retained","exitCode":false}'},
            {"tool_output": '{"output":"not retained","exitCode":2}'},
            {"tool_output": '{"output":"x","exitCode":0,"extra":1}'},
            {
                "hook_event_name": "postToolUseFailure",
                "failure_type": "error",
                "error_message": "exit 2",
            },
        ]:
            self.assertIsNone(A.qualified_success({**event, **change}, "postToolUse"))

    def test_real_competing_record_owners_one_wins(self):
        evidence = self.root / "evidence"
        evidence.mkdir(mode=0o700)
        A.ReceiptStore(evidence, "a" * 64)
        script = """import importlib.util,sys
from pathlib import Path
s=importlib.util.spec_from_file_location("a",sys.argv[1]);a=importlib.util.module_from_spec(s);s.loader.exec_module(a)
try:
 store=a.ReceiptStore(Path(sys.argv[2]),"a"*64)
 store.begin({"conversation_id":"c","generation_id":"g","tool_use_id":"t"},"printf x",[],{})
except a.Refusal:sys.exit(3)
"""
        argv = [
            sys.executable,
            "-c",
            script,
            str(ROOT / "integrations/cursor/hook_adapter.py"),
            str(evidence),
        ]
        children = [
            subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            for _ in range(2)
        ]
        codes = []
        for child in children:
            _out, err = child.communicate(timeout=5)
            self.assertEqual(err, b"")
            codes.append(child.returncode)
        self.assertEqual(sorted(codes), [0, 3])


@unittest.skipUnless(
    os.environ.get("CURSOR_TEST_AGENT"),
    "Exact released agent path is required for actual CLI qualification",
)
class ReleasedAgentContracts(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="cursor-released-agent-")
        self.root = Path(self.temp.name).resolve() / "public project 東京"
        self.root.mkdir(mode=0o700)
        self.agent = Path(os.environ["CURSOR_TEST_AGENT"]).resolve()
        self.assertIn(digest(self.agent), A.RELEASED_AGENT_SHA256)
        self.settings = self.root / "settings"
        self.settings.mkdir(mode=0o700)
        (self.settings / "storage").mkdir(mode=0o700)
        (self.root / ".terraphim").mkdir(mode=0o700)
        self.settings_file = self.settings / "settings.toml"
        self.settings_file.write_text(
            'server_hostname = "127.0.0.1:8000"\napi_endpoint = "http://127.0.0.1:8000/api"\ninitialized = true\ndefault_data_path = '
            + json.dumps(str(self.settings / "storage"))
            + '\n[profiles.local]\ntype = "dashmap"\nroot = '
            + json.dumps(str(self.settings / "storage"))
            + "\n"
        )
        self.settings_file.chmod(0o600)
        self.rules = self.root / "rules.json"
        self.guard = self.root / "guard.json"
        self.rules.write_text(
            json.dumps(
                {
                    "name": "compiled_corrections",
                    "data": {
                        "printf old": {
                            "id": 1,
                            "nterm": "printf new",
                            "display_value": "printf new",
                            "pinned": False,
                        }
                    },
                }
            )
        )
        self.guard.write_text('{"name":"guard","data":{}}')
        roles = {}
        for name, path in [("corrections", self.rules), ("guard", self.guard)]:
            roles[name] = {
                "name": name,
                "shortname": None,
                "relevance_function": "title-scorer",
                "terraphim_it": False,
                "theme": "default",
                "haystacks": [],
                "kg": {
                    "automata_path": {"Local": str(path)},
                    "knowledge_graph_local": None,
                    "public": False,
                    "publish": False,
                },
            }
        self.config = self.root / "roles.json"
        self.config.write_text(
            json.dumps(
                {
                    "id": "Embedded",
                    "global_shortcut": None,
                    "roles": roles,
                    "default_role": "corrections",
                    "selected_role": "corrections",
                }
            )
        )

        def ref(p):
            return {"path": str(p), "sha256": digest(p)}

        self.policy = {
            "schemaVersion": 1,
            "projectRoot": str(self.root),
            "agent": ref(self.agent),
            "roleConfig": ref(self.config),
            "startupSettings": {
                "directory": str(self.settings),
                "settingsSha256": digest(self.settings_file),
            },
            "correctionRole": "corrections",
            "guardRole": "guard",
            "compiledRules": ref(self.rules),
            "guardRules": ref(self.guard),
            "rewriteEnabled": True,
            "captureFailures": False,
            "evidence": {"enabled": False},
        }
        self.path = self.root / "policy.json"
        self.write_policy()
        self.event = {
            "tool_name": "Shell",
            "tool_input": {
                "command": "printf old",
                "working_directory": str(self.root),
                "description": "public fixture",
            },
            "cwd": str(self.root),
            "workspace_roots": [str(self.root)],
        }

    def tearDown(self):
        self.temp.cleanup()

    def write_policy(self):
        self.path.write_text(json.dumps(self.policy))
        self.expected = digest(self.path)

    def test_real_released_rewrite_off_and_guard(self):
        result = A.handle_event(self.event, "preToolUse", str(self.path), self.expected)
        self.assertEqual(
            result,
            {
                "permission": "allow",
                "updated_input": {**self.event["tool_input"], "command": "printf new"},
            },
        )
        if os.environ.get("CURSOR_TEST_EVIDENCE"):
            evidence = Path(os.environ["CURSOR_TEST_EVIDENCE"])
            evidence.mkdir(parents=True, exist_ok=True)
            (evidence / "released-rewrite.json").write_text(
                json.dumps(
                    {
                        "scope": "real released agent through adapter, not native Cursor",
                        "agentSha256": digest(self.agent),
                        "policySha256": self.expected,
                        "result": result,
                    },
                    indent=2,
                )
                + "\n"
            )
        self.policy["rewriteEnabled"] = False
        self.write_policy()
        unchanged = A.handle_event(
            self.event, "preToolUse", str(self.path), self.expected
        )
        self.assertEqual(unchanged, {"permission": "allow"})
        if os.environ.get("CURSOR_TEST_EVIDENCE"):
            (
                Path(os.environ["CURSOR_TEST_EVIDENCE"]) / "released-rewrite-off.json"
            ).write_text(json.dumps(unchanged) + "\n")
        self.event["tool_input"]["command"] = "rm -rf /"
        with self.assertRaisesRegex(A.Refusal, "agent_denied"):
            A.handle_event(self.event, "preToolUse", str(self.path), self.expected)
        self.assertEqual(
            digest(self.settings_file), self.policy["startupSettings"]["settingsSha256"]
        )

    def test_policy_drift_and_project_overlay_refuse_before_spawn(self):
        old = self.expected
        self.rules.write_text('{"name":"changed","data":{}}')
        self.policy["compiledRules"]["sha256"] = digest(self.rules)
        self.policy["rewriteEnabled"] = False
        self.write_policy()
        with self.assertRaisesRegex(A.Refusal, "policy_digest"):
            A.handle_event(self.event, "preToolUse", str(self.path), old)
        (self.root / ".terraphim/config.json").write_text("{}")
        with self.assertRaisesRegex(A.Refusal, "project_config"):
            A.handle_event(self.event, "preToolUse", str(self.path), self.expected)

    def test_cli_inspect_does_not_read_stdin_or_modify_records(self):
        evidence = self.root / "evidence"
        evidence.mkdir(mode=0o700)
        self.policy["evidence"] = {
            "enabled": True,
            "directory": str(evidence),
            "outputFiles": [],
        }
        self.write_policy()
        store = A.ReceiptStore(evidence, self.expected)
        event = {
            "conversation_id": "c",
            "generation_id": "g",
            "tool_use_id": "unfinished",
        }
        record = store.begin(event, "printf x", [], A.receipt_identities(self.policy))
        before = {p.name: p.read_bytes() for p in evidence.iterdir()}
        child = subprocess.run(
            [
                sys.executable,
                str(ROOT / "integrations/cursor/hook_adapter.py"),
                "--policy",
                str(self.path),
                "--policy-sha256",
                self.expected,
                "--inspect-receipts",
            ],
            input=b"not json, deliberately unused",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=5,
        )
        self.assertEqual(child.returncode, 0)
        self.assertEqual(child.stderr, b"")
        self.assertEqual(
            json.loads(child.stdout)["unfinished"][0]["recordId"], record["recordId"]
        )
        self.assertEqual(before, {p.name: p.read_bytes() for p in evidence.iterdir()})

    def test_capture_is_unavailable_without_native_result_qualification(self):
        self.policy["captureFailures"] = True
        self.write_policy()
        with self.assertRaisesRegex(A.Refusal, "capture_unavailable"):
            A.handle_event(self.event, "preToolUse", str(self.path), self.expected)
        self.assertFalse((self.root / ".terraphim/learnings").exists())

    def test_actual_cwd_and_workspace_bounds(self):
        for change in [
            {"cwd": str(self.root.parent)},
            {"workspace_roots": [str(self.root), str(self.root.parent)]},
            {"tool_input": {**self.event["tool_input"], "cwd": str(self.root.parent)}},
            {
                "tool_input": {
                    **self.event["tool_input"],
                    "working_directory": str(self.root.parent),
                }
            },
        ]:
            with self.subTest(change=list(change)), self.assertRaises(A.Refusal):
                A.handle_event(
                    {**self.event, **change},
                    "preToolUse",
                    str(self.path),
                    self.expected,
                )

    def test_closed_policy_and_boolean_types(self):
        original = copy.deepcopy(self.policy)
        for change in [
            {"schemaVersion": True},
            {"rewriteEnabled": 1},
            {"unknown": False},
            {"guardRole": "corrections"},
            {"evidence": {"enabled": False, "directory": "/ignored"}},
        ]:
            self.policy = {**original, **change}
            self.write_policy()
            with self.subTest(change=list(change)), self.assertRaises(A.Refusal):
                A.load_policy(str(self.path), self.expected)

    def test_remote_settings_and_provider_config_refuse(self):
        original_config = self.config.read_bytes()
        for kind in ["provider", "alias", "remotegraph"]:
            config = json.loads(original_config)
            if kind == "provider":
                config["roles"]["corrections"]["llm_api_key"] = (
                    "not-a-secret-test-marker"
                )
            elif kind == "alias":
                config["roles"]["guard"]["shortname"] = "Corrections"
            else:
                config["roles"]["guard"]["kg"]["automata_path"] = {
                    "Remote": "https://example.invalid/graph"
                }
            self.config.write_text(json.dumps(config))
            self.policy["roleConfig"]["sha256"] = digest(self.config)
            self.write_policy()
            with self.subTest(kind=kind), self.assertRaises(A.Refusal):
                A.load_policy(str(self.path), self.expected)
        self.config.write_bytes(original_config)
        self.policy["roleConfig"]["sha256"] = digest(self.config)
        self.settings_file.write_text(
            self.settings_file.read_text().replace('type = "dashmap"', 'type = "s3"')
        )
        self.policy["startupSettings"]["settingsSha256"] = digest(self.settings_file)
        self.write_policy()
        with self.assertRaises(A.Refusal):
            A.load_policy(str(self.path), self.expected)

    def test_actual_replacement_is_guarded_and_substrings_are_not_attributed(self):
        rules = json.loads(self.rules.read_text())
        rules["data"]["printf old"]["display_value"] = "rm -rf /"
        rules["data"]["printf old"]["nterm"] = "rm -rf /"
        self.rules.write_text(json.dumps(rules))
        self.policy["compiledRules"]["sha256"] = digest(self.rules)
        self.write_policy()
        with self.assertRaisesRegex(A.Refusal, "agent_denied"):
            A.handle_event(self.event, "preToolUse", str(self.path), self.expected)
        self.event["tool_input"]["command"] = "echo printf old"
        with self.assertRaisesRegex(A.Refusal, "rewrite_unattributed"):
            A.handle_event(self.event, "preToolUse", str(self.path), self.expected)

    def test_evidence_off_creates_no_receipt_and_post_never_learns(self):
        event = {
            **self.event,
            "cursor_version": "3.24.18",
            "hook_event_name": "postToolUseFailure",
            "failure_type": "error",
            "error_message": "exit 2",
        }
        before = sorted(str(p.relative_to(self.root)) for p in self.root.rglob("*"))
        self.assertEqual(
            A.handle_event(event, "postToolUseFailure", str(self.path), self.expected),
            {},
        )
        self.assertEqual(
            sorted(str(p.relative_to(self.root)) for p in self.root.rglob("*")), before
        )

    def test_conflicting_failure_cannot_mutate_owned_call(self):
        evidence = self.root / "evidence"
        evidence.mkdir(mode=0o700)
        self.policy["evidence"] = {
            "enabled": True,
            "directory": str(evidence),
            "outputFiles": [],
        }
        self.write_policy()
        event = {
            **self.event,
            "conversation_id": "c",
            "generation_id": "g",
            "tool_use_id": "t",
            "cursor_version": "3.24.18",
        }
        response = A.handle_event(event, "preToolUse", str(self.path), self.expected)
        store = A.ReceiptStore(evidence, self.expected)
        before = store.path(event).read_bytes()
        conflicting = {
            **event,
            "hook_event_name": "postToolUseFailure",
            "tool_input": {**response["updated_input"], "command": "foreign command"},
            "failure_type": "error",
        }
        with self.assertRaisesRegex(A.Refusal, "evidence_command_mismatch"):
            A.handle_event(
                conflicting, "postToolUseFailure", str(self.path), self.expected
            )
        self.assertEqual(store.path(event).read_bytes(), before)

    def test_tampered_receipt_cannot_expand_policy_or_change_identities(self):
        evidence = self.root / "evidence"
        evidence.mkdir(mode=0o700)
        selected = self.root / "selected-output.txt"
        unselected = self.root / "unselected-output.txt"
        outside = self.root.parent / "outside-public-fixture.txt"
        self.policy["evidence"] = {
            "enabled": True,
            "directory": str(evidence),
            "outputFiles": [str(selected)],
        }
        self.write_policy()
        event = {
            **self.event,
            "conversation_id": "c",
            "generation_id": "g",
            "tool_use_id": "tamper",
            "cursor_version": "3.24.18",
        }
        response = A.handle_event(event, "preToolUse", str(self.path), self.expected)
        store = A.ReceiptStore(evidence, self.expected)
        record_path = store.path(event)
        original = json.loads(record_path.read_text())
        outside.write_text("Test-owned public bytes outside the admitted project.\n")
        unselected.write_text("Test-owned public bytes not selected by the policy.\n")
        selected.write_text("Fresh explicitly selected output.\n")
        post = {
            **event,
            "hook_event_name": "postToolUse",
            "tool_input": response["updated_input"],
            "tool_output": '{"output":"parser fixture only","exitCode":0}',
        }
        # Actual audit events observe filesystem opens; this replaces no implementation.
        observed = []
        observing = [False]

        def audit(name, args):
            if observing[0] and name == "open" and isinstance(args[0], (str, bytes)):
                observed.append(os.fsdecode(args[0]))

        sys.addaudithook(audit)
        mutations = [
            ("outside", {"selectedOutputs": [str(outside)]}),
            ("unselected", {"selectedOutputs": [str(unselected)]}),
            ("omit-required-output", {"selectedOutputs": []}),
            (
                "agent-identity",
                {"identities": {**original["identities"], "agent": "0" * 64}},
            ),
            (
                "adapter-identity",
                {"identities": {**original["identities"], "adapter": "0" * 64}},
            ),
        ]
        for name, change in mutations:
            with self.subTest(name=name):
                record_path.write_text(json.dumps({**original, **change}))
                before = record_path.read_bytes()
                observed.clear()
                observing[0] = True
                try:
                    with self.assertRaisesRegex(A.Refusal, "evidence_admission"):
                        A.handle_event(
                            post, "postToolUse", str(self.path), self.expected
                        )
                finally:
                    observing[0] = False
                self.assertNotIn(str(outside), observed)
                self.assertNotIn(str(unselected), observed)
                self.assertNotIn(str(selected), observed)
                self.assertEqual(record_path.read_bytes(), before)
                self.assertEqual(digest(self.path), self.expected)
        # Unchanged admitted receipt still completes from the real selected file.
        record_path.write_text(json.dumps(original))
        self.assertEqual(
            A.handle_event(post, "postToolUse", str(self.path), self.expected), {}
        )
        completed = json.loads(record_path.read_text())
        self.assertEqual(completed["state"], "completed")
        self.assertEqual(
            completed["artifacts"],
            [
                {
                    "path": str(selected),
                    "sha256": digest(selected),
                    "bytes": selected.stat().st_size,
                }
            ],
        )

    def test_real_agent_applied_receipt_then_observed_success_parser(self):
        evidence = self.root / "evidence"
        evidence.mkdir(mode=0o700)
        selected = self.root / "public-output.txt"
        self.policy["evidence"] = {
            "enabled": True,
            "directory": str(evidence),
            "outputFiles": [str(selected)],
        }
        self.write_policy()
        event = {
            **self.event,
            "conversation_id": "c",
            "generation_id": "g",
            "tool_use_id": "t",
            "cursor_version": "3.24.18",
        }
        result = A.handle_event(event, "preToolUse", str(self.path), self.expected)
        self.assertEqual(result["updated_input"]["command"], "printf new")
        # This is parser/store integration, not a fabricated native event or tool pass.
        selected.write_text("actual test-owned file\n")
        post = {
            **event,
            "tool_input": result["updated_input"],
            "hook_event_name": "postToolUse",
            "tool_output": '{"output":"must never be persisted","exitCode":0}',
        }
        self.assertEqual(
            A.handle_event(post, "postToolUse", str(self.path), self.expected), {}
        )
        store = A.ReceiptStore(evidence, self.expected)
        record = store.read(store.key(event))
        self.assertEqual(record["state"], "completed")
        self.assertEqual(record["artifacts"][0]["sha256"], digest(selected))
        self.assertNotIn("must never be persisted", store.path(event).read_text())


if __name__ == "__main__":
    unittest.main()
