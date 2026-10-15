#!/usr/bin/env python3
"""Read back every immutable public release asset and compare reviewed bytes."""

from __future__ import annotations
import argparse
import hashlib
import importlib.util
import io
import subprocess
import tempfile
import zipfile
import json
from pathlib import Path
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

REPOSITORY = "terraphim/terraphim-cursor-plugin"
MAX_ASSET_BYTES = 32 * 1024 * 1024


class ReleaseError(RuntimeError):
    """Published bytes do not satisfy the reviewed release contract."""


def _read(url: str, timeout: float, limit: int) -> bytes:
    try:
        with urlopen(
            Request(url, headers={"User-Agent": "terraphim-release-readback/1"}),
            timeout=timeout,
        ) as response:
            if response.status != 200:
                raise ReleaseError(f"HTTP {response.status} for {url}")
            data = response.read(limit + 1)
            if len(data) > limit:
                raise ReleaseError(f"response exceeds byte limit: {url}")
            return data
    except HTTPError as error:
        error.close()
        raise ReleaseError(f"HTTP {error.code} for {url}") from error
    except (URLError, TimeoutError, OSError) as error:
        raise ReleaseError(f"cannot read {url}: {error}") from error


def _generator():
    spec = importlib.util.spec_from_file_location(
        "cursor_distribution", Path(__file__).with_name("generate_distribution.py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _json_file(path: Path) -> dict:
    try:
        raw = path.read_bytes()
        if len(raw) > 2 * 1024 * 1024:
            raise ReleaseError("JSON evidence exceeds byte limit")

        def pairs(values):
            result = {}
            for key, value in values:
                if key in result:
                    raise ReleaseError("duplicate JSON key")
                result[key] = value
            return result

        value = json.loads(
            raw,
            object_pairs_hook=pairs,
            parse_constant=lambda _: (_ for _ in ()).throw(
                ReleaseError("nonfinite JSON")
            ),
        )
        if not isinstance(value, dict):
            raise ReleaseError("JSON evidence must be an object")
        return value
    except (OSError, ValueError, UnicodeError, RecursionError) as error:
        raise ReleaseError(f"invalid JSON evidence: {path.name}") from error


def _safe_file(root: Path, name: str) -> Path:
    if not _generator().safe_member(name):
        raise ReleaseError("noncanonical evidence path")
    root = root.resolve()
    for index in range(1, len(Path(name).parts) + 1):
        if (root / Path(*Path(name).parts[:index])).is_symlink():
            raise ReleaseError("linked evidence is forbidden")
    path = root / name
    if not path.is_file() or not path.resolve().is_relative_to(root):
        raise ReleaseError("evidence file is missing or escaping")
    return path


def _archive_members(archive: Path) -> dict[str, bytes]:
    """Read regular, bounded ZIP members without trusting extraction paths."""
    try:
        if archive.stat().st_size > MAX_ASSET_BYTES:
            raise ReleaseError("archive exceeds byte limit")
        with zipfile.ZipFile(archive) as package:
            members = package.infolist()
            if (
                len(members) > 512
                or sum(item.file_size for item in members) > MAX_ASSET_BYTES
            ):
                raise ReleaseError("archive payload exceeds limits")
            result = {}
            for item in members:
                if (
                    not _generator().safe_member(item.filename)
                    or item.filename in result
                    or item.flag_bits & 1
                    or item.is_dir()
                    or item.external_attr >> 16 != 0o100644
                    or item.file_size > 2 * 1024 * 1024
                ):
                    raise ReleaseError("unsafe, duplicate or oversized archive member")
                result[item.filename] = package.read(item)
            return result
    except (OSError, ValueError, zipfile.BadZipFile, RuntimeError) as error:
        if isinstance(error, ReleaseError):
            raise
        raise ReleaseError("invalid archive") from error


def verify_cursor_archive(root: Path, archive: Path, source_commit: str) -> dict:
    """Rebuild exact package bytes from admitted source, including provenance."""
    try:
        generator = _generator()
        metadata = generator.load_metadata(root)
        with tempfile.TemporaryDirectory() as temporary:
            expected = generator.build_cursor_archive(
                root, metadata, Path(temporary), source_commit
            )
            if (
                archive.name != expected.name
                or archive.read_bytes() != expected.read_bytes()
            ):
                raise ReleaseError("integration archive differs from exact source")
        members = _archive_members(archive)
        return {
            "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
            "files": {
                name: hashlib.sha256(data).hexdigest() for name, data in members.items()
            },
        }
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise ReleaseError("cannot rebuild exact integration archive") from error


def release_asset_paths(
    root: Path, tag: str, *, cursor_archive: Path | None = None
) -> list[Path]:
    """Exact historical seven-asset contract, or eight with the integration."""
    metadata = _json_file(root / "distribution/metadata.json")
    version = metadata.get("plugin", {}).get("version")
    if tag != f"v{version}":
        raise ReleaseError("source version differs from release tag")
    skills = (
        "terraphim-grep",
        "terraphim-agent-learn",
        "terraphim-agent-memory",
        "terraphim-editor",
    )
    names = {f"{name}-{version}.zip" for name in skills}
    dist = root / "dist/autoclaw"
    if {path.name for path in dist.glob("*.zip")} != names:
        raise ReleaseError(
            "source skill asset set is not the exact four-skill contract"
        )
    paths = [dist / name for name in sorted(names)]
    checksum = dist / "SHA256SUMS"
    expected_sums = "".join(
        f"{hashlib.sha256((dist / f'{name}-{version}.zip').read_bytes()).hexdigest()}  {name}-{version}.zip\n"
        for name in skills
    )
    if checksum.read_text() != expected_sums:
        raise ReleaseError("source skill checksums differ")
    if metadata.get("cursor_integration") is not None:
        if (
            cursor_archive is None
            or not cursor_archive.is_file()
            or cursor_archive.name != f"terraphim-cursor-integration-{version}.zip"
        ):
            raise ReleaseError("new release requires the additive integration archive")
        # Keep committed skill checksums unchanged; the CI-built checksum file
        # includes the additional integration archive for this release only.
        if cursor_archive.parent.resolve() == dist.resolve():
            raise ReleaseError(
                "additive release checksum must stay outside committed skill assets"
            )
        checksum = cursor_archive.parent / "SHA256SUMS"
        checksum.write_text(
            expected_sums
            + f"{hashlib.sha256(cursor_archive.read_bytes()).hexdigest()}  {cursor_archive.name}\n"
        )
        paths.append(cursor_archive)
    elif cursor_archive is not None:
        raise ReleaseError("historical release cannot acquire an integration asset")
    paths.extend(
        [
            checksum,
            root / "assets/v-model-overview.svg",
            root / "assets/v-model-overview.png",
        ]
    )
    if any(not path.is_file() or path.is_symlink() for path in paths):
        raise ReleaseError("source release assets missing or linked")
    return paths


def verify_rewrite_chain(
    receipt: dict, folder: Path, package: dict, outputs: set[str]
) -> dict:
    """Bind attempted/applied/executed commands to actual selected output bytes."""
    execution = receipt.get("rewriteExecution")
    if not isinstance(execution, dict) or set(execution) != {
        "postEvent",
        "selectedOutputs",
    }:
        raise ReleaseError("native rewrite execution chain is required")
    post_ref = execution["postEvent"]
    mapping = execution["selectedOutputs"]
    if (
        not isinstance(post_ref, str)
        or post_ref not in outputs
        or not isinstance(mapping, dict)
        or not 0 < len(mapping) <= 16
    ):
        raise ReleaseError("native post event and selected outputs are required")
    completed = _json_file(_safe_file(folder, receipt["rewriteChecks"]["rewrite"]))
    post = _json_file(_safe_file(folder, post_ref))
    attempted, applied = (
        completed.get("attemptedCommand"),
        completed.get("appliedCommand"),
    )
    if (
        type(completed.get("schemaVersion")) is not int
        or completed["schemaVersion"] != 1
        or completed.get("state") != "completed"
        or type(completed.get("exitCode")) is not int
        or completed["exitCode"] != 0
        or not isinstance(attempted, str)
        or not isinstance(applied, str)
        or not attempted
        or not applied
        or attempted == applied
        or any(
            "\0" in command or len(command.encode("utf-8")) > 16384
            for command in (attempted, applied)
        )
    ):
        raise ReleaseError("completed native rewrite with actual zero exit is required")
    identities = completed.get("identities")
    if (
        not isinstance(identities, dict)
        or set(identities)
        != {"adapter", "agent", "roleConfig", "compiledRules", "guardRules", "settings"}
        or identities["adapter"]
        != package["files"]["integrations/cursor/hook_adapter.py"]
        or identities["agent"]
        != "bff31dc42d6d1a99bf51291039d7719c6a48c2326e582e5e24eaa1eaf11e17ec"
    ):
        raise ReleaseError(
            "rewrite did not use the installed adapter and selected released agent"
        )
    input_hashes = {
        item["sha256"] for item in receipt["files"].values() if item["kind"] == "input"
    }
    if completed.get("policySha256") not in input_hashes or any(
        not isinstance(identities[key], str) or identities[key] not in input_hashes
        for key in ("roleConfig", "compiledRules", "guardRules", "settings")
    ):
        raise ReleaseError(
            "actual rewrite policy/config/rules/settings inputs are missing"
        )
    ids = [post.get(key) for key in ("conversation_id", "generation_id", "tool_use_id")]
    result = post.get("resultShape")
    if (
        post.get("hook_event_name") != "postToolUse"
        or post.get("tool_name") != "Shell"
        or post.get("cursor_version") != receipt["host"]["version"]
        or post.get("command") != applied
        or not isinstance(result, dict)
        or set(result) != {"output", "exitCode"}
        or result["output"] != "str"
        or type(result["exitCode"]) is not int
        or result["exitCode"] != 0
        or any(not isinstance(value, str) or not 0 < len(value) <= 256 for value in ids)
        or completed.get("callKey")
        != hashlib.sha256(json.dumps(ids, ensure_ascii=True).encode()).hexdigest()
    ):
        raise ReleaseError(
            "actual post event does not correlate with applied command and zero exit"
        )
    if (
        {
            "user_email",
            "model",
            "transcript_path",
            "tool_output",
            "messages",
            "environment",
        }
        & set(post)
        or type(completed.get("createdAtNs")) is not int
        or type(post.get("observedUnixNs")) is not int
        or not 0 < completed["createdAtNs"] <= post["observedUnixNs"]
    ):
        raise ReleaseError("native event timing or privacy boundary differs")
    selected = completed.get("selectedOutputs")
    artifacts = completed.get("artifacts")
    if (
        not isinstance(selected, list)
        or any(not isinstance(name, str) for name in selected)
        or len(selected) != len(set(selected))
        or set(selected) != set(mapping)
        or not isinstance(artifacts, list)
        or len(artifacts) != len(selected)
    ):
        raise ReleaseError("completed rewrite lacks its exact selected output set")
    seen = set()
    verified = {}
    for artifact in artifacts:
        if not isinstance(artifact, dict) or set(artifact) != {
            "path",
            "sha256",
            "bytes",
        }:
            raise ReleaseError("invalid completed output descriptor")
        source = artifact["path"]
        if not isinstance(source, str) or source not in mapping or source in seen:
            raise ReleaseError("completed output path differs")
        seen.add(source)
        target = mapping[source]
        if not isinstance(target, str) or target not in outputs:
            raise ReleaseError("selected rewrite output is not an actual output")
        data = _safe_file(folder, target).read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        if (
            type(artifact["bytes"]) is not int
            or len(data) != artifact["bytes"]
            or len(data) > 1024 * 1024
            or artifact["sha256"] != digest
            or digest in input_hashes
        ):
            raise ReleaseError(
                "selected output is stale, copied input or differs from completed record"
            )
        verified[target] = {"sha256": digest, "bytes": len(data)}
    return {
        "attemptedCommand": attempted,
        "appliedCommand": applied,
        "executedCommand": post["command"],
        "exitCode": post["resultShape"]["exitCode"],
        "callKey": completed["callKey"],
        "outputs": verified,
    }


def verify_native_qualification(
    root: Path,
    archive: Path,
    folder: Path,
    source_commit: str,
    candidate_run_id: int,
    candidate_artifact_id: int,
) -> dict:
    """Admit reviewed actual-output evidence; booleans alone never qualify."""
    package = verify_cursor_archive(root, archive, source_commit)
    receipt_path = _safe_file(folder, "native-receipt.json")
    receipt = _json_file(receipt_path)
    review = _json_file(_safe_file(folder, "review.json"))
    if (
        type(receipt.get("schemaVersion")) is not int
        or receipt.get("schemaVersion") != 1
        or receipt.get("kind") != "cursor-native-qualification"
        or receipt.get("sourceCommit") != source_commit
    ):
        raise ReleaseError("native evidence identity differs")
    candidate = receipt.get("candidate")
    if (
        not isinstance(candidate, dict)
        or type(candidate.get("runId")) is not int
        or type(candidate.get("artifactId")) is not int
        or type(candidate_run_id) is not int
        or type(candidate_artifact_id) is not int
        or candidate_run_id <= 0
        or candidate_artifact_id <= 0
    ):
        raise ReleaseError("candidate IDs must be positive integers")
    if candidate != {
        "runId": candidate_run_id,
        "artifactId": candidate_artifact_id,
        "archive": archive.name,
        "sha256": package["sha256"],
    }:
        raise ReleaseError("native evidence is not bound to candidate artifact")
    if (
        type(review.get("schemaVersion")) is not int
        or review.get("schemaVersion") != 1
        or review.get("status") != "PASS"
        or review.get("sourceCommit") != source_commit
        or not isinstance(review.get("reviewer"), str)
        or not review["reviewer"].strip()
        or review.get("nativeReceiptSha256")
        != hashlib.sha256(receipt_path.read_bytes()).hexdigest()
    ):
        raise ReleaseError("independent review is missing or stale")
    files = receipt.get("files")
    if not isinstance(files, dict) or not files or len(files) > 256:
        raise ReleaseError("actual evidence file manifest required")
    hashes = {}
    outputs = set()
    total = 0
    for name, item in files.items():
        if (
            not isinstance(item, dict)
            or set(item) != {"sha256", "bytes", "kind"}
            or item["kind"] not in ("input", "output")
        ):
            raise ReleaseError("invalid evidence file descriptor")
        path = _safe_file(folder, name)
        data = path.read_bytes()
        total += len(data)
        if (
            len(data) > 2 * 1024 * 1024
            or total > MAX_ASSET_BYTES
            or type(item["bytes"]) is not int
            or len(data) != item["bytes"]
            or hashlib.sha256(data).hexdigest() != item["sha256"]
        ):
            raise ReleaseError("actual evidence bytes differ")
        hashes[name] = item["sha256"]
        if item["kind"] == "output" and data:
            outputs.add(name)
    actual = {
        path.relative_to(folder).as_posix()
        for path in folder.rglob("*")
        if path.is_file() or path.is_symlink()
    }
    if (
        actual != set(files) | {"native-receipt.json", "review.json"}
        or review.get("evidenceHashes") != hashes
    ):
        raise ReleaseError("reviewed evidence tree differs")
    host = receipt.get("host", {})
    if not isinstance(host, dict):
        raise ReleaseError("host identity must be an object")
    if (
        host.get("platform") != "darwin-arm64"
        or host.get("version") != "3.24.18"
        or host.get("commit") != "be4c9e5350d77747b42cd467cbd3370a753d4640"
        or host.get("vendorEvidence") not in outputs
        or host.get("installedManifest") not in outputs
    ):
        raise ReleaseError(
            "actual released Cursor identity/signature/install evidence missing"
        )
    installed = _json_file(folder / host["installedManifest"])
    if (
        installed.get("archiveSha256") != package["sha256"]
        or installed.get("files") != package["files"]
    ):
        raise ReleaseError("actual installed payload differs from candidate")
    vendor = _json_file(folder / host["vendorEvidence"])
    if (
        vendor.get("status") != "VALID"
        or vendor.get("version") != host["version"]
        or vendor.get("commit") != host["commit"]
        or not isinstance(vendor.get("argv"), list)
        or not vendor["argv"]
        or not all(isinstance(arg, str) for arg in vendor["argv"])
        or type(vendor.get("exitCode")) is not int
        or vendor["exitCode"] != 0
    ):
        raise ReleaseError("vendor verification evidence is incomplete")
    capabilities = receipt.get("capabilities", {})
    if not isinstance(capabilities, dict):
        raise ReleaseError("capability record must be an object")
    if (
        capabilities.get("nativeRewriteQualified") is not True
        or type(capabilities.get("automaticFailureCaptureAvailable")) is not bool
    ):
        raise ReleaseError("native rewrite is mandatory for the whole update")
    cases = receipt.get("cases")
    ids = {f"C-{index:02d}" for index in range(1, 10)}
    if (
        not isinstance(cases, list)
        or len(cases) != 9
        or any(not isinstance(item, dict) for item in cases)
        or {item.get("id") for item in cases if isinstance(item, dict)} != ids
    ):
        raise ReleaseError("all pre-publication C-01 through C-09 cases required")
    for case in cases:
        refs = case.get("evidence")
        if (
            case.get("status") != "PASS"
            or case.get("scope") != "native"
            or not isinstance(refs, list)
            or not refs
            or any(not isinstance(ref, str) for ref in refs)
            or not set(refs) <= outputs
        ):
            raise ReleaseError("native case lacks actual hashed outputs")
        argv = case.get("argv")
        if (
            not (
                isinstance(argv, list)
                and argv
                and all(isinstance(value, str) for value in argv)
            )
            and case.get("uiEvidence") not in outputs
        ):
            raise ReleaseError("native case lacks actual argv or UI record")
    checks = receipt.get("rewriteChecks", {})
    required = {
        "rewrite",
        "rewriteOff",
        "guardOriginal",
        "guardReplacement",
        "crash",
        "timeout",
        "nonzeroExit",
        "noOutput",
        "malformedResponse",
    }
    if (
        not isinstance(checks, dict)
        or set(checks) != required
        or any(
            not isinstance(value, str) or value not in outputs
            for value in checks.values()
        )
    ):
        raise ReleaseError("mandatory rewrite and host-failure checks lack outputs")
    capture = receipt.get("captureChecks", {})
    required_capture = {"disabledNoWrite", "missingExitNoWrite", "correlation"}
    if capabilities["automaticFailureCaptureAvailable"]:
        required_capture |= {
            "actualNonzeroCapture",
            "storageAdmission",
            "savedLearningReadback",
        }
    if (
        not isinstance(capture, dict)
        or set(capture) != required_capture
        or any(
            not isinstance(value, str) or value not in outputs
            for value in capture.values()
        )
    ):
        raise ReleaseError("capture scope lacks actual qualification outputs")
    chain = verify_rewrite_chain(receipt, folder, package, outputs)
    return {
        "status": "PASS_REVIEWED_NATIVE_EVIDENCE",
        "sourceCommit": source_commit,
        "archiveSha256": package["sha256"],
        "nativeReceiptSha256": hashlib.sha256(receipt_path.read_bytes()).hexdigest(),
        "reviewSha256": hashlib.sha256(
            (folder / "review.json").read_bytes()
        ).hexdigest(),
        "evidenceHashes": hashes,
        "rewriteExecution": chain,
        "capabilities": capabilities,
        "scope": "Reviewed pre-publication native evidence; not public delivery or curated admission.",
    }


def _gh(endpoint: str, *, binary: bool = False):
    """Use GitHub's CLI for authenticated same-repository artifact downloads."""
    with tempfile.TemporaryFile() as output:
        try:
            result = subprocess.run(
                ["gh", "api", "--method", "GET", endpoint],
                stdout=output,
                stderr=subprocess.PIPE,
                timeout=60,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            raise ReleaseError("GitHub artifact request failed") from error
        if result.returncode or output.tell() > MAX_ASSET_BYTES:
            raise ReleaseError("GitHub artifact request failed or exceeded limit")
        output.seek(0)
        data = output.read()
    if binary:
        return data
    try:
        return json.loads(data)
    except (ValueError, UnicodeError) as error:
        raise ReleaseError("GitHub metadata is not JSON") from error


def validate_artifact_identity(
    artifact: dict, run: dict, artifact_id: int, expected_name: str
) -> dict:
    """Admit metadata for the existing successful main validation workflow."""
    if type(artifact_id) is not int or artifact_id <= 0:
        raise ReleaseError("invalid artifact ID")
    if not isinstance(artifact, dict) or not isinstance(
        artifact.get("workflow_run"), dict
    ):
        raise ReleaseError("artifact metadata lacks a workflow run")
    workflow_run = artifact["workflow_run"]
    run_id = workflow_run.get("id")
    if type(run_id) is not int or run_id <= 0:
        raise ReleaseError("artifact has no run identity")
    if not isinstance(run, dict) or not isinstance(run.get("head_repository"), dict):
        raise ReleaseError("workflow metadata lacks source repository")
    if (
        type(artifact.get("id")) is not int
        or artifact["id"] != artifact_id
        or artifact.get("name") != expected_name
        or artifact.get("expired") is not False
        or type(artifact.get("size_in_bytes")) is not int
        or not 0 < artifact["size_in_bytes"] <= MAX_ASSET_BYTES
        or type(run.get("id")) is not int
        or run["id"] != run_id
        or run.get("status") != "completed"
        or run.get("conclusion") != "success"
        or run.get("head_branch") != "main"
        or run.get("event") not in ("push", "workflow_dispatch")
        or run.get("path") != ".github/workflows/validate.yml"
        or run["head_repository"].get("full_name") != REPOSITORY
        or run.get("head_sha") != workflow_run.get("head_sha")
        or not re.fullmatch(r"[0-9a-f]{40}", str(run.get("head_sha")))
    ):
        raise ReleaseError(
            "artifact is not from successful same-repository main validation"
        )
    return {"runId": run_id, "artifactId": artifact_id, "sourceCommit": run["head_sha"]}


def _artifact(
    artifact_id: int, expected_name: str, expected_digest: str | None = None
) -> tuple[bytes, dict]:
    if type(artifact_id) is not int or artifact_id <= 0:
        raise ReleaseError("invalid artifact ID")
    prefix = f"repos/{REPOSITORY}/actions"
    artifact = _gh(f"{prefix}/artifacts/{artifact_id}")
    if not isinstance(artifact, dict) or not isinstance(
        artifact.get("workflow_run"), dict
    ):
        raise ReleaseError("artifact metadata lacks a workflow run")
    run_id = artifact["workflow_run"].get("id")
    if type(run_id) is not int or run_id <= 0:
        raise ReleaseError("artifact has no run identity")
    run = _gh(f"{prefix}/runs/{run_id}")
    admitted = validate_artifact_identity(artifact, run, artifact_id, expected_name)
    data = _gh(f"{prefix}/artifacts/{artifact_id}/zip", binary=True)
    digest = hashlib.sha256(data).hexdigest()
    if (
        artifact.get("digest") != f"sha256:{digest}"
        or expected_digest is not None
        and digest != expected_digest
    ):
        raise ReleaseError("immutable artifact digest differs")
    return data, {**admitted, "sha256": digest}


def _extract_artifact(data: bytes, destination: Path) -> None:
    """Extract only bounded regular members to a fresh private directory."""
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as package:
            members = package.infolist()
            if (
                not members
                or len(members) > 512
                or sum(item.file_size for item in members) > MAX_ASSET_BYTES
            ):
                raise ReleaseError("artifact member bounds exceeded")
            seen = set()
            for item in members:
                mode = item.external_attr >> 16
                if (
                    not _generator().safe_member(item.filename)
                    or item.filename in seen
                    or item.is_dir()
                    or item.flag_bits & 1
                    or mode & 0o170000 not in (0, 0o100000)
                    or item.file_size > MAX_ASSET_BYTES
                ):
                    raise ReleaseError("unsafe artifact member")
                seen.add(item.filename)
            for item in members:
                path = destination / item.filename
                path.parent.mkdir(parents=True, exist_ok=True)
                with path.open("xb") as target:
                    target.write(package.read(item))
    except (OSError, ValueError, RuntimeError, zipfile.BadZipFile) as error:
        if isinstance(error, ReleaseError):
            raise
        raise ReleaseError("cannot safely extract artifact") from error


def verify_qualification_tree(
    folder: Path, tree: dict, commit: str, version: str
) -> dict:
    """Compare artifact bytes with the exact committed Git blob tree."""
    if not re.fullmatch(r"[0-9a-f]{40}", commit) or not re.fullmatch(
        r"[0-9]+\.[0-9]+\.[0-9]+(?:-[A-Za-z0-9.-]+)?", version
    ):
        raise ReleaseError("invalid qualification source identity")
    prefix = f"qualification/cursor/{version}/"
    if (
        not isinstance(tree, dict)
        or tree.get("truncated") is not False
        or not isinstance(tree.get("tree"), list)
    ):
        raise ReleaseError("qualification source tree is incomplete")
    expected = {}
    for entry in tree["tree"]:
        if not isinstance(entry, dict):
            raise ReleaseError("invalid source tree member")
        name = entry.get("path", "")
        if not isinstance(name, str):
            raise ReleaseError("invalid source tree path")
        if name.startswith(prefix) and entry.get("type") != "tree":
            if entry.get("type") != "blob" or entry.get("mode") != "100644":
                raise ReleaseError("qualification source contains a nonregular member")
            relative = name.removeprefix(prefix)
            if (
                not _generator().safe_member(relative)
                or relative in expected
                or not re.fullmatch(r"[0-9a-f]{40}", str(entry.get("sha")))
            ):
                raise ReleaseError("invalid or duplicate qualification source member")
            expected[relative] = entry["sha"]
    actual = {}
    for path in folder.rglob("*"):
        if path.is_file() or path.is_symlink():
            relative = path.relative_to(folder).as_posix()
            data = _safe_file(folder, relative).read_bytes()
            actual[relative] = hashlib.sha1(
                f"blob {len(data)}\0".encode() + data
            ).hexdigest()
    if not expected or actual != expected:
        raise ReleaseError(
            "qualification artifact differs from immutable source evidence"
        )
    return {"sourceCommit": commit, "path": prefix, "files": expected}


def admit_native_artifacts(
    root: Path,
    archive: Path,
    source_commit: str,
    qualification_id: int,
    qualification_sha256: str,
) -> dict:
    """Bind native evidence and exact candidate to trusted immutable CI artifacts."""
    if not re.fullmatch(r"[0-9a-f]{64}", qualification_sha256):
        raise ReleaseError("qualification artifact SHA256 is required")
    data, qualification = _artifact(
        qualification_id, "cursor-native-qualification", qualification_sha256
    )
    with tempfile.TemporaryDirectory() as temporary:
        folder = Path(temporary) / "qualification"
        folder.mkdir()
        _extract_artifact(data, folder)
        receipt = _json_file(folder / "native-receipt.json")
        if not isinstance(receipt.get("candidate"), dict):
            raise ReleaseError("native candidate identity required")
        candidate_id = receipt["candidate"].get("artifactId")
        candidate_data, candidate = _artifact(
            candidate_id, "cursor-integration-candidate"
        )
        if (
            candidate["sourceCommit"] != source_commit
            or receipt.get("sourceCommit") != source_commit
        ):
            raise ReleaseError("signed tag and qualified candidate source differ")
        candidate_folder = Path(temporary) / "candidate"
        candidate_folder.mkdir()
        _extract_artifact(candidate_data, candidate_folder)
        if {p.name for p in candidate_folder.iterdir()} != {
            archive.name,
            "candidate.json",
        }:
            raise ReleaseError("candidate artifact payload differs")
        if (candidate_folder / archive.name).read_bytes() != archive.read_bytes():
            raise ReleaseError("candidate artifact differs from release archive")
        manifest = _json_file(candidate_folder / "candidate.json")
        if manifest != {
            "schemaVersion": 1,
            "sourceCommit": source_commit,
            "archive": archive.name,
            "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        }:
            raise ReleaseError("candidate manifest differs")
        result = verify_native_qualification(
            root, archive, folder, source_commit, candidate["runId"], candidate_id
        )
        version = _json_file(root / "distribution/metadata.json")["plugin"]["version"]
        tree = _gh(
            f"repos/{REPOSITORY}/git/trees/{qualification['sourceCommit']}?recursive=1"
        )
        result["qualificationSource"] = verify_qualification_tree(
            folder, tree, qualification["sourceCommit"], version
        )
        result["candidateArtifact"] = candidate
        result["qualificationArtifact"] = qualification
        return result


def native_release_notes(admission: dict, tag: str) -> str:
    """Link the exact admitted public qualification without interpolating free text."""
    if not isinstance(tag, str) or not re.fullmatch(
        r"v[0-9]+\.[0-9]+\.[0-9]+(?:-[A-Za-z0-9.-]+)?", tag
    ):
        raise ReleaseError("invalid release notes tag")
    if (
        not isinstance(admission, dict)
        or admission.get("status") != "PASS_REVIEWED_NATIVE_EVIDENCE"
    ):
        raise ReleaseError("release notes require admitted native evidence")
    qualification = admission.get("qualificationSource")
    if (
        not isinstance(qualification, dict)
        or qualification.get("path") != f"qualification/cursor/{tag[1:]}/"
    ):
        raise ReleaseError("release notes qualification path differs")
    for commit in (admission.get("sourceCommit"), qualification.get("sourceCommit")):
        if not isinstance(commit, str) or not re.fullmatch(r"[0-9a-f]{40}", commit):
            raise ReleaseError("release notes require immutable source identities")
    for field in ("archiveSha256", "nativeReceiptSha256", "reviewSha256"):
        value = admission.get(field)
        if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
            raise ReleaseError("release notes require exact qualification digests")
    base = f"https://github.com/{REPOSITORY}/blob/{qualification['sourceCommit']}/{qualification['path']}"
    return (
        f"Terraphim Skills Introduction {tag} includes the four signed skills and the Cursor integration archive.\n\n"
        "The reviewed Cursor qualification covers macOS ARM64. "
        f"[Actual capability record and saved-output references]({base}native-receipt.json) "
        f"and [independent review]({base}review.json) are bound to this release.\n\n"
        f"Candidate source: `{admission['sourceCommit']}`\n\n"
        f"Integration archive SHA256: `{admission['archiveSha256']}`\n\n"
        f"Native receipt SHA256: `{admission['nativeReceiptSha256']}`\n\n"
        f"Independent review SHA256: `{admission['reviewSha256']}`\n\n"
        "Marketplace admission and other native platforms remain separate qualifications.\n"
    )


def verify_release(
    root: Path,
    tag: str,
    *,
    api_url: str | None = None,
    asset_base: str | None = None,
    timeout: float = 15,
    cursor_archive: Path | None = None,
) -> dict:
    """Compare actual metadata and downloads with an already verified source tag."""
    if not re.fullmatch(r"v[0-9]+\.[0-9]+\.[0-9]+(?:-[A-Za-z0-9.-]+)?", tag):
        raise ReleaseError("invalid release tag")
    if timeout <= 0:
        raise ReleaseError("timeout must be positive")
    try:
        version = json.loads((root / "distribution/metadata.json").read_text())[
            "plugin"
        ]["version"]
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise ReleaseError("invalid source distribution metadata") from error
    if tag != f"v{version}":
        raise ReleaseError("source version differs from release tag")
    paths = release_asset_paths(root, tag, cursor_archive=cursor_archive)
    expected = {path.name: path for path in paths}
    api_url = (
        api_url or f"https://api.github.com/repos/{REPOSITORY}/releases/tags/{tag}"
    )
    asset_base = (
        asset_base or f"https://github.com/{REPOSITORY}/releases/download/{tag}/"
    )
    try:
        release = json.loads(_read(api_url, timeout, 1024 * 1024))
    except (ValueError, UnicodeError) as error:
        raise ReleaseError("release metadata is not JSON") from error
    if (
        not isinstance(release, dict)
        or release.get("tag_name") != tag
        or release.get("draft") is not False
    ):
        raise ReleaseError("release identity differs or is still a draft")
    assets = release.get("assets")
    if not isinstance(assets, list) or any(
        not isinstance(item, dict) for item in assets
    ):
        raise ReleaseError("release assets are invalid")
    names = [item.get("name") for item in assets]
    if (
        any(not isinstance(name, str) for name in names)
        or len(names) != len(set(names))
        or set(names) != set(expected)
    ):
        raise ReleaseError("release asset set differs from reviewed source")
    results = {}
    for item in assets:
        name = item["name"]
        url = asset_base + quote(name, safe="")
        source = expected[name].read_bytes()
        if (
            item.get("browser_download_url") != url
            or item.get("state") != "uploaded"
            or item.get("size") != len(source)
        ):
            raise ReleaseError(f"invalid publication metadata for {name}")
        if len(source) > MAX_ASSET_BYTES:
            raise ReleaseError(f"source asset exceeds byte limit: {name}")
        downloaded = _read(url, timeout, MAX_ASSET_BYTES)
        if downloaded != source:
            raise ReleaseError(f"public asset differs from reviewed source: {name}")
        results[name] = {
            "bytes": len(downloaded),
            "sha256": hashlib.sha256(downloaded).hexdigest(),
            "url": url,
        }
    return {
        "status": "PASS",
        "repository": REPOSITORY,
        "tag": tag,
        "assets": results,
        "scope": "Actual public downloads equal verified source assets; curated listing and native host acceptance are separate.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root", type=Path, default=Path(__file__).resolve().parents[1]
    )
    parser.add_argument("--tag", required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--cursor-archive", type=Path)
    parser.add_argument("--source-commit")
    parser.add_argument("--native-only", action="store_true")
    parser.add_argument("--qualification-artifact-id", type=int)
    parser.add_argument("--qualification-artifact-sha256")
    parser.add_argument("--check-native-folder", type=Path)
    parser.add_argument("--release-notes", type=Path)
    args = parser.parse_args()
    try:
        if args.release_notes and (not args.native_only or args.check_native_folder):
            raise ReleaseError(
                "release notes require immutable native artifact admission"
            )
        if args.check_native_folder:
            native = _json_file(args.check_native_folder / "native-receipt.json")
            source = native.get("sourceCommit", "")
            candidate = native.get("candidate", {})
            with tempfile.TemporaryDirectory() as temporary:
                generator = _generator()
                archive = generator.build_cursor_archive(
                    args.root,
                    generator.load_metadata(args.root),
                    Path(temporary),
                    source,
                )
                result = verify_native_qualification(
                    args.root,
                    archive,
                    args.check_native_folder,
                    source,
                    candidate.get("runId"),
                    candidate.get("artifactId"),
                )
            result["scope"] = (
                "Local structural/digest admission only; artifact/source provenance is checked again at release."
            )
        elif args.native_only:
            if (
                not args.cursor_archive
                or not args.source_commit
                or not args.qualification_artifact_id
                or not args.qualification_artifact_sha256
            ):
                raise ReleaseError(
                    "native qualification is required; publication remains held"
                )
            release_asset_paths(args.root, args.tag, cursor_archive=args.cursor_archive)
            result = admit_native_artifacts(
                args.root,
                args.cursor_archive,
                args.source_commit,
                args.qualification_artifact_id,
                args.qualification_artifact_sha256,
            )
            if args.release_notes:
                notes = native_release_notes(result, args.tag)
                args.release_notes.parent.mkdir(parents=True, exist_ok=True)
                args.release_notes.write_text(notes)
        else:
            if args.cursor_archive:
                if not args.source_commit:
                    raise ReleaseError("source commit required for integration archive")
                verify_cursor_archive(
                    args.root, args.cursor_archive, args.source_commit
                )
            result = verify_release(
                args.root, args.tag, cursor_archive=args.cursor_archive
            )
        status = 0
    except (ReleaseError, OSError, ValueError, KeyError, TypeError) as error:
        result = {"status": "FAIL", "tag": args.tag, "error": str(error)}
        status = 1
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))
    return status


if __name__ == "__main__":
    sys.exit(main())
