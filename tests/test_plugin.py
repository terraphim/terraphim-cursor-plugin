import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / ".cursor-plugin" / "plugin.json"
EXPECTED_SKILLS = {
    "terraphim-grep": "terraphim-grep",
    "terraphim-agent-learn": "terraphim-agent learn",
    "terraphim-agent-memory": "terraphim-agent memory",
}


def frontmatter(text: str) -> dict[str, str]:
    match = re.match(r"\A---\n(.*?)\n---\n", text, re.DOTALL)
    if not match:
        return {}
    fields: dict[str, str] = {}
    for line in match.group(1).splitlines():
        key, separator, value = line.partition(":")
        if separator:
            fields[key.strip()] = value.strip()
    return fields


class PluginContractTests(unittest.TestCase):
    def test_manifest_declares_exactly_three_skills(self) -> None:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(manifest["license"], "Apache-2.0")
        self.assertEqual(
            manifest["skills"],
            [f"skills/{name}" for name in EXPECTED_SKILLS],
        )
        for relative in manifest["skills"]:
            self.assertTrue((ROOT / relative / "SKILL.md").is_file())

    def test_skill_frontmatter_is_open_source_and_consistent(self) -> None:
        for name in EXPECTED_SKILLS:
            text = (ROOT / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
            metadata = frontmatter(text)
            self.assertEqual(metadata.get("name"), name)
            self.assertEqual(metadata.get("license"), "Apache-2.0")
            self.assertTrue(metadata.get("description"))

    def test_each_wrapper_names_its_real_command(self) -> None:
        for name, command in EXPECTED_SKILLS.items():
            text = (ROOT / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
            self.assertIn(command, text)
            self.assertIn("--help", text)
            self.assertIn("--version", text)

    def test_public_package_contains_no_proprietary_or_secret_markers(self) -> None:
        forbidden = (
            "LicenseRef-Terraphim-" + "Subscriber-1.0",
            "op" + "://",
            "OPENAI_REVIEW_" + "PASSWORD_HASH",
            "stripe-webhook-" + "secret",
        )
        for path in ROOT.rglob("*"):
            if not path.is_file() or {".git", "__pycache__"} & set(path.parts):
                continue
            if path.name not in {"LICENSE", "NOTICE"} and path.suffix not in {
                ".json",
                ".md",
                ".py",
                ".toml",
            }:
                continue
            text = path.read_text(encoding="utf-8")
            for marker in forbidden:
                self.assertNotIn(marker, text, path.as_posix())

    def test_grep_defaults_to_offline_search(self) -> None:
        text = (ROOT / "skills" / "terraphim-grep" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("--search-only", text)
        self.assertIn("--paths", text)
        self.assertIn("--json", text)
        self.assertIn("--answer", text)

    def test_learning_and_memory_distinguish_reads_from_writes(self) -> None:
        learning = (ROOT / "skills" / "terraphim-agent-learn" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        memory = (ROOT / "skills" / "terraphim-agent-memory" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        for token in ("learn list", "learn query", "learn capture", "learn correct"):
            self.assertIn(token, learning)
        for token in (
            "memory scope",
            "memory retrieve",
            "memory provenance",
            "memory apply",
            "memory capture",
            "memory retire",
        ):
            self.assertIn(token, memory)


if __name__ == "__main__":
    unittest.main()
