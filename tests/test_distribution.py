from __future__ import annotations

import hashlib
import importlib.util
import io
import json
from pathlib import Path
import re
import tempfile
import unittest
import zipfile
from contextlib import redirect_stdout


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "generate_distribution", ROOT / "scripts" / "generate_distribution.py"
)
assert SPEC is not None and SPEC.loader is not None
GENERATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GENERATOR)


class DistributionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.metadata = GENERATOR.load_metadata(ROOT)

    def test_exact_public_skill_allowlist_and_tree(self) -> None:
        self.assertEqual([], GENERATOR.validate_metadata(ROOT, self.metadata))
        names = tuple(skill["name"] for skill in self.metadata["skills"])
        self.assertEqual(GENERATOR.ALLOWED_SKILLS, names)

    def test_print_version_matches_manifests(self) -> None:
        self.assertEqual("0.2.1", self.metadata["plugin"]["version"])
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(0, GENERATOR.main(["--print-version"]))
        self.assertEqual("0.2.1\n", output.getvalue())

    def test_generated_manifests_are_current_and_deterministic(self) -> None:
        expected = GENERATOR.generated_files(ROOT, self.metadata)
        first = {path: content for path, content in expected.items()}
        second = GENERATOR.generated_files(ROOT, self.metadata)
        self.assertEqual(first, second)
        for path, content in expected.items():
            self.assertEqual(content, path.read_text(encoding="utf-8"), path)

    def test_manifests_share_identity_version_and_skills(self) -> None:
        plugin = self.metadata["plugin"]
        expected_paths = [skill["path"] for skill in self.metadata["skills"]]
        manifests = [
            json.loads((ROOT / ".cursor-plugin/plugin.json").read_text()),
            json.loads((ROOT / "kimi.plugin.json").read_text()),
            json.loads((ROOT / "plugin.json").read_text()),
            json.loads((ROOT / ".zcode-plugin/plugin.json").read_text()),
        ]
        for manifest in manifests:
            self.assertEqual(plugin["name"], manifest["name"])
            self.assertEqual(plugin["version"], manifest["version"])
            self.assertEqual(plugin["homepage"], manifest["homepage"])
            self.assertEqual(
                expected_paths,
                [path.removeprefix("./") for path in manifest["skills"]],
            )

    def test_no_ambient_components_are_packaged(self) -> None:
        forbidden = {"commands", "agents", "hooks", "mcpServers", "lspServers"}
        for path in (
            ROOT / ".cursor-plugin/plugin.json",
            ROOT / "kimi.plugin.json",
            ROOT / "plugin.json",
            ROOT / ".zcode-plugin/plugin.json",
            ROOT / ".claude-plugin/plugin.json",
        ):
            manifest = json.loads(path.read_text())
            self.assertTrue(forbidden.isdisjoint(manifest), path)

    def test_kimi_marketplace_uses_current_v2_contract(self) -> None:
        marketplace = json.loads((ROOT / "marketplaces/kimi.json").read_text())
        self.assertEqual("2", marketplace["version"])
        self.assertEqual(
            {
                "id",
                "displayName",
                "description",
                "source",
            },
            set(marketplace["plugins"][0]),
        )

    def test_zcode_marketplace_pins_release_and_category(self) -> None:
        marketplace = json.loads((ROOT / "marketplaces/zcode.json").read_text())
        entry = marketplace["plugins"][0]
        self.assertEqual("terraphim-skills-intro", entry["name"])
        self.assertEqual("developer-tools", entry["category"])
        self.assertEqual("v0.2.1", entry["source"]["ref"])
        self.assertTrue(entry["strict"])
        self.assertEqual({"en", "zh-CN"}, set(entry["description_i18n"]))
        manifest = json.loads((ROOT / ".zcode-plugin/plugin.json").read_text())
        self.assertEqual(entry["description_i18n"], manifest["description_i18n"])

    def test_autoclaw_archives_are_reproducible_and_one_skill_each(self) -> None:
        with (
            tempfile.TemporaryDirectory() as first_dir,
            tempfile.TemporaryDirectory() as second_dir,
        ):
            first = Path(first_dir)
            second = Path(second_dir)
            GENERATOR.build_autoclaw_archives(ROOT, self.metadata, first)
            GENERATOR.build_autoclaw_archives(ROOT, self.metadata, second)
            self.assertEqual(
                (first / "SHA256SUMS").read_bytes(),
                (second / "SHA256SUMS").read_bytes(),
            )
            for archive in sorted(first.glob("*.zip")):
                twin = second / archive.name
                self.assertEqual(archive.read_bytes(), twin.read_bytes())
                with zipfile.ZipFile(archive) as package:
                    roots = {name.split("/", 1)[0] for name in package.namelist()}
                    self.assertEqual(1, len(roots), archive)
                    self.assertIn(f"{next(iter(roots))}/SKILL.md", package.namelist())

    def test_committed_autoclaw_checksums_match_archives(self) -> None:
        dist = ROOT / "dist" / "autoclaw"
        recorded = {}
        for line in (dist / "SHA256SUMS").read_text().splitlines():
            digest, name = line.split("  ", 1)
            recorded[name] = digest
        archives = sorted(dist.glob("*.zip"))
        self.assertEqual({archive.name for archive in archives}, set(recorded))
        for archive in archives:
            self.assertEqual(
                recorded[archive.name], hashlib.sha256(archive.read_bytes()).hexdigest()
            )

    def test_release_checkout_fetches_annotated_tag_object(self) -> None:
        workflow = (ROOT / ".github/workflows/release.yml").read_text()
        self.assertIn("fetch-depth: 0", workflow)
        self.assertIn('git verify-tag "$GITHUB_REF_NAME"', workflow)

    def test_docs_cover_hosts_and_dependency_probes(self) -> None:
        readme = (ROOT / "README.md").read_text().lower()
        uat = (ROOT / "docs/uat/multi-marketplace.md").read_text().lower()
        for host in (
            "cursor",
            "kimi",
            "autoclaw",
            "zcode",
            "hermes",
            "skills.sh",
            "claude",
        ):
            self.assertIn(host, readme)
            self.assertIn(host, uat)
        for probe in self.metadata["runtime"]["verify"]:
            self.assertIn(probe, (ROOT / "docs/install-dependencies.md").read_text())

    def test_skills_hint_dependencies_without_installing_them(self) -> None:
        for name in GENERATOR.ALLOWED_SKILLS:
            text = (ROOT / "skills" / name / "SKILL.md").read_text().lower()
            self.assertIn("brew tap terraphim/terraphim", text)
            self.assertNotIn("automatically install", text)

    def test_pack_excludes_secret_and_proprietary_markers(self) -> None:
        forbidden = (
            "op" + "://",
            "stripe_" + "secret",
            "premium skill " + "body",
        )
        for path in ROOT.rglob("*"):
            if (
                not path.is_file()
                or {".git", "__pycache__"} & set(path.parts)
                or path.suffix == ".zip"
            ):
                continue
            text = path.read_text(encoding="utf-8", errors="ignore").lower()
            for marker in forbidden:
                self.assertNotIn(marker, text, path)

    def test_catalogue_links_are_neutral_and_do_not_checkout(self) -> None:
        for name in GENERATOR.ALLOWED_SKILLS:
            text = (ROOT / "skills" / name / "SKILL.md").read_text().lower()
            self.assertIn("https://terraphim-skills.md/skills/", text)
            self.assertIn("never starts checkout or changes", text)

    def test_chinese_readme_matches_public_boundary(self) -> None:
        text = (ROOT / "README_CN.md").read_text()
        self.assertIn("terraphim-grep", text)
        self.assertIn("terraphim-agent-learn", text)
        self.assertIn("terraphim-agent-memory", text)
        self.assertIn("https://terraphim-skills.md/skills/", text)

    def test_local_markdown_links_resolve(self) -> None:
        link_pattern = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
        for markdown in ROOT.rglob("*.md"):
            if ".git" in markdown.parts:
                continue
            for target in link_pattern.findall(markdown.read_text(encoding="utf-8")):
                if target.startswith(("http://", "https://", "mailto:", "#")):
                    continue
                path = target.split("#", 1)[0]
                self.assertTrue(
                    (markdown.parent / path).resolve().exists(), (markdown, target)
                )


if __name__ == "__main__":
    unittest.main()
