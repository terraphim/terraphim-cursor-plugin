"""Static setup contracts; these do not qualify native Cursor execution."""
import hashlib
import json
import re
import shlex
import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CURSOR = ROOT / "integrations/cursor"


def read_json(relative):
    return json.loads((CURSOR / relative).read_text(encoding="utf-8"))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class CursorSetupTests(unittest.TestCase):
    def test_selected_release_inputs_are_complete_and_immutable(self):
        inputs = read_json("release-inputs.json")
        self.assertEqual(inputs["clients"]["version"], "1.21.20")
        self.assertEqual(inputs["clients"]["sourceCommit"], "d55d373ec2eb100d334712f086dc95a2829856e7")
        self.assertEqual(len(inputs["clients"]["assets"]), 4)
        self.assertEqual({(a["tool"], a["target"]) for a in inputs["clients"]["assets"]},
                         {(tool, target) for tool in ("terraphim-grep", "terraphim-agent")
                          for target in ("aarch64-apple-darwin", "aarch64-unknown-linux-musl")})
        for asset in inputs["clients"]["assets"]:
            self.assertIn("/releases/download/v1.21.20/", asset["url"])
            for field in ("archiveSha256", "binarySha256"):
                self.assertRegex(asset[field], r"^[0-9a-f]{64}$")
                self.assertGreater(len(set(asset[field])), 8)
            self.assertGreater(asset["bytes"], 1000000)
        mcp = inputs["grepMcp"]
        self.assertEqual(mcp["version"], "0.1.1")
        self.assertEqual(mcp["sourceCommit"], "7fefd368af8cd09ed8d9505ebca7bcdf3e914560")
        self.assertEqual(mcp["sdkRequirement"], "mcp==1.30.0")
        self.assertEqual(mcp["serverSha256"], "bfa55c6c7edebf5c370ec8b7166298167f97e8faa16eb5e68ae2afd7143a86bc")
        self.assertNotIn("nativeAcceptance", inputs)
        self.assertIn("matching release qualification record", inputs["qualificationRequirement"])

    def test_mcp_example_is_direct_retrieval_only_without_secrets(self):
        cfg = read_json("mcp.json.example")
        self.assertEqual(set(cfg), {"mcpServers"})
        self.assertEqual(set(cfg["mcpServers"]), {"terraphim-grep"})
        server = cfg["mcpServers"]["terraphim-grep"]
        self.assertEqual(set(server), {"command", "args"})
        self.assertTrue(Path(server["command"]).is_absolute())
        args = server["args"]
        self.assertTrue(args[0].endswith("server.py"))
        self.assertEqual(args[1::2], ["--binary", "--binary-sha256", "--graph", "--corpus"])
        selected = next(a for a in read_json("release-inputs.json")["clients"]["assets"]
                        if a["tool"] == "terraphim-grep" and a["target"] == "aarch64-apple-darwin")
        self.assertEqual(args[args.index("--binary-sha256") + 1], selected["binarySha256"])
        self.assertNotIn("--allow-synthesis", args)
        self.assertNotIn("install.py", " ".join(args))

    def test_hook_examples_quote_paths_and_pin_complete_policy(self):
        cfg = read_json("hooks.json.example")
        self.assertEqual(cfg["version"], 1)
        self.assertEqual(set(cfg["hooks"]), {"preToolUse", "postToolUse", "postToolUseFailure"})
        policy_hash = digest(CURSOR / "policy.json.example")
        for event, hooks in cfg["hooks"].items():
            self.assertEqual(len(hooks), 1)
            item = hooks[0]
            self.assertEqual(item["matcher"], "Shell")
            self.assertEqual(item["timeout"], 15)
            self.assertIs(item["failClosed"], True)
            argv = shlex.split(item["command"])
            self.assertEqual(argv[2::2], ["--policy", "--policy-sha256", "--event"])
            self.assertEqual(argv[5], policy_hash)
            self.assertEqual(argv[7], event)
            self.assertIn(" ", argv[0])
            self.assertIn(" ", argv[1])

    def test_policy_disables_optional_effects_and_hashes_actual_example_files(self):
        policy = read_json("policy.json.example")
        self.assertIs(policy["rewriteEnabled"], False)
        self.assertIs(policy["captureFailures"], False)
        self.assertEqual(policy["evidence"], {"enabled": False})
        self.assertNotEqual(policy["correctionRole"], policy["guardRole"])
        files = {"roleConfig": "examples/role-config.json.example",
                 "compiledRules": "examples/compiled-corrections.json",
                 "guardRules": "examples/guard-rules.json"}
        for field, relative in files.items():
            self.assertEqual(policy[field]["sha256"], digest(CURSOR / relative))
        self.assertEqual(policy["startupSettings"]["settingsSha256"],
                         digest(CURSOR / "examples/settings.toml.example"))
        selected = next(a for a in read_json("release-inputs.json")["clients"]["assets"]
                        if a["tool"] == "terraphim-agent" and a["target"] == "aarch64-apple-darwin")
        self.assertEqual(policy["agent"]["sha256"], selected["binarySha256"])

    def test_role_and_settings_examples_have_no_remote_or_project_discovery_fallback(self):
        policy = read_json("policy.json.example")
        roles = read_json("examples/role-config.json.example")
        self.assertEqual(set(roles["roles"]), {policy["correctionRole"], policy["guardRole"]})
        for name, role in roles["roles"].items():
            self.assertEqual(role["name"], name)
            self.assertEqual(role["haystacks"], [])
            self.assertIn(role["relevance_function"], {"title-scorer", "terraphim-graph"})
            self.assertIsNone(role["shortname"])
            self.assertFalse(role["kg"]["public"])
            self.assertFalse(role["kg"]["publish"])
            key = "compiledRules" if name == policy["correctionRole"] else "guardRules"
            self.assertEqual(role["kg"]["automata_path"], {"Local": policy[key]["path"]})
            self.assertFalse(any("provider" in k or "llm" in k for k in role))
        settings = tomllib.loads((CURSOR / "examples/settings.toml.example").read_text())
        self.assertNotIn("role_config", settings)
        self.assertEqual(set(settings["profiles"]), {"dashmap"})
        self.assertEqual(settings["profiles"]["dashmap"]["type"], "dashmap")
        self.assertTrue(Path(settings["profiles"]["dashmap"]["root"]).is_relative_to(
            Path(policy["startupSettings"]["directory"])))

    def test_public_corpus_is_input_only_and_has_no_authored_search_alias(self):
        paths = sorted((CURSOR / "examples/corpus").glob("*.md"))
        self.assertEqual(len(paths), 3)
        for path in paths:
            text = path.read_text()
            self.assertIn("Risk:", text)
            self.assertNotIn("concern", text.lower())
        concept = (CURSOR / "examples/concepts/Risk.md").read_text()
        self.assertIn("synonyms:: Concern", concept)
        rules = read_json("examples/compiled-corrections.json")
        self.assertTrue(rules["data"])
        self.assertEqual(read_json("examples/guard-rules.json")["data"], {})

    def test_setup_is_read_first_and_guide_requires_matching_qualification(self):
        command = (CURSOR / "commands/terraphim-setup.md").read_text()
        guide = (CURSOR / "README.md").read_text()
        self.assertTrue(command.startswith("---\n"))
        for text in (command, guide):
            self.assertIn("read-first", text)
            self.assertNotIn("NOT_RUN", text)
            self.assertIn("matching release qualification record", " ".join(text.split()))
        for required in ("Hold the update until hooks pass", "Commands, status and explicitly selected output files only",
                         "captureFailures", "unavailable", "collision", "entry", "--allow-synthesis",
                         "1.21.20", "0.1.1", "no graph-free mode", "startup", "TERRAPHIM_DEFAULT_DATA_PATH",
                         "TERRAPHIM_SETTINGS_PATH", "--inspect-receipts", "tool_input.cwd", "missing exit"):
            self.assertIn(required, " ".join(guide.split()))
        self.assertNotIn("curl |", guide)
        self.assertNotIn("install.py", command)

    def test_public_setup_links_resolve_without_private_local_paths(self):
        for path in [CURSOR / "README.md", CURSOR / "commands/terraphim-setup.md"]:
            text = path.read_text()
            for href in re.findall(r"\]\(([^)]+)\)", text):
                if "://" not in href and not href.startswith("#"):
                    self.assertTrue((path.parent / href.split("#", 1)[0]).resolve().is_file(), href)
            self.assertNotIn("/Users/alex/", text)
            self.assertNotIn("op" + "://", text)
        self.assertFalse((ROOT / "mcp.json").exists())
        self.assertFalse((ROOT / "hooks/hooks.json").exists())
        self.assertFalse((ROOT / "commands/terraphim-setup.md").exists())


if __name__ == "__main__":
    unittest.main()
