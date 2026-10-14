"""Real signed source, imported files and malicious tar regression cases."""

from __future__ import annotations

import gzip
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import tarfile
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "verify_kilo", ROOT / "scripts/verify_kilo_distribution.py"
)
assert SPEC and SPEC.loader
V = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(V)
INPUTS = json.loads((ROOT / "integrations/kilo/release-inputs.json").read_text())
ID = "terraphim-grep"
FIXTURE = ROOT / "tests/fixtures/kilo" / ID


class KiloDistributionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.imported = self.root / ID
        shutil.copytree(FIXTURE, self.imported)

    def archive(self, extras=(), *, omit=None):
        """Create a real tar archive without ever extracting it."""
        path = self.root / "skill.tar.gz"
        with tarfile.open(path, "w:gz", format=tarfile.PAX_FORMAT) as archive:
            for file in sorted(self.imported.rglob("*")):
                if (
                    file.is_file()
                    and file.name not in ("local.patch", "local.remove")
                    and file.name != omit
                ):
                    archive.add(
                        file,
                        arcname=f"{ID}/{file.relative_to(self.imported)}",
                        recursive=False,
                    )
            for member, payload in extras:
                archive.addfile(member, io.BytesIO(payload))
        return path

    def test_actual_official_import_matches_pinned_tree_and_original_body(self):
        receipt = V.verify_import(ROOT / "skills" / ID, self.imported, INPUTS, ID)
        self.assertEqual("PASS", receipt["status"])
        self.assertNotIn("skill.toml", receipt["archiveFiles"])
        self.assertIn("NOTICE", receipt["archiveFiles"])
        self.assertIn("references/kilo-provenance.json", receipt["archiveFiles"])

    def test_all_original_skills_have_exact_admitted_file_hashes(self):
        for name in INPUTS["skills"]:
            self.assertEqual(
                INPUTS["skills"][name]["sourceFiles"],
                V.read_tree(ROOT / "skills" / name),
            )

    def test_actual_signed_sources_verify_with_pinned_official_tsm(self):
        executable = os.environ.get("TERRAPHIM_TSM_VERIFIER")
        if not executable:
            self.skipTest(
                "Set TERRAPHIM_TSM_VERIFIER to the pinned official tsm binary; CI requires it"
            )
        for name in INPUTS["skills"]:
            receipt = V.verify_source(
                ROOT / "skills" / name, INPUTS, name, Path(executable)
            )
            self.assertEqual("PASS", receipt["status"])
            self.assertEqual(INPUTS["publisherKey"], receipt["publisherKey"])

    def test_untrusted_verifier_is_refused_before_execution(self):
        executable = self.root / "not-a-verifier"
        executable.write_text("#!/bin/sh\ntouch unexpected-execution\n")
        executable.chmod(0o755)
        with self.assertRaisesRegex(V.VerificationError, "verifier identity"):
            V.verify_source(ROOT / "skills" / ID, INPUTS, ID, executable)
        self.assertFalse((Path.cwd() / "unexpected-execution").exists())

    def test_publisher_key_is_pinned_independently_of_manifest(self):
        inputs = json.loads(json.dumps(INPUTS))
        inputs["publisherKey"] = "0" * 64
        with self.assertRaisesRegex(V.VerificationError, "publisher"):
            V.verify_import(ROOT / "skills" / ID, self.imported, inputs, ID)

    def test_source_manifest_or_payload_changes_are_refused(self):
        for rel in ["skill.toml", "SKILL.md"]:
            source = self.root / ("source-" + rel.replace(".", "-"))
            shutil.copytree(ROOT / "skills" / ID, source)
            with (source / rel).open("ab") as file:
                file.write(b"changed")
            with self.assertRaisesRegex(V.VerificationError, "source"):
                V.verify_import(source, self.imported, INPUTS, ID)

    def test_undeclared_source_file_is_refused(self):
        source = self.root / "source"
        shutil.copytree(ROOT / "skills" / ID, source)
        (source / "unlisted.txt").write_text("not signed")
        with self.assertRaisesRegex(V.VerificationError, "source"):
            V.verify_import(source, self.imported, INPUTS, ID)

    def test_semantic_change_refused_even_if_import_digest_is_recomputed(self):
        skill = self.imported / "SKILL.md"
        skill.write_text(
            skill.read_text().replace(
                "bounded, offline search", "unrestricted online execution"
            )
        )
        inputs = json.loads(json.dumps(INPUTS))
        inputs["skills"][ID]["import"]["files"] = V.read_tree(self.imported)
        with self.assertRaisesRegex(V.VerificationError, "body"):
            V.verify_import(ROOT / "skills" / ID, self.imported, inputs, ID)

    def test_binary_resources_may_not_be_normalized(self):
        self.assertEqual(b"abc\x00 \r\n", V.normalized_resource(b"abc\x00 \r\n"))
        self.assertEqual(b"\xff \r\n", V.normalized_resource(b"\xff \r\n"))
        self.assertEqual(b"abc\n", V.normalized_resource(b"abc \r\n\n"))

    def test_license_notice_provenance_signature_and_controls_are_required(self):
        for rel in [
            "LICENSE",
            "NOTICE",
            "references/kilo-provenance.json",
            "local.remove",
            "local.patch",
        ]:
            with self.subTest(rel=rel):
                file = self.imported / rel
                data = file.read_bytes()
                file.unlink()
                with self.assertRaises(V.VerificationError):
                    V.verify_import(ROOT / "skills" / ID, self.imported, INPUTS, ID)
                file.write_bytes(data)
        (self.imported / "skill.toml").write_bytes(
            (ROOT / "skills" / ID / "skill.toml").read_bytes()
        )
        with self.assertRaises(V.VerificationError):
            V.verify_import(ROOT / "skills" / ID, self.imported, INPUTS, ID)

    def test_import_symlinks_and_duplicate_normalized_paths_are_refused(self):
        (self.imported / "link").symlink_to(ROOT / "README.md")
        with self.assertRaisesRegex(V.VerificationError, "symlink"):
            V.read_tree(self.imported)
        (self.imported / "link").unlink()
        for names in [("A.txt", "a.txt"), ("caf\u00e9", "cafe\u0301")]:
            # Test names directly: macOS filesystems may alias these on creation.
            with self.assertRaisesRegex(V.VerificationError, "collision"):
                V.validate_names(names)

    def test_actual_archive_round_trip_matches_all_payload_files(self):
        receipt = V.verify_archive(self.archive(), INPUTS, ID)
        self.assertEqual("PASS", receipt["status"])
        self.assertEqual(
            hashlib.sha256((self.root / "skill.tar.gz").read_bytes()).hexdigest(),
            receipt["sha256"],
        )

    def test_archive_refuses_unsafe_names_types_duplicates_and_extra_files(self):
        cases = [
            ("../escape", tarfile.REGTYPE),
            ("/absolute", tarfile.REGTYPE),
            (ID + "/..\\escape", tarfile.REGTYPE),
            ("other/SKILL.md", tarfile.REGTYPE),
            (ID + "/SKILL.md", tarfile.REGTYPE),
            (ID + "/skill.md", tarfile.REGTYPE),
            (ID + "/extra", tarfile.REGTYPE),
            (ID + "/link", tarfile.SYMTYPE),
            (ID + "/hardlink", tarfile.LNKTYPE),
            (ID + "/device", tarfile.CHRTYPE),
            (ID + "/fifo", tarfile.FIFOTYPE),
        ]
        for name, kind in cases:
            with self.subTest(name=name, kind=kind):
                member = tarfile.TarInfo(name)
                member.type = kind
                member.linkname = (
                    "/etc/passwd" if kind in (tarfile.SYMTYPE, tarfile.LNKTYPE) else ""
                )
                member.size = 1 if kind == tarfile.REGTYPE else 0
                with self.assertRaises(V.VerificationError):
                    V.verify_archive(self.archive([(member, b"x")]), INPUTS, ID)

    def test_archive_refuses_missing_and_changed_payload(self):
        with self.assertRaises(V.VerificationError):
            V.verify_archive(self.archive(omit="NOTICE"), INPUTS, ID)
        (self.imported / "NOTICE").write_text("changed")
        with self.assertRaises(V.VerificationError):
            V.verify_archive(self.archive(), INPUTS, ID)

    def test_archive_file_and_compressed_limits(self):
        member = tarfile.TarInfo(ID + "/large")
        member.size = V.MAX_FILE_BYTES + 1
        with self.assertRaisesRegex(V.VerificationError, "size"):
            V.verify_archive(self.archive([(member, b"x" * member.size)]), INPUTS, ID)
        path = self.root / "too-big.gz"
        with path.open("wb") as file:
            file.truncate(V.MAX_ARCHIVE_BYTES + 1)
        with self.assertRaisesRegex(V.VerificationError, "compressed"):
            V.verify_archive(path, INPUTS, ID)

    def test_gzip_expansion_and_malformed_archive_are_bounded(self):
        path = self.root / "bomb.gz"
        with gzip.open(path, "wb") as file:
            for _ in range(V.MAX_TAR_BYTES // (1024 * 1024) + 1):
                file.write(b"\x00" * (1024 * 1024))
        with self.assertRaisesRegex(V.VerificationError, "expanded tar"):
            V.verify_archive(path, INPUTS, ID)
        path.write_bytes(b"not gzip")
        with self.assertRaises(V.VerificationError):
            V.verify_archive(path, INPUTS, ID)

    def test_archive_refuses_nonzero_trailing_bytes_and_second_tar(self):
        path = self.archive()
        raw = gzip.decompress(path.read_bytes())
        second = io.BytesIO()
        with tarfile.open(fileobj=second, mode="w") as archive:
            member = tarfile.TarInfo("../outside.txt")
            member.size = 1
            archive.addfile(member, io.BytesIO(b"x"))
        for tail in [b"uninspected trailing bytes", second.getvalue()]:
            path.write_bytes(gzip.compress(raw + tail))
            with self.assertRaisesRegex(V.VerificationError, "trailing"):
                V.verify_archive(path, INPUTS, ID)

    def test_path_and_count_limits(self):
        with self.assertRaises(V.VerificationError):
            V.validate_names(["x" * (V.MAX_PATH_BYTES + 1)])
        with self.assertRaises(V.VerificationError):
            V.validate_names(["a//b"])
        for n in range(V.MAX_FILES + 1):
            (self.root / f"file-{n}").touch()
        with self.assertRaisesRegex(V.VerificationError, "count"):
            V.read_tree(self.root)


if __name__ == "__main__":
    unittest.main()
