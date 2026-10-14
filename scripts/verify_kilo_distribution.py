#!/usr/bin/env python3
"""Verify signed source and exact reviewed Kilo transforms without extracting tar files.

The checked-in release-inputs file is the reviewed admission boundary. It is not
an automatically learned allowlist. Original BLAKE3/signature verification uses
the official pinned TSM; SHA-256 records distribution identities separately.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import tarfile
import tomllib
import unicodedata

MAX_FILES = 2048
MAX_FILE_BYTES = 8 * 1024 * 1024
MAX_TOTAL_BYTES = 32 * 1024 * 1024
MAX_ARCHIVE_BYTES = 32 * 1024 * 1024
MAX_PATH_BYTES = 1024
# Bound raw tar headers/PAX extensions as well as regular payload expansion.
MAX_TAR_BYTES = MAX_TOTAL_BYTES + 8 * 1024 * 1024
TRUSTED_PUBLISHER = "261c6820525270bfe2a5daaa5bf3f581bd9bc193e1a0148010e870a3a63ad959"
TRUSTED_TSM = {
    "39ba54477a2dd6de4142688d3c0e500752effd799f664ecf67b393b3a91ac287": "aarch64-apple-darwin",
    "2dc46f7c0a7d67e21b7f9b254e6d99b778509799d53a8beaf3a095d9de864aab": "x86_64-unknown-linux-gnu",
}
CONTROLS = {"local.patch", "local.remove"}
PROVENANCE_PATH = "references/kilo-provenance.json"
FOOTER = """\n## Kilo distribution provenance\n\nThis Kilo copy preserves the original skill instructions and resources. Its\nfrontmatter and packaging were transformed by the pinned Kilo importer. The\noriginal Terraphim signature applies to the immutable source, not this copy.\nSee [source provenance](references/kilo-provenance.json), [LICENSE](LICENSE) and\n[NOTICE](NOTICE).\n"""


class VerificationError(ValueError):
    """An input violates the reviewed package admission contract."""


def digest(data: bytes) -> str:
    """Return the distribution SHA-256, never a substitute for signed BLAKE3."""
    return hashlib.sha256(data).hexdigest()


def validate_names(names) -> None:
    """Reject ambiguous paths before reading payloads or considering extraction."""
    seen = set()
    for name in names:
        if (
            not isinstance(name, str)
            or not name
            or "\\" in name
            or "\x00" in name
            or len(name.encode("utf-8")) > MAX_PATH_BYTES
            or any(part in ("", ".", "..") for part in name.split("/"))
            or re.match(r"^[A-Za-z]:", name)
        ):
            raise VerificationError(f"unsafe path: {name!r}")
        normalized = unicodedata.normalize("NFC", name).casefold()
        if normalized in seen:
            raise VerificationError(f"duplicate or normalized path collision: {name!r}")
        seen.add(normalized)


def read_tree(root: Path) -> dict[str, str]:
    """Hash a bounded regular-file tree without following symlink entries."""
    if root.is_symlink() or not root.is_dir():
        raise VerificationError("tree root must be a real directory, not a symlink")
    paths = []
    directories = []
    total = 0
    result = {}
    for base, dirs, files in os.walk(root, followlinks=False):
        for name in dirs + files:
            file = Path(base) / name
            rel = file.relative_to(root).as_posix()
            info = file.lstat()
            if stat.S_ISLNK(info.st_mode):
                raise VerificationError(f"symlink refused: {rel}")
            if stat.S_ISDIR(info.st_mode):
                directories.append(rel)
                if len(directories) > MAX_FILES:
                    raise VerificationError("directory count limit exceeded")
                continue
            if not stat.S_ISREG(info.st_mode):
                raise VerificationError(f"non-regular file refused: {rel}")
            paths.append(rel)
            if len(paths) > MAX_FILES:
                raise VerificationError("file count limit exceeded")
            if info.st_size > MAX_FILE_BYTES:
                raise VerificationError(f"file size limit exceeded: {rel}")
            total += info.st_size
            if total > MAX_TOTAL_BYTES:
                raise VerificationError("total size limit exceeded")
            with file.open("rb") as handle:
                data = handle.read(MAX_FILE_BYTES + 1)
            if len(data) != info.st_size:
                raise VerificationError(f"file changed while reading: {rel}")
            result[rel] = digest(data)
    validate_names(paths + directories)
    return dict(sorted(result.items()))


def _entry(inputs: dict, entry_id: str) -> dict:
    if (
        inputs.get("schemaVersion") != 1
        or inputs.get("publisherKey") != TRUSTED_PUBLISHER
    ):
        raise VerificationError("untrusted publisher or input schema")
    if not re.fullmatch(r"[0-9a-f]{40}", inputs.get("importerCommit", "")):
        raise VerificationError("importer must be pinned to a full commit")
    row = inputs.get("skills", {}).get(entry_id)
    if not row or not re.fullmatch(r"terraphim-[a-z-]+", entry_id):
        raise VerificationError("entry is not admitted")
    if row.get(
        "sourceRepository"
    ) != "https://github.com/terraphim/terraphim-cursor-plugin" or not re.fullmatch(
        r"[0-9a-f]{40}", row.get("sourceCommit", "")
    ):
        raise VerificationError("source identity is not pinned")
    return row


def _source(source: Path, inputs: dict, entry_id: str) -> tuple[dict, dict]:
    row = _entry(inputs, entry_id)
    actual = read_tree(source)
    if actual != row["sourceFiles"]:
        raise VerificationError("source files differ from admitted hashes")
    try:
        manifest = tomllib.loads((source / "skill.toml").read_text(encoding="utf-8"))
    except (ValueError, OSError) as error:
        raise VerificationError(f"invalid source manifest: {error}") from error
    if (
        manifest.get("skill", {}).get("name") != entry_id
        or manifest["skill"].get("version") != row["version"]
        or manifest.get("signature", {}).get("public_key") != TRUSTED_PUBLISHER
    ):
        raise VerificationError("source manifest identity/publisher mismatch")
    if manifest.get("files") != row["sourceBlake3"] or set(actual) != set(
        manifest["files"]
    ) | {"skill.toml"}:
        raise VerificationError("source contains unsigned or missing payload files")
    return row, manifest


def verify_source(source: Path, inputs: dict, entry_id: str, tsm: Path) -> dict:
    """Verify admitted source hashes and the original signature using real TSM."""
    row, manifest = _source(source, inputs, entry_id)
    if tsm.is_symlink() or not tsm.is_file() or tsm.stat().st_size > MAX_TOTAL_BYTES:
        raise VerificationError("verifier identity is not admitted")
    identity = digest(tsm.read_bytes())
    if identity not in TRUSTED_TSM:
        raise VerificationError("verifier identity is not admitted")
    if source.name != entry_id:
        raise VerificationError("source directory must match its signed skill name")
    try:
        version = subprocess.run(
            [str(tsm), "--version"],
            capture_output=True,
            text=True,
            check=True,
            timeout=15,
        )
        if version.stdout.strip() != "tsm 0.1.16":
            raise VerificationError("verifier version is not 0.1.16")
        result = subprocess.run(
            [
                str(tsm),
                "verify",
                entry_id,
                "--install-dir",
                str(source.parent),
                "--trusted-key",
                TRUSTED_PUBLISHER,
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=60,
        )
    except (subprocess.SubprocessError, OSError) as error:
        raise VerificationError(
            f"official signature verification failed: {error}"
        ) from error
    if read_tree(source) != row["sourceFiles"] or digest(tsm.read_bytes()) != identity:
        raise VerificationError("source/verifier changed during verification")
    return {
        "status": "PASS",
        "entryId": entry_id,
        "sourceCommit": row["sourceCommit"],
        "releaseStatus": row["releaseStatus"],
        "publisherKey": TRUSTED_PUBLISHER,
        "verifierSha256": identity,
        "verifierVersion": version.stdout.strip(),
        "manifestSha256": row["sourceFiles"]["skill.toml"],
        "sourceBlake3": manifest["files"],
        "sourceFiles": row["sourceFiles"],
        "verificationOutput": result.stdout + result.stderr,
    }


def normalized_resource(data: bytes) -> bytes:
    """Match upstream text normalization; binary resources must stay identical."""
    if b"\x00" in data:
        return data
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return data
    text = re.sub(r"[ \t]+$", "", text.replace("\r\n", "\n"), flags=re.MULTILINE)
    return (text.rstrip("\n") + "\n").encode("utf-8")


def _body(data: bytes) -> bytes:
    normalized = normalized_resource(data)
    sections = normalized.split(b"\n---\n", 1)
    if not normalized.startswith(b"---\n") or len(sections) != 2:
        raise VerificationError("SKILL.md must have delimited frontmatter")
    return sections[1]


def wording_corrections(row: dict, entry_id: str) -> list[dict]:
    """Return the single reviewed factual correction for the original 1.0.3 skills."""
    if (
        entry_id
        not in {"terraphim-grep", "terraphim-agent-memory", "terraphim-agent-learn"}
        or row.get("version") != "1.0.3"
        or row.get("sourceCommit") != "391c7e4ebc103f1770b9dca589fcce7ccd211d5f"
    ):
        return []
    return [
        {
            "sourceVersion": "1.0.3",
            "sourceCommit": "391c7e4ebc103f1770b9dca589fcce7ccd211d5f",
            "oldText": "For signed,\nchecksummed release archives",
            "newText": "For checksummed release archives",
            "reason": "The verified skill signature does not authenticate separate CLI archives; only CLI release checksums were verified.",
        }
    ]


def expected_instruction_body(data: bytes, row: dict, entry_id: str) -> bytes:
    """Preserve original instructions except an exact admitted factual correction."""
    body = _body(data).rstrip(b"\n")
    for correction in wording_corrections(row, entry_id):
        old = correction["oldText"].encode()
        if body.count(old) != 1:
            raise VerificationError(
                "reviewed wording correction is not uniquely applicable"
            )
        body = body.replace(old, correction["newText"].encode())
    return body + b"\n" + FOOTER.encode()


def _archive_files(row: dict) -> dict:
    imported = row.get("import")
    if not imported:
        raise VerificationError("import has not been admitted")
    files = imported["files"]
    if "skill.toml" in files or not {
        "SKILL.md",
        "LICENSE",
        "NOTICE",
        PROVENANCE_PATH,
        *CONTROLS,
    } <= set(files):
        raise VerificationError(
            "import lacks provenance/license/control files or retains signature"
        )
    validate_names(files)
    return {name: value for name, value in files.items() if name not in CONTROLS}


def verify_import(source: Path, imported: Path, inputs: dict, entry_id: str) -> dict:
    """Compare exact official-import output and independently constrain transforms."""
    row, _ = _source(source, inputs, entry_id)
    archive_files = _archive_files(row)
    actual = read_tree(imported)
    if actual != row["import"]["files"]:
        raise VerificationError(
            "import tree differs from reviewed official updater output"
        )
    if (imported / "local.remove").read_bytes() != b"skill.toml\n":
        raise VerificationError("root signature removal is not exact")
    if _body((imported / "SKILL.md").read_bytes()) != expected_instruction_body(
        (source / "SKILL.md").read_bytes(), row, entry_id
    ):
        raise VerificationError("imported instruction body changed")
    for name in row["sourceBlake3"]:
        if name != "SKILL.md" and (imported / name).read_bytes() != normalized_resource(
            (source / name).read_bytes()
        ):
            raise VerificationError(f"imported source resource changed: {name}")
    for name, expected in row["licenseFiles"].items():
        if actual.get(name) != expected:
            raise VerificationError(f"license/notice changed: {name}")
    provenance = json.loads((imported / PROVENANCE_PATH).read_text(encoding="utf-8"))
    if provenance.get("wordingCorrections", []) != wording_corrections(row, entry_id):
        raise VerificationError("wording provenance differs from reviewed correction")
    original = provenance["source"]
    if (
        provenance.get("schemaVersion") != 1
        or provenance.get("entryId") != entry_id
        or original["commit"] != row["sourceCommit"]
        or original["repository"] != row["sourceRepository"]
        or original["release"] != row["sourceRelease"]
        or original["version"] != row["version"]
        or original["publisherKey"] != TRUSTED_PUBLISHER
        or original["manifestSha256"] != row["sourceFiles"]["skill.toml"]
        or original["files"]
        != {
            name: {"sha256": row["sourceFiles"][name], "blake3": value}
            for name, value in row["sourceBlake3"].items()
        }
        or provenance["importer"]["commit"] != inputs["importerCommit"]
    ):
        raise VerificationError("import provenance differs from verified source")
    return {
        "status": "PASS",
        "entryId": entry_id,
        "sourceCommit": row["sourceCommit"],
        "importerCommit": inputs["importerCommit"],
        "files": actual,
        "archiveFiles": archive_files,
        "transforms": provenance["transforms"],
        "scope": "source bytes and reviewed import; call verify_source for signature proof",
    }


def verify_archive(archive: Path, inputs: dict, entry_id: str) -> dict:
    """Validate a bounded gzip/tar and exact payload without extracting any member."""
    row = _entry(inputs, entry_id)
    expected = _archive_files(row)
    if (
        archive.is_symlink()
        or not archive.is_file()
        or archive.stat().st_size > MAX_ARCHIVE_BYTES
    ):
        raise VerificationError("compressed archive size/type refused")
    compressed = archive.read_bytes()
    if len(compressed) > MAX_ARCHIVE_BYTES:
        raise VerificationError("compressed archive size limit exceeded")
    try:
        with gzip.GzipFile(fileobj=io.BytesIO(compressed)) as zipped:
            raw = zipped.read(MAX_TAR_BYTES + 1)
        if len(raw) > MAX_TAR_BYTES:
            raise VerificationError("expanded tar size limit exceeded")
        actual, names, total, members = {}, [], 0, 0
        required_dirs = {entry_id}
        for name in expected:
            parts = name.split("/")
            required_dirs.update(
                entry_id + "/" + "/".join(parts[:n]) for n in range(1, len(parts))
            )
        with tarfile.open(fileobj=io.BytesIO(raw), mode="r:") as container:
            for member in container:
                members += 1
                if members > 2 * MAX_FILES:
                    raise VerificationError("archive member count limit exceeded")
                name = member.name.rstrip("/") if member.isdir() else member.name
                names.append(name)
                validate_names(names)
                if member.isdir():
                    if name not in required_dirs:
                        raise VerificationError("unexpected archive directory")
                    continue
                if (
                    member.type not in (tarfile.REGTYPE, tarfile.AREGTYPE)
                    or member.sparse is not None
                ):
                    raise VerificationError(
                        "archive link/device/sparse/non-regular entry refused"
                    )
                if member.size < 0 or member.size > MAX_FILE_BYTES:
                    raise VerificationError("archive file size limit exceeded")
                total += member.size
                if total > MAX_TOTAL_BYTES or len(actual) >= MAX_FILES:
                    raise VerificationError(
                        "archive total size/file count limit exceeded"
                    )
                if not name.startswith(entry_id + "/"):
                    raise VerificationError("unexpected outer archive directory")
                rel = name[len(entry_id) + 1 :]
                if rel not in expected:
                    raise VerificationError("undeclared archive file")
                handle = container.extractfile(member)
                if handle is None:
                    raise VerificationError("archive member has no payload")
                data = handle.read(MAX_FILE_BYTES + 1)
                if len(data) != member.size:
                    raise VerificationError("archive member size mismatch")
                actual[rel] = digest(data)
            if any(raw[container.offset :]):
                raise VerificationError("nonzero trailing tar data refused")
    except (tarfile.TarError, OSError, EOFError) as error:
        raise VerificationError(f"invalid compressed tar: {error}") from error
    if actual != expected:
        raise VerificationError("archive payload differs from admitted import")
    return {
        "status": "PASS",
        "entryId": entry_id,
        "sha256": digest(compressed),
        "size": len(compressed),
        "expandedPayloadBytes": total,
        "files": actual,
    }


def main(argv=None) -> int:
    """Write a machine-readable receipt; never upload or mutate source/imports."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--tsm", type=Path, required=True)
    parser.add_argument(
        "--entry", action="append", help="Defaults to every admitted source skill"
    )
    parser.add_argument("--import-root", type=Path)
    parser.add_argument("--archive-root", type=Path)
    args = parser.parse_args(argv)
    try:
        inputs = json.loads(args.inputs.read_text(encoding="utf-8"))
        results = []
        for entry_id in args.entry or list(inputs["skills"]):
            source = args.source_root / entry_id
            result = {"source": verify_source(source, inputs, entry_id, args.tsm)}
            if args.import_root:
                result["import"] = verify_import(
                    source, args.import_root / entry_id, inputs, entry_id
                )
            if args.archive_root:
                result["archive"] = verify_archive(
                    args.archive_root / f"{entry_id}.tar.gz", inputs, entry_id
                )
            results.append(result)
        print(
            json.dumps(
                {"schemaVersion": 1, "status": "PASS", "results": results}, indent=2
            )
        )
        return 0
    except (VerificationError, KeyError, ValueError, OSError) as error:
        print(json.dumps({"schemaVersion": 1, "status": "FAIL", "error": str(error)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
