from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


gen = load("generate_distribution")
verify = load("verify_published_release")
COMMIT = "a" * 40  # Structural fixture identity, never native acceptance.
FILES = (
    "integrations/cursor/README.md",
    "integrations/cursor/commands/terraphim-setup.md",
    "integrations/cursor/hook_adapter.py",
    "integrations/cursor/mcp.json.example",
    "integrations/cursor/hooks.json.example",
    "integrations/cursor/policy.json.example",
    "integrations/cursor/release-inputs.json",
    "schemas/cursor-hook-policy.schema.json",
    "schemas/cursor-hook-receipt.schema.json",
)


def sha(data):
    return hashlib.sha256(data).hexdigest()


class CursorDistributionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "source"
        self.root.mkdir()
        for name in ("skills", "assets"):
            shutil.copytree(ROOT / name, self.root / name)
        for name in ("LICENSE", "NOTICE"):
            shutil.copyfile(ROOT / name, self.root / name)
        self.metadata = copy.deepcopy(gen.load_metadata(ROOT))
        self.metadata["plugin"]["version"] = "0.2.7"
        self.metadata["cursor_integration"] = {
            "schema_version": 1,
            "files": list(FILES),
        }
        for name in FILES:
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("Public structural packaging fixture.\n")
        (self.root / "distribution").mkdir()
        self.save_metadata()
        for path, content in gen.generated_files(self.root, self.metadata).items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)

    def tearDown(self):
        self.temp.cleanup()

    def save_metadata(self):
        (self.root / "distribution/metadata.json").write_text(json.dumps(self.metadata))

    def build(self, name="output"):
        return gen.build_cursor_archive(
            self.root, self.metadata, Path(self.temp.name) / name, COMMIT
        )

    def test_only_cursor_declares_nested_command(self):
        generated = gen.generated_files(self.root, self.metadata)
        for path, content in generated.items():
            manifest = json.loads(content)
            if path.relative_to(self.root).as_posix() == ".cursor-plugin/plugin.json":
                self.assertEqual(
                    ["integrations/cursor/commands/terraphim-setup.md"],
                    manifest["commands"],
                )
            else:
                self.assertFalse({"commands", "hooks", "mcpServers"} & manifest.keys())

    def test_historical_cursor_manifest_stays_instruction_only(self):
        old = copy.deepcopy(self.metadata)
        del old["cursor_integration"]
        old["plugin"]["version"] = "0.2.6"
        self.assertNotIn("commands", gen.render_cursor(old))

    def test_archive_is_exact_reproducible_and_keeps_signed_skills(self):
        first = self.build()
        second = self.build("again")
        self.assertEqual(first.read_bytes(), second.read_bytes())
        with zipfile.ZipFile(first) as package:
            names = package.namelist()
            self.assertEqual(len(names), len(set(names)))
            self.assertIn(".cursor-plugin/plugin.json", names)
            self.assertIn("cursor-provenance.json", names)
            provenance = json.loads(package.read("cursor-provenance.json"))
            self.assertEqual(COMMIT, provenance["sourceCommit"])
            self.assertEqual(
                set(names) - {"cursor-provenance.json"}, set(provenance["files"])
            )
            for member in package.infolist():
                self.assertEqual(0o100644, member.external_attr >> 16)
                if member.filename != "cursor-provenance.json":
                    self.assertEqual(
                        sha(package.read(member)), provenance["files"][member.filename]
                    )
                if member.filename.startswith("skills/") or member.filename in (
                    "NOTICE",
                    "LICENSE",
                ):
                    self.assertEqual(
                        (self.root / member.filename).read_bytes(), package.read(member)
                    )

    def test_missing_explicit_member_is_refused(self):
        (self.root / FILES[0]).unlink()
        with self.assertRaises(ValueError):
            self.build()

    def test_symlink_member_is_refused(self):
        member = self.root / FILES[0]
        member.unlink()
        member.symlink_to(self.root / "LICENSE")
        with self.assertRaises(ValueError):
            self.build()

    def test_source_identity_and_member_paths_are_strict(self):
        for commit in ("main", "a" * 39, "A" * 40):
            with self.subTest(commit=commit), self.assertRaises(ValueError):
                gen.build_cursor_archive(
                    self.root, self.metadata, Path(self.temp.name) / "out", commit
                )
        for value in (
            "../secret",
            "/absolute",
            "integrations/cursor/../secret",
            "integrations/cursor/x\\bad",
            "integrations/cursor/x\nsecret",
        ):
            with self.subTest(path=value), self.assertRaises(ValueError):
                changed = copy.deepcopy(self.metadata)
                changed["cursor_integration"]["files"].append(value)
                gen.build_cursor_archive(
                    self.root, changed, Path(self.temp.name) / "out", COMMIT
                )

    def test_ambient_host_discovery_is_refused(self):
        (self.root / "commands").mkdir()
        (self.root / "commands/accidental.md").write_text("do not activate")
        with self.assertRaises(ValueError):
            self.build()

    def test_historical_asset_contract_is_exact_seven(self):
        old = copy.deepcopy(self.metadata)
        old["plugin"]["version"] = "0.2.6"
        del old["cursor_integration"]
        self.metadata = old
        self.save_metadata()
        gen.build_autoclaw_archives(self.root, old, self.root / "dist/autoclaw")
        paths = verify.release_asset_paths(self.root, "v0.2.6")
        self.assertEqual(7, len(paths))
        (self.root / "dist/autoclaw/extra.zip").write_bytes(b"unreviewed")
        with self.assertRaises(verify.ReleaseError):
            verify.release_asset_paths(self.root, "v0.2.6")

    def test_new_contract_requires_additive_archive(self):
        gen.build_autoclaw_archives(
            self.root, self.metadata, self.root / "dist/autoclaw"
        )
        with self.assertRaises(verify.ReleaseError):
            verify.release_asset_paths(self.root, "v0.2.7")
        archive = self.build()
        paths = verify.release_asset_paths(self.root, "v0.2.7", cursor_archive=archive)
        self.assertEqual(8, len(paths))
        checksum = next(p for p in paths if p.name == "SHA256SUMS").read_text()
        self.assertIn(f"{sha(archive.read_bytes())}  {archive.name}\n", checksum)

    def test_boolean_only_native_receipt_is_refused(self):
        archive = self.build()
        evidence = Path(self.temp.name) / "qualification"
        evidence.mkdir()
        (evidence / "native-receipt.json").write_text(
            json.dumps({"nativeRewriteQualified": True})
        )
        with self.assertRaises(verify.ReleaseError):
            verify.verify_native_qualification(
                self.root, archive, evidence, COMMIT, 1, 2
            )

    def test_absent_native_evidence_never_passes(self):
        with self.assertRaises(verify.ReleaseError):
            verify.verify_native_qualification(
                self.root, self.build(), Path(self.temp.name) / "absent", COMMIT, 1, 2
            )

    def qualification_fixture(self):
        """Structural unit-test data only; never actual native acceptance."""
        archive = self.build()
        folder = Path(self.temp.name) / "qualification-structure"
        folder.mkdir(exist_ok=True)
        package = verify.verify_cursor_archive(self.root, archive, COMMIT)
        outputs = {
            "outputs/installed.json": json.dumps(
                {"archiveSha256": package["sha256"], "files": package["files"]}
            ).encode(),
            "outputs/vendor.json": json.dumps(
                {
                    "status": "VALID",
                    "version": "3.24.18",
                    "commit": "be4c9e5350d77747b42cd467cbd3370a753d4640",
                    "argv": ["structural-fixture-only"],
                    "exitCode": 0,
                }
            ).encode(),
            "outputs/observed.txt": b"STRUCTURAL UNIT TEST; NOT A NATIVE OUTPUT OR QUALIFICATION.\n",
            "inputs/public.txt": b"Explicitly classified input fixture.\n",
        }
        manifest = {}
        for name, data in outputs.items():
            target = folder / name
            target.parent.mkdir(exist_ok=True)
            target.write_bytes(data)
            manifest[name] = {
                "sha256": sha(data),
                "bytes": len(data),
                "kind": "input" if name.startswith("inputs/") else "output",
            }
        record = {
            "schemaVersion": 1,
            "kind": "cursor-native-qualification",
            "sourceCommit": COMMIT,
            "candidate": {
                "runId": 1,
                "artifactId": 2,
                "archive": archive.name,
                "sha256": package["sha256"],
            },
            "host": {
                "platform": "darwin-arm64",
                "version": "3.24.18",
                "commit": "be4c9e5350d77747b42cd467cbd3370a753d4640",
                "vendorEvidence": "outputs/vendor.json",
                "installedManifest": "outputs/installed.json",
            },
            "capabilities": {
                "nativeRewriteQualified": True,
                "automaticFailureCaptureAvailable": False,
            },
            "files": manifest,
            "cases": [
                {
                    "id": f"C-{i:02d}",
                    "status": "PASS",
                    "scope": "native",
                    "evidence": ["outputs/observed.txt"],
                    "argv": ["structural-fixture-only"],
                }
                for i in range(1, 10)
            ],
            "rewriteChecks": {
                key: "outputs/observed.txt"
                for key in [
                    "rewrite",
                    "rewriteOff",
                    "guardOriginal",
                    "guardReplacement",
                    "crash",
                    "timeout",
                    "nonzeroExit",
                    "noOutput",
                    "malformedResponse",
                ]
            },
            "captureChecks": {
                key: "outputs/observed.txt"
                for key in ["disabledNoWrite", "missingExitNoWrite", "correlation"]
            },
        }
        inputs = {}
        for label in (
            "policy",
            "roleConfig",
            "compiledRules",
            "guardRules",
            "settings",
        ):
            name = f"inputs/{label}.json"
            data = json.dumps({"structural_fixture": label}).encode()
            (folder / name).write_bytes(data)
            manifest[name] = {"sha256": sha(data), "bytes": len(data), "kind": "input"}
            inputs[label] = sha(data)
        ids = ["structural-conversation", "structural-generation", "structural-call"]
        selected = "/public/fixture/derived.json"
        result = json.dumps({"fixture": "derived output; not native evidence"}).encode()
        post = {
            "hook_event_name": "postToolUse",
            "cursor_version": "3.24.18",
            "tool_name": "Shell",
            "conversation_id": ids[0],
            "generation_id": ids[1],
            "tool_use_id": ids[2],
            "command": "python3 validate_brief.py --check",
            "resultShape": {"output": "str", "exitCode": 0},
            "observedUnixNs": 2,
        }
        completed = {
            "schemaVersion": 1,
            "state": "completed",
            "exitCode": 0,
            "attemptedCommand": "python3 validate_brief.py --chek",
            "appliedCommand": post["command"],
            "createdAtNs": 1,
            "callKey": sha(json.dumps(ids, ensure_ascii=True).encode()),
            "policySha256": inputs["policy"],
            "identities": {
                **{
                    k: inputs[k]
                    for k in ("roleConfig", "compiledRules", "guardRules", "settings")
                },
                "adapter": package["files"]["integrations/cursor/hook_adapter.py"],
                "agent": "bff31dc42d6d1a99bf51291039d7719c6a48c2326e582e5e24eaa1eaf11e17ec",
            },
            "selectedOutputs": [selected],
            "artifacts": [
                {"path": selected, "sha256": sha(result), "bytes": len(result)}
            ],
        }
        for name, data in [
            ("outputs/derived.json", result),
            ("outputs/post.json", json.dumps(post).encode()),
            ("outputs/completed.json", json.dumps(completed).encode()),
        ]:
            (folder / name).write_bytes(data)
            manifest[name] = {"sha256": sha(data), "bytes": len(data), "kind": "output"}
        record["rewriteChecks"]["rewrite"] = "outputs/completed.json"
        record["rewriteExecution"] = {
            "postEvent": "outputs/post.json",
            "selectedOutputs": {selected: "outputs/derived.json"},
        }
        self.write_structural_review(folder, record)
        return archive, folder, record

    def write_structural_review(self, folder, record):
        raw = (json.dumps(record, indent=2) + "\n").encode()
        (folder / "native-receipt.json").write_bytes(raw)
        review = {
            "schemaVersion": 1,
            "status": "PASS",
            "sourceCommit": COMMIT,
            "reviewer": "STRUCTURAL UNIT TEST ONLY",
            "nativeReceiptSha256": sha(raw),
            "evidenceHashes": {
                name: value["sha256"] for name, value in record["files"].items()
            },
        }
        (folder / "review.json").write_text(json.dumps(review))

    def test_structural_receipt_admission_is_not_artifact_or_native_proof(self):
        archive, folder, _record = self.qualification_fixture()
        result = verify.verify_native_qualification(
            self.root, archive, folder, COMMIT, 1, 2
        )
        self.assertEqual(result["archiveSha256"], sha(archive.read_bytes()))
        self.assertNotIn("qualificationArtifact", result)
        self.assertFalse(result["capabilities"]["automaticFailureCaptureAvailable"])
        # Only admit_native_artifacts adds trusted same-repository run and Git
        # evidence-tree provenance. These local fixture bytes never enter it.

    def test_source_candidate_host_and_evidence_mutations_refuse(self):
        archive, folder, original = self.qualification_fixture()
        changes = [
            lambda r: r.update(sourceCommit="b" * 40),
            lambda r: r["candidate"].update(runId=True),
            lambda r: r["candidate"].update(artifactId=3),
            lambda r: r["candidate"].update(sha256="0" * 64),
            lambda r: r["host"].update(platform="linux-arm64"),
            lambda r: r["host"].update(version="3.24.19"),
            lambda r: r["capabilities"].update(nativeRewriteQualified=False),
            lambda r: r["capabilities"].update(automaticFailureCaptureAvailable=0),
            lambda r: r["capabilities"].update(automaticFailureCaptureAvailable=True),
            lambda r: r["cases"].pop(),
            lambda r: r["cases"][0].update(status="NOT_RUN"),
            lambda r: r["cases"][0].update(scope="static"),
            lambda r: r["cases"][0].update(evidence=["inputs/public.txt"]),
            lambda r: r["cases"][0].update(argv=[]),
            lambda r: r["rewriteChecks"].pop("guardReplacement"),
            lambda r: r["rewriteChecks"].update(rewrite="inputs/public.txt"),
            lambda r: r["captureChecks"].pop("disabledNoWrite"),
            lambda r: r["files"]["outputs/observed.txt"].update(sha256="0" * 64),
            lambda r: r["files"]["outputs/observed.txt"].update(bytes=True),
        ]
        for index, change in enumerate(changes):
            record = copy.deepcopy(original)
            change(record)
            self.write_structural_review(folder, record)
            with self.subTest(index=index), self.assertRaises(verify.ReleaseError):
                verify.verify_native_qualification(
                    self.root, archive, folder, COMMIT, 1, 2
                )

    def test_stale_review_changed_output_and_extra_file_refuse(self):
        archive, folder, record = self.qualification_fixture()
        review = json.loads((folder / "review.json").read_text())
        review["nativeReceiptSha256"] = "0" * 64
        (folder / "review.json").write_text(json.dumps(review))
        with self.assertRaises(verify.ReleaseError):
            verify.verify_native_qualification(self.root, archive, folder, COMMIT, 1, 2)
        self.write_structural_review(folder, record)
        target = folder / "outputs/observed.txt"
        original = target.read_bytes()
        target.write_bytes(original + b"changed")
        with self.assertRaises(verify.ReleaseError):
            verify.verify_native_qualification(self.root, archive, folder, COMMIT, 1, 2)
        target.write_bytes(original)
        (folder / "unreviewed.txt").write_text("extra")
        with self.assertRaises(verify.ReleaseError):
            verify.verify_native_qualification(self.root, archive, folder, COMMIT, 1, 2)

    def test_duplicate_json_link_and_missing_vendor_result_refuse(self):
        archive, folder, record = self.qualification_fixture()
        (folder / "native-receipt.json").write_text(
            '{"schemaVersion":1,"schemaVersion":1}'
        )
        with self.assertRaises(verify.ReleaseError):
            verify.verify_native_qualification(self.root, archive, folder, COMMIT, 1, 2)
        self.write_structural_review(folder, record)
        target = folder / "outputs/observed.txt"
        target.unlink()
        target.symlink_to(folder / "inputs/public.txt")
        with self.assertRaises(verify.ReleaseError):
            verify.verify_native_qualification(self.root, archive, folder, COMMIT, 1, 2)

    def test_additive_checksums_cannot_overwrite_committed_sums(self):
        gen.build_autoclaw_archives(
            self.root, self.metadata, self.root / "dist/autoclaw"
        )
        archive = gen.build_cursor_archive(
            self.root, self.metadata, self.root / "dist/autoclaw", COMMIT
        )
        before = (self.root / "dist/autoclaw/SHA256SUMS").read_bytes()
        with self.assertRaises(verify.ReleaseError):
            verify.release_asset_paths(self.root, "v0.2.7", cursor_archive=archive)
        self.assertEqual(before, (self.root / "dist/autoclaw/SHA256SUMS").read_bytes())

    def test_artifact_extraction_rejects_paths_links_and_duplicates(self):
        import io
        import warnings

        for name, mode, duplicate in [
            ("../escape", 0o100644, False),
            ("a/../b", 0o100644, False),
            ("x", 0o120777, False),
            ("x", 0o100644, True),
            ("a\\b", 0o100644, False),
        ]:
            stream = io.BytesIO()
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                with zipfile.ZipFile(stream, "w") as package:
                    info = zipfile.ZipInfo(name)
                    info.external_attr = mode << 16
                    package.writestr(info, b"actual archive member")
                    if duplicate:
                        package.writestr(info, b"duplicate")
            with (
                tempfile.TemporaryDirectory() as output,
                self.subTest(name=name, mode=mode, duplicate=duplicate),
                self.assertRaises(verify.ReleaseError),
            ):
                verify._extract_artifact(stream.getvalue(), Path(output))
                self.assertEqual(list(Path(output).iterdir()), [])

    def test_actual_package_local_markdown_links_are_included(self):
        import posixpath
        import re

        metadata = gen.load_metadata(ROOT)
        payload = gen.cursor_payload(ROOT, metadata)
        for name, body in payload.items():
            if not name.endswith(".md"):
                continue
            for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", body.decode("utf-8")):
                if target.startswith(("https://", "http://", "mailto:", "#")):
                    continue
                resolved = posixpath.normpath(
                    posixpath.join(posixpath.dirname(name), target.split("#", 1)[0])
                )
                self.assertIn(resolved, payload, (name, target))

    def test_artifact_origin_and_run_mutations_refuse(self):
        artifact = {
            "id": 2,
            "name": "cursor-integration-candidate",
            "expired": False,
            "size_in_bytes": 100,
            "workflow_run": {"id": 1, "head_sha": COMMIT},
        }
        run = {
            "id": 1,
            "status": "completed",
            "conclusion": "success",
            "head_branch": "main",
            "event": "push",
            "path": ".github/workflows/validate.yml",
            "head_repository": {"full_name": verify.REPOSITORY},
            "head_sha": COMMIT,
        }
        self.assertEqual(
            verify.validate_artifact_identity(artifact, run, 2, artifact["name"])[
                "sourceCommit"
            ],
            COMMIT,
        )
        mutations = [
            ("artifact", "id", True),
            ("artifact", "expired", True),
            ("artifact", "size_in_bytes", True),
            ("artifact", "size_in_bytes", verify.MAX_ASSET_BYTES + 1),
            ("artifact", "name", "other"),
            ("artifact", "workflow_run", None),
            ("run", "id", 3),
            ("run", "conclusion", "failure"),
            ("run", "status", "in_progress"),
            ("run", "head_branch", "feature"),
            ("run", "event", "pull_request"),
            ("run", "path", ".github/workflows/untrusted.yml"),
            ("run", "head_sha", "b" * 40),
            ("run", "head_repository", {"full_name": "other/fork"}),
            ("run", "head_repository", None),
        ]
        for kind, key, value in mutations:
            changed_artifact, changed_run = copy.deepcopy(artifact), copy.deepcopy(run)
            (changed_artifact if kind == "artifact" else changed_run)[key] = value
            with (
                self.subTest(kind=kind, key=key, value=value),
                self.assertRaises(verify.ReleaseError),
            ):
                verify.validate_artifact_identity(
                    changed_artifact, changed_run, 2, artifact["name"]
                )

    def test_committed_qualification_uses_real_git_blob_identities(self):
        import subprocess

        _archive, folder, _record = self.qualification_fixture()
        entries = []
        for path in sorted(folder.rglob("*")):
            if path.is_file():
                actual_git_hash = (
                    subprocess.run(
                        ["git", "hash-object", "--stdin"],
                        input=path.read_bytes(),
                        capture_output=True,
                        check=True,
                    )
                    .stdout.decode()
                    .strip()
                )
                entries.append(
                    {
                        "path": f"qualification/cursor/0.2.7/{path.relative_to(folder).as_posix()}",
                        "mode": "100644",
                        "type": "blob",
                        "sha": actual_git_hash,
                    }
                )
        tree = {"truncated": False, "tree": entries}
        result = verify.verify_qualification_tree(folder, tree, COMMIT, "0.2.7")
        self.assertEqual(len(result["files"]), len(entries))
        changes = [
            lambda t: t.update(truncated=True),
            lambda t: t["tree"][0].update(sha="0" * 40),
            lambda t: t["tree"][0].update(mode="120000"),
            lambda t: t["tree"].pop(),
            lambda t: t["tree"].append(copy.deepcopy(t["tree"][0])),
            lambda t: t["tree"][0].update(path="qualification/cursor/0.2.7/../escape"),
        ]
        for index, change in enumerate(changes):
            changed = copy.deepcopy(tree)
            change(changed)
            with self.subTest(index=index), self.assertRaises(verify.ReleaseError):
                verify.verify_qualification_tree(folder, changed, COMMIT, "0.2.7")

    def test_ci_requires_exact_released_protocol_tests_and_no_skips(self):
        for name in ("validate.yml", "release.yml"):
            workflow = (ROOT / ".github/workflows" / name).read_text()
            self.assertIn("runs-on: ubuntu-24.04-arm", workflow)
            self.assertIn("CURSOR_TEST_AGENT:", workflow)
            self.assertIn("not result.skipped", workflow)
            self.assertIn(
                "cf09f161ff42180308509d8e9b43b66c94bedd3801987cd1112b38b3718b5789",
                workflow,
            )
            self.assertIn(
                "5ae520c7034dd125dc6ccb0f6a2f7233794e4bef254381f292566827988f9c52",
                workflow,
            )
        release = (ROOT / ".github/workflows/release.yml").read_text()
        self.assertIn("needs: [validate, protocol-contracts]", release)
        self.assertNotIn("release upload", release)
        self.assertNotIn("--clobber", release)

    def test_native_rewrite_chain_mutations_fail_even_with_fresh_review_hashes(self):
        archive, folder, record = self.qualification_fixture()
        original = (folder / "outputs/completed.json").read_bytes()
        changes = [
            lambda r: r.update(state="applied"),
            lambda r: r.update(exitCode=1),
            lambda r: r.update(attemptedCommand=r["appliedCommand"]),
            lambda r: r.update(callKey="0" * 64),
            lambda r: r["identities"].update(adapter="0" * 64),
            lambda r: r["identities"].update(agent="0" * 64),
            lambda r: r["identities"].update(settings="0" * 64),
            lambda r: r.update(policySha256="0" * 64),
            lambda r: r["artifacts"][0].update(sha256="0" * 64),
            lambda r: r.update(selectedOutputs=[]),
            lambda r: r.update(createdAtNs=3),
        ]
        for index, change in enumerate(changes):
            value = json.loads(original)
            change(value)
            raw = json.dumps(value).encode()
            (folder / "outputs/completed.json").write_bytes(raw)
            record["files"]["outputs/completed.json"].update(
                sha256=sha(raw), bytes=len(raw)
            )
            self.write_structural_review(folder, record)
            with self.subTest(index=index), self.assertRaises(verify.ReleaseError):
                verify.verify_native_qualification(
                    self.root, archive, folder, COMMIT, 1, 2
                )

    def test_copied_input_cannot_qualify_executed_rewrite_output(self):
        archive, folder, record = self.qualification_fixture()
        raw = (folder / "inputs/public.txt").read_bytes()
        (folder / "outputs/derived.json").write_bytes(raw)
        record["files"]["outputs/derived.json"].update(sha256=sha(raw), bytes=len(raw))
        completed = json.loads((folder / "outputs/completed.json").read_text())
        completed["artifacts"][0].update(sha256=sha(raw), bytes=len(raw))
        data = json.dumps(completed).encode()
        (folder / "outputs/completed.json").write_bytes(data)
        record["files"]["outputs/completed.json"].update(
            sha256=sha(data), bytes=len(data)
        )
        self.write_structural_review(folder, record)
        with self.assertRaises(verify.ReleaseError):
            verify.verify_native_qualification(self.root, archive, folder, COMMIT, 1, 2)

    def test_actual_post_event_status_command_and_correlation_are_required(self):
        archive, folder, record = self.qualification_fixture()
        original = (folder / "outputs/post.json").read_bytes()
        changes = [
            lambda r: r.update(tool_use_id="other"),
            lambda r: r.update(command="different"),
            lambda r: r.update(hook_event_name="postToolUseFailure"),
            lambda r: r.update(cursor_version="other"),
            lambda r: r["resultShape"].update(exitCode=True),
            lambda r: r["resultShape"].pop("exitCode"),
        ]
        for index, change in enumerate(changes):
            value = json.loads(original)
            change(value)
            raw = json.dumps(value).encode()
            (folder / "outputs/post.json").write_bytes(raw)
            record["files"]["outputs/post.json"].update(sha256=sha(raw), bytes=len(raw))
            self.write_structural_review(folder, record)
            with self.subTest(index=index), self.assertRaises(verify.ReleaseError):
                verify.verify_native_qualification(
                    self.root, archive, folder, COMMIT, 1, 2
                )

    def test_missing_signed_skill_body_or_manifest_refuses_archive(self):
        for name in ("SKILL.md", "skill.toml"):
            path = self.root / "skills/terraphim-grep" / name
            data = path.read_bytes()
            path.unlink()
            try:
                with self.subTest(name=name), self.assertRaises(ValueError):
                    self.build()
            finally:
                path.write_bytes(data)

    def test_missing_signed_skill_directory_refuses_archive(self):
        shutil.rmtree(self.root / "skills/terraphim-editor")
        with self.assertRaises(ValueError):
            self.build()

    def write_file_bound_structural_review(self, folder, record):
        """Rebind test-only review to actual files, including malformed records."""
        raw = (json.dumps(record, indent=2) + "\n").encode()
        (folder / "native-receipt.json").write_bytes(raw)
        hashes = {
            path.relative_to(folder).as_posix(): sha(path.read_bytes())
            for path in folder.rglob("*")
            if path.is_file()
            and path.name not in ("native-receipt.json", "review.json")
        }
        (folder / "review.json").write_text(
            json.dumps(
                {
                    "schemaVersion": 1,
                    "status": "PASS",
                    "sourceCommit": COMMIT,
                    "reviewer": "STRUCTURAL UNIT TEST ONLY",
                    "nativeReceiptSha256": sha(raw),
                    "evidenceHashes": hashes,
                }
            )
        )

    def test_malformed_evidence_manifest_is_rejected_after_review_rebinding(self):
        archive, folder, original = self.qualification_fixture()
        values = [None, [], {}, {str(i): {} for i in range(257)}]
        for value in values:
            record = copy.deepcopy(original)
            record["files"] = value
            self.write_file_bound_structural_review(folder, record)
            with (
                self.subTest(value_type=type(value).__name__),
                self.assertRaisesRegex(
                    verify.ReleaseError, "actual evidence file manifest required"
                ),
            ):
                verify.verify_native_qualification(
                    self.root, archive, folder, COMMIT, 1, 2
                )
        for descriptor in [
            None,
            [],
            {},
            {"sha256": "0" * 64, "bytes": 1, "kind": "claim"},
        ]:
            record = copy.deepcopy(original)
            record["files"]["outputs/observed.txt"] = descriptor
            self.write_file_bound_structural_review(folder, record)
            with (
                self.subTest(descriptor=descriptor),
                self.assertRaisesRegex(
                    verify.ReleaseError, "invalid evidence file descriptor"
                ),
            ):
                verify.verify_native_qualification(
                    self.root, archive, folder, COMMIT, 1, 2
                )

    def test_host_and_capability_objects_cannot_be_replaced_by_truthy_values(self):
        archive, folder, original = self.qualification_fixture()
        for field, message in [
            ("host", "host identity must be an object"),
            ("capabilities", "capability record must be an object"),
        ]:
            for value in [None, True, ["PASS"], "PASS"]:
                record = copy.deepcopy(original)
                record[field] = value
                self.write_file_bound_structural_review(folder, record)
                with (
                    self.subTest(field=field, value=value),
                    self.assertRaisesRegex(verify.ReleaseError, message),
                ):
                    verify.verify_native_qualification(
                        self.root, archive, folder, COMMIT, 1, 2
                    )

    def test_installed_payload_and_vendor_claims_refuse_with_valid_file_digests(self):
        archive, folder, original = self.qualification_fixture()
        mutations = {
            "outputs/installed.json": [
                ("archiveSha256", "0" * 64),
                ("files", {}),
                ("files", {"integrations/cursor/hook_adapter.py": "0" * 64}),
            ],
            "outputs/vendor.json": [
                ("status", "NOT_RUN"),
                ("version", "other"),
                ("commit", "0" * 40),
                ("argv", []),
                ("argv", "codesign"),
                ("argv", [True]),
                ("exitCode", True),
                ("exitCode", 1),
            ],
        }
        for name, cases in mutations.items():
            target = folder / name
            original_bytes = target.read_bytes()
            for key, value in cases:
                document = json.loads(original_bytes)
                document[key] = value
                raw = json.dumps(document).encode()
                target.write_bytes(raw)
                record = copy.deepcopy(original)
                record["files"][name].update(sha256=sha(raw), bytes=len(raw))
                self.write_file_bound_structural_review(folder, record)
                message = (
                    "actual installed payload differs"
                    if "installed" in name
                    else "vendor verification evidence is incomplete"
                )
                with (
                    self.subTest(name=name, key=key, value=value),
                    self.assertRaisesRegex(verify.ReleaseError, message),
                ):
                    verify.verify_native_qualification(
                        self.root, archive, folder, COMMIT, 1, 2
                    )
            target.write_bytes(original_bytes)

    def test_oversized_actual_evidence_refuses_even_with_correct_digests(self):
        archive, folder, record = self.qualification_fixture()
        raw = b"x" * (2 * 1024 * 1024 + 1)
        (folder / "outputs/observed.txt").write_bytes(raw)
        record["files"]["outputs/observed.txt"].update(sha256=sha(raw), bytes=len(raw))
        self.write_file_bound_structural_review(folder, record)
        with self.assertRaisesRegex(
            verify.ReleaseError, "actual evidence bytes differ"
        ):
            verify.verify_native_qualification(self.root, archive, folder, COMMIT, 1, 2)

    def test_rewrite_execution_requires_actual_bounded_output_mapping(self):
        archive, folder, original = self.qualification_fixture()
        for value, message in [
            (None, "native rewrite execution chain is required"),
            ({}, "native rewrite execution chain is required"),
            (
                {
                    "postEvent": "outputs/post.json",
                    "selectedOutputs": {},
                    "extra": True,
                },
                "native rewrite execution chain is required",
            ),
            (
                {"postEvent": "inputs/public.txt", "selectedOutputs": {}},
                "native post event and selected outputs are required",
            ),
            (
                {"postEvent": "outputs/post.json", "selectedOutputs": []},
                "native post event and selected outputs are required",
            ),
            (
                {"postEvent": "outputs/post.json", "selectedOutputs": {}},
                "native post event and selected outputs are required",
            ),
            (
                {
                    "postEvent": "outputs/post.json",
                    "selectedOutputs": {
                        str(i): "outputs/derived.json" for i in range(17)
                    },
                },
                "native post event and selected outputs are required",
            ),
        ]:
            record = copy.deepcopy(original)
            record["rewriteExecution"] = value
            self.write_file_bound_structural_review(folder, record)
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(verify.ReleaseError, message),
            ):
                verify.verify_native_qualification(
                    self.root, archive, folder, COMMIT, 1, 2
                )

    def test_completed_rewrite_descriptor_and_selected_target_are_exact(self):
        archive, folder, original = self.qualification_fixture()
        target = folder / "outputs/completed.json"
        source = json.loads(target.read_text())
        for descriptor, message in [
            (None, "invalid completed output descriptor"),
            (
                {"path": source["selectedOutputs"][0]},
                "invalid completed output descriptor",
            ),
            (
                {**source["artifacts"][0], "path": "/unselected"},
                "completed output path differs",
            ),
            ({**source["artifacts"][0], "path": True}, "completed output path differs"),
        ]:
            completed = copy.deepcopy(source)
            completed["artifacts"] = [descriptor]
            raw = json.dumps(completed).encode()
            target.write_bytes(raw)
            record = copy.deepcopy(original)
            record["files"]["outputs/completed.json"].update(
                sha256=sha(raw), bytes=len(raw)
            )
            self.write_file_bound_structural_review(folder, record)
            with (
                self.subTest(descriptor=descriptor),
                self.assertRaisesRegex(verify.ReleaseError, message),
            ):
                verify.verify_native_qualification(
                    self.root, archive, folder, COMMIT, 1, 2
                )
        raw = json.dumps(source).encode()
        target.write_bytes(raw)
        for value in ["inputs/public.txt", "outputs/absent.json", True]:
            record = copy.deepcopy(original)
            record["files"]["outputs/completed.json"].update(
                sha256=sha(raw), bytes=len(raw)
            )
            record["rewriteExecution"]["selectedOutputs"][
                source["selectedOutputs"][0]
            ] = value
            self.write_file_bound_structural_review(folder, record)
            with (
                self.subTest(target=value),
                self.assertRaisesRegex(
                    verify.ReleaseError,
                    "selected rewrite output is not an actual output",
                ),
            ):
                verify.verify_native_qualification(
                    self.root, archive, folder, COMMIT, 1, 2
                )

    def test_real_artifact_extraction_reads_exact_bytes_and_refuses_replacement(self):
        import io

        stream = io.BytesIO()
        members = {
            "nested/source.txt": b"Unicode: \xce\xbb\r\n",
            "result.json": b'{"result":1}\n',
        }
        with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as archive:
            for name, data in members.items():
                archive.writestr(name, data)
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            verify._extract_artifact(stream.getvalue(), folder)
            self.assertEqual(
                members, {name: (folder / name).read_bytes() for name in members}
            )
            with self.assertRaisesRegex(
                verify.ReleaseError, "cannot safely extract artifact"
            ):
                verify._extract_artifact(stream.getvalue(), folder)
            self.assertEqual(
                members, {name: (folder / name).read_bytes() for name in members}
            )
        for count in [0, 513]:
            stream = io.BytesIO()
            with zipfile.ZipFile(stream, "w") as archive:
                for index in range(count):
                    archive.writestr(str(index), b"bounded input")
            with tempfile.TemporaryDirectory() as temporary:
                folder = Path(temporary)
                with (
                    self.subTest(count=count),
                    self.assertRaisesRegex(
                        verify.ReleaseError, "artifact member bounds exceeded"
                    ),
                ):
                    verify._extract_artifact(stream.getvalue(), folder)
                self.assertEqual([], list(folder.iterdir()))

    def test_release_notes_link_only_exact_qualified_source_and_digests(self):
        admission = {
            "status": "PASS_REVIEWED_NATIVE_EVIDENCE",
            "sourceCommit": COMMIT,
            "archiveSha256": "1" * 64,
            "nativeReceiptSha256": "2" * 64,
            "reviewSha256": "3" * 64,
            "qualificationSource": {
                "sourceCommit": "b" * 40,
                "path": "qualification/cursor/0.2.7/",
            },
        }
        notes = verify.native_release_notes(admission, "v0.2.7")
        self.assertIn(
            "https://github.com/terraphim/terraphim-cursor-plugin/blob/"
            + "b" * 40
            + "/qualification/cursor/0.2.7/native-receipt.json",
            notes,
        )
        self.assertIn("Native receipt SHA256: `" + "2" * 64 + "`", notes)
        self.assertIn("Independent review SHA256: `" + "3" * 64 + "`", notes)
        self.assertIn("macOS ARM64", notes)
        mutations = [
            lambda r: r.update(status="NOT_RUN"),
            lambda r: r.update(sourceCommit="main"),
            lambda r: r.update(nativeReceiptSha256="a" * 63 + "\n"),
            lambda r: r.update(reviewSha256="`injected`"),
            lambda r: r["qualificationSource"].update(sourceCommit="main"),
            lambda r: r["qualificationSource"].update(
                path="qualification/cursor/0.2.7/../escape/"
            ),
            lambda r: r["qualificationSource"].update(
                path="qualification/cursor/0.2.6/"
            ),
            lambda r: r["qualificationSource"].update(path="https://example.invalid/"),
        ]
        for index, change in enumerate(mutations):
            changed = copy.deepcopy(admission)
            change(changed)
            with self.subTest(index=index), self.assertRaises(verify.ReleaseError):
                verify.native_release_notes(changed, "v0.2.7")
        with self.assertRaises(verify.ReleaseError):
            verify.native_release_notes(admission, "v0.2.7\n# injected")

    def test_release_notes_are_not_written_without_native_admission(self):
        import subprocess
        import sys

        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            notes = folder / "release.md"
            receipt = folder / "receipt.json"
            for native_args in ([], ["--native-only"]):
                command = [
                    sys.executable,
                    str(ROOT / "scripts/verify_published_release.py"),
                    "--root",
                    str(self.root),
                    "--tag",
                    "v0.2.7",
                    "--receipt",
                    str(receipt),
                    "--release-notes",
                    str(notes),
                    *native_args,
                ]
                result = subprocess.run(
                    command, capture_output=True, text=True, timeout=10
                )
                self.assertEqual(result.returncode, 1)
                self.assertEqual(json.loads(receipt.read_text())["status"], "FAIL")
                self.assertFalse(notes.exists())
        workflow = (ROOT / ".github/workflows/release.yml").read_text()
        publish = workflow.split("  publish:\n", 1)[1]
        self.assertIn('--release-notes "$RUNNER_TEMP/cursor-release-notes.md"', publish)
        self.assertIn('--notes-file "$RUNNER_TEMP/cursor-release-notes.md"', publish)
        self.assertNotIn("--generate-notes", publish)


if __name__ == "__main__":
    unittest.main()
