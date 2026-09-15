#!/usr/bin/env python3
"""Render native marketplace manifests and deterministic AutoClaw archives."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
from typing import Sequence
import zipfile


ROOT = Path(__file__).resolve().parents[1]
METADATA = ROOT / "distribution" / "metadata.json"
ALLOWED_SKILLS = (
    "terraphim-grep",
    "terraphim-agent-learn",
    "terraphim-agent-memory",
)


def load_metadata(root: Path) -> dict[str, object]:
    """Load canonical distribution metadata.

    Raises:
        ValueError: If the metadata root is not a JSON object.
    """

    value = json.loads((root / "distribution" / "metadata.json").read_text())
    if not isinstance(value, dict):
        raise ValueError("distribution metadata must be a JSON object")
    return value


def _frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    match = re.match(r"\A---\n(.*?)\n---\n", text, re.DOTALL)
    if not match:
        return {}
    fields: dict[str, str] = {}
    for line in match.group(1).splitlines():
        key, separator, value = line.partition(":")
        if separator:
            fields[key.strip()] = value.strip()
    return fields


def validate_metadata(root: Path, metadata: dict[str, object]) -> list[str]:
    """Return deterministic validation errors; empty means valid."""

    errors: list[str] = []
    plugin = metadata.get("plugin")
    runtime = metadata.get("runtime")
    skills = metadata.get("skills")
    if metadata.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    if not isinstance(plugin, dict):
        errors.append("plugin must be an object")
        plugin = {}
    if not isinstance(runtime, dict):
        errors.append("runtime must be an object")
    if not isinstance(skills, list):
        errors.append("skills must be an array")
        skills = []

    required_plugin = (
        "name",
        "display_name",
        "version",
        "description",
        "description_zh_cn",
        "author_name",
        "author_email",
        "homepage",
        "catalogue",
        "repository",
        "license",
        "category",
        "keywords",
    )
    for key in required_plugin:
        if not plugin.get(key):
            errors.append(f"plugin.{key} is required")
    if plugin.get("name") != "terraphim-skills-intro":
        errors.append("plugin.name must remain terraphim-skills-intro")
    if plugin.get("license") != "Apache-2.0":
        errors.append("plugin.license must be Apache-2.0")

    names = [item.get("name") for item in skills if isinstance(item, dict)]
    if names != list(ALLOWED_SKILLS):
        errors.append(f"skills must be the exact ordered allowlist {ALLOWED_SKILLS!r}")
    discovered = sorted(
        path.parent.name for path in (root / "skills").glob("*/SKILL.md")
    )
    if discovered != sorted(ALLOWED_SKILLS):
        errors.append(f"skill tree differs from allowlist: {discovered!r}")

    for item in skills:
        if not isinstance(item, dict):
            errors.append("each skill must be an object")
            continue
        name = item.get("name")
        relative = item.get("path")
        if not isinstance(name, str) or not isinstance(relative, str):
            errors.append("each skill requires string name and path")
            continue
        expected_path = f"skills/{name}"
        if relative != expected_path:
            errors.append(f"{name} path must be {expected_path}")
            continue
        skill_file = root / relative / "SKILL.md"
        if not skill_file.is_file():
            errors.append(f"{relative}/SKILL.md is missing")
            continue
        fields = _frontmatter(skill_file)
        if fields.get("name") != name:
            errors.append(f"{name} frontmatter name does not match")
        if fields.get("license") != plugin.get("license"):
            errors.append(f"{name} frontmatter licence does not match")
        if not fields.get("description"):
            errors.append(f"{name} frontmatter description is missing")
    return sorted(errors)


def _identity(metadata: dict[str, object]) -> dict[str, object]:
    plugin = metadata["plugin"]
    assert isinstance(plugin, dict)
    return {
        "name": plugin["name"],
        "description": plugin["description"],
        "version": plugin["version"],
        "author": {
            "name": plugin["author_name"],
            "email": plugin["author_email"],
        },
        "homepage": plugin["homepage"],
        "repository": plugin["repository"],
        "license": plugin["license"],
        "keywords": plugin["keywords"],
    }


def _skill_paths(metadata: dict[str, object], *, dotted: bool = False) -> list[str]:
    skills = metadata["skills"]
    assert isinstance(skills, list)
    prefix = "./" if dotted else ""
    return [prefix + item["path"] for item in skills if isinstance(item, dict)]


def render_cursor(metadata: dict[str, object]) -> dict[str, object]:
    """Render the Cursor plugin manifest."""

    value = _identity(metadata)
    value["logo"] = "assets/logo.svg"
    value["skills"] = _skill_paths(metadata)
    return value


def render_kimi(metadata: dict[str, object]) -> dict[str, object]:
    """Render the Kimi plugin manifest."""

    value = _identity(metadata)
    plugin = metadata["plugin"]
    assert isinstance(plugin, dict)
    value["skills"] = _skill_paths(metadata, dotted=True)
    value["interface"] = {
        "displayName": plugin["display_name"],
        "shortDescription": "Local search, learning, and memory workflows",
        "developerName": plugin["author_name"],
        "websiteURL": plugin["homepage"],
    }
    return value


def render_kimi_marketplace(metadata: dict[str, object]) -> dict[str, object]:
    """Render the Terraphim Kimi custom marketplace."""

    plugin = metadata["plugin"]
    assert isinstance(plugin, dict)
    tag = f"v{plugin['version']}"
    return {
        "version": "2",
        "plugins": [
            {
                "id": plugin["name"],
                "displayName": plugin["display_name"],
                "description": plugin["description"],
                "source": f"{plugin['repository']}/archive/refs/tags/{tag}.zip",
            }
        ],
    }


def render_zcode(metadata: dict[str, object]) -> dict[str, object]:
    """Render the ZCode native plugin manifest."""

    value = _identity(metadata)
    plugin = metadata["plugin"]
    assert isinstance(plugin, dict)
    value["displayName"] = plugin["display_name"]
    value["description_i18n"] = {
        "en": plugin["description"],
        "zh-CN": plugin["description_zh_cn"],
    }
    value["skills"] = _skill_paths(metadata, dotted=True)
    return value


def render_zcode_marketplace(metadata: dict[str, object]) -> dict[str, object]:
    """Render a ZCode-compatible publisher marketplace."""

    plugin = metadata["plugin"]
    assert isinstance(plugin, dict)
    return {
        "name": "terraphim-skills",
        "description": "Public Community skills from Terraphim AI.",
        "plugins": [
            {
                "name": plugin["name"],
                "source": {
                    "source": "github",
                    "repo": "terraphim/terraphim-cursor-plugin",
                    "path": ".",
                    "ref": f"v{plugin['version']}",
                },
                "description": plugin["description"],
                "description_i18n": {
                    "en": plugin["description"],
                    "zh-CN": plugin["description_zh_cn"],
                },
                "version": plugin["version"],
                "category": "developer-tools",
                "tags": plugin["keywords"],
                "strict": True,
            }
        ],
    }


def render_claude_plugin(metadata: dict[str, object]) -> dict[str, object]:
    """Render the Claude Code plugin manifest."""

    return _identity(metadata)


def render_claude_marketplace(metadata: dict[str, object]) -> dict[str, object]:
    """Render the publisher-owned Claude Code marketplace."""

    plugin = metadata["plugin"]
    assert isinstance(plugin, dict)
    return {
        "name": "terraphim-skills",
        "description": "Public Community skills from Terraphim AI.",
        "owner": {
            "name": plugin["author_name"],
            "email": plugin["author_email"],
        },
        "plugins": [
            {
                "name": plugin["name"],
                "source": "./",
                "description": plugin["description"],
                "version": plugin["version"],
                "category": "development",
                "homepage": plugin["homepage"],
            }
        ],
    }


def generated_files(root: Path, metadata: dict[str, object]) -> dict[Path, str]:
    """Return generated manifest paths and canonical JSON text."""

    rendered = {
        Path(".cursor-plugin/plugin.json"): render_cursor(metadata),
        Path("kimi.plugin.json"): render_kimi(metadata),
        Path("plugin.json"): render_kimi(metadata),
        Path("marketplaces/kimi.json"): render_kimi_marketplace(metadata),
        Path(".zcode-plugin/plugin.json"): render_zcode(metadata),
        Path("marketplaces/zcode.json"): render_zcode_marketplace(metadata),
        Path(".claude-plugin/plugin.json"): render_claude_plugin(metadata),
        Path(".claude-plugin/marketplace.json"): render_claude_marketplace(metadata),
    }
    return {
        root / path: json.dumps(value, indent=2, ensure_ascii=False) + "\n"
        for path, value in rendered.items()
    }


def write_or_check(root: Path, *, check: bool) -> int:
    """Write outputs or return one when committed outputs drift."""

    metadata = load_metadata(root)
    errors = validate_metadata(root, metadata)
    if errors:
        for error in errors:
            print(f"error: {error}")
        return 1
    drift: list[str] = []
    for path, content in generated_files(root, metadata).items():
        if check:
            if not path.is_file() or path.read_text(encoding="utf-8") != content:
                drift.append(path.relative_to(root).as_posix())
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
    if drift:
        for path in drift:
            print(f"out of date: {path}")
        return 1
    return 0


def _zip_info(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o100644 << 16
    info.create_system = 3
    return info


def build_autoclaw_archives(
    root: Path, metadata: dict[str, object], output: Path
) -> list[Path]:
    """Build one deterministic ZIP per allowlisted skill plus SHA256SUMS."""

    output.mkdir(parents=True, exist_ok=True)
    plugin = metadata["plugin"]
    skills = metadata["skills"]
    assert isinstance(plugin, dict) and isinstance(skills, list)
    archives: list[Path] = []
    for skill in skills:
        assert isinstance(skill, dict)
        name = str(skill["name"])
        skill_root = root / str(skill["path"])
        archive = output / f"{name}-{plugin['version']}.zip"
        with zipfile.ZipFile(archive, "w") as target:
            for source in sorted(
                path for path in skill_root.rglob("*") if path.is_file()
            ):
                relative = source.relative_to(skill_root).as_posix()
                target.writestr(
                    _zip_info(f"{name}/{relative}"),
                    source.read_bytes(),
                    compresslevel=9,
                )
        archives.append(archive)
    checksums = "".join(
        f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}\n"
        for path in archives
    )
    (output / "SHA256SUMS").write_text(checksums, encoding="utf-8")
    return archives


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--print-version", action="store_true")
    parser.add_argument("--autoclaw-dist", type=Path)
    args = parser.parse_args(argv)
    if args.print_version:
        metadata = load_metadata(ROOT)
        errors = validate_metadata(ROOT, metadata)
        if errors:
            for error in errors:
                print(f"error: {error}")
            return 1
        plugin = metadata["plugin"]
        assert isinstance(plugin, dict)
        print(plugin["version"])
        return 0
    result = write_or_check(ROOT, check=args.check)
    if result or args.check or args.autoclaw_dist is None:
        return result
    metadata = load_metadata(ROOT)
    build_autoclaw_archives(ROOT, metadata, args.autoclaw_dist)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
