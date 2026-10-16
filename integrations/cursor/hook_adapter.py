#!/usr/bin/env python3
"""Opt-in Cursor envelope adapter for the pinned Terraphim agent, never a shell.

Native result qualification is deliberately separate from transport implementation.
No automatic learning capture or result-schema guess is enabled by this module.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import selectors
import signal
import stat
import subprocess
import sys
import time
import tomllib
import uuid

MAX_BYTES = 1024 * 1024
MAX_COMMAND_BYTES = 16 * 1024
RELEASED_AGENT_SHA256 = frozenset(
    {
        "bff31dc42d6d1a99bf51291039d7719c6a48c2326e582e5e24eaa1eaf11e17ec",
        "5ae520c7034dd125dc6ccb0f6a2f7233794e4bef254381f292566827988f9c52",
    }
)
AUTOMATIC_FAILURE_CAPTURE_AVAILABLE = False
NATIVE_SUCCESS_VERSIONS = ("3.24.18", "3.25.6")
DIGEST = re.compile(r"[0-9a-f]{64}\Z")
TERMINAL = frozenset({"completed", "denied", "incomplete", "evidence_error"})


class Refusal(Exception):
    """A bounded, non-sensitive diagnostic suitable for a deny response."""


def require(condition: bool, code: str) -> None:
    """Refuse a contract violation without including source data in the error."""
    if not condition:
        raise Refusal(code)


def exact_fields(value: object, fields: set[str], code: str) -> dict:
    """Require an object with one closed field set."""
    require(type(value) is dict and set(value) == fields, code)
    return value


def decode_json(raw: bytes) -> dict:
    """Read one bounded UTF-8 object, rejecting duplicates and unsafe numbers."""
    require(len(raw) <= MAX_BYTES, "json_size")

    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "json_duplicate_key")
            result[key] = value
        return result

    def constant(_value):
        raise Refusal("json_nonfinite")

    try:
        value = json.loads(
            raw.decode("utf-8"), object_pairs_hook=pairs, parse_constant=constant
        )
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise Refusal("json_invalid") from exc
    require(type(value) is dict, "json_object")
    pending = [(value, 1)]
    while pending:
        item, depth = pending.pop()
        require(depth <= 32, "json_depth")
        if isinstance(item, (dict, list)):
            children = item.values() if isinstance(item, dict) else item
            pending.extend(
                (child, depth + 1)
                for child in children
                if isinstance(child, (dict, list))
            )
        elif isinstance(item, float):
            require(item not in (float("inf"), -float("inf")), "json_nonfinite")

    # parse_constant handles NaN/Infinity literals; exponent overflow needs this walk.
    def finite(item):
        if isinstance(item, dict):
            return all(finite(v) for v in item.values())
        if isinstance(item, list):
            return all(finite(v) for v in item)
        return not isinstance(item, float) or abs(item) != float("inf")

    require(finite(value), "json_nonfinite")
    return value


def command(value: object) -> str:
    """Validate a command as text; never normalize or execute it."""
    require(
        type(value) is str and bool(value) and "\x00" not in value, "command_invalid"
    )
    try:
        require(len(value.encode("utf-8")) <= MAX_COMMAND_BYTES, "command_size")
    except UnicodeError as exc:
        raise Refusal("command_encoding") from exc
    return value


def checked_path(
    value: object,
    *,
    directory: bool = False,
    prospective: bool = False,
    private: bool = False,
) -> Path:
    """Admit canonical absolute paths without following symlink components."""
    require(
        type(value) is str and value.startswith("/") and "\x00" not in value,
        "path_absolute",
    )
    require(not any(part in (".", "..") for part in value.split("/")), "path_traversal")
    p = Path(value)
    require(str(p) == value, "path_canonical")
    current = Path(p.anchor)
    for index, part in enumerate(p.parts[1:]):
        current /= part
        try:
            info = current.lstat()
        except FileNotFoundError:
            require(prospective and index == len(p.parts) - 2, "path_missing")
            return p
        require(not stat.S_ISLNK(info.st_mode), "path_symlink")
    info = p.stat()
    require(
        stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode),
        "path_type",
    )
    if private:
        require(
            info.st_uid == os.getuid() and info.st_mode & 0o077 == 0, "path_private"
        )
    return p


def read_regular(value: str, *, private: bool = False) -> bytes:
    """Read a bounded regular file with final-component no-follow enforcement."""
    p = checked_path(value, private=private)
    descriptor = os.open(p, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(descriptor, "rb") as stream:
        require(stat.S_ISREG(os.fstat(stream.fileno()).st_mode), "path_type")
        raw = stream.read(MAX_BYTES + 1)
    require(len(raw) <= MAX_BYTES, "file_size")
    return raw


def file_digest(value: str) -> str:
    """Hash admitted executable bytes without loading the binary into memory."""
    p = checked_path(value)
    result = hashlib.sha256()
    descriptor = os.open(p, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(descriptor, "rb") as stream:
        require(stat.S_ISREG(os.fstat(stream.fileno()).st_mode), "path_type")
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def inside(path: Path, root: Path) -> None:
    require(path != root and path.is_relative_to(root), "path_outside")


def validate_rules(value: dict, *, empty: bool) -> dict:
    """Admit only the selected Rust compiler's actual Thesaurus representation."""
    exact_fields(value, {"name", "data"}, "rules_shape")
    require(type(value["name"]) is str and bool(value["name"]), "rules_name")
    require(type(value["data"]) is dict, "rules_data")
    if empty:
        require(not value["data"], "guard_not_empty")
    for original, term in value["data"].items():
        command(original)
        exact_fields(term, {"id", "nterm", "display_value", "pinned"}, "rule_shape")
        require(type(term["id"]) is int and 0 < term["id"] <= (2**64 - 1), "rule_id")
        require(type(term["pinned"]) is bool, "rule_pinned")
        command(term["nterm"])
        command(term["display_value"])
    return value["data"]


def validate_settings(raw: bytes, directory: Path) -> None:
    """Admit a confined, already-created local DashMap profile only."""
    try:
        value = tomllib.loads(raw.decode("utf-8"))
    except (UnicodeError, ValueError) as exc:
        raise Refusal("settings_invalid") from exc
    exact_fields(
        value,
        {
            "server_hostname",
            "api_endpoint",
            "initialized",
            "default_data_path",
            "profiles",
        },
        "settings_fields",
    )
    require(
        value["server_hostname"] in ("127.0.0.1:8000", "localhost:8000"),
        "settings_server",
    )
    require(
        value["api_endpoint"]
        in ("http://127.0.0.1:8000/api", "http://localhost:8000/api"),
        "settings_api",
    )
    require(
        value["initialized"] is True or value["initialized"] == "true",
        "settings_initialized",
    )
    data = checked_path(value["default_data_path"], directory=True, private=True)
    inside(data, directory)
    require(
        type(value["profiles"]) is dict and bool(value["profiles"]), "settings_profiles"
    )
    for profile in value["profiles"].values():
        exact_fields(profile, {"type", "root"}, "settings_profile")
        require(profile["type"] == "dashmap", "settings_backend")
        path = checked_path(profile["root"], directory=True, private=True)
        inside(path, directory)


def validate_roles(value: dict, policy: dict) -> None:
    """Check exact admitted local references; reject provider or implicit config."""
    exact_fields(
        value,
        {"id", "global_shortcut", "roles", "default_role", "selected_role"},
        "config_fields",
    )
    require(
        value["id"] in ("Embedded", "Server") and value["global_shortcut"] is None,
        "config_identity",
    )
    names = [policy["correctionRole"], policy["guardRole"]]
    require(all(type(n) is str and 0 < len(n) <= 128 for n in names), "role_name")
    require(names[0].casefold() != names[1].casefold(), "role_collision")
    require(
        type(value["roles"]) is dict and set(value["roles"]) == set(names),
        "roles_exact",
    )
    require(
        value["default_role"] == names[0] and value["selected_role"] == names[0],
        "roles_selected",
    )
    aliases = set()
    for name, graph_key in zip(names, ("compiledRules", "guardRules")):
        role = value["roles"][name]
        fields = {
            "name",
            "shortname",
            "relevance_function",
            "terraphim_it",
            "theme",
            "kg",
            "haystacks",
        }
        if type(role) is dict and "extra" in role:
            require(role["extra"] == {}, "role_extra")
            fields.add("extra")
        exact_fields(role, fields, "role_fields")
        require(role["name"] == name and role["haystacks"] == [], "role_scope")
        require(
            role["relevance_function"] in ("title-scorer", "terraphim-graph"),
            "role_scorer",
        )
        require(
            type(role["terraphim_it"]) is bool
            and type(role["theme"]) is str
            and len(role["theme"]) <= 128,
            "role_presentation",
        )
        own_aliases = {name.casefold()}
        if role["shortname"] is not None:
            require(
                type(role["shortname"]) is str and 0 < len(role["shortname"]) <= 128,
                "role_shortname",
            )
            own_aliases.add(role["shortname"].casefold())
        require(not own_aliases & aliases, "role_collision")
        aliases.update(own_aliases)
        kg = exact_fields(
            role["kg"],
            {"automata_path", "knowledge_graph_local", "public", "publish"},
            "role_kg",
        )
        require(
            kg["knowledge_graph_local"] is None
            and kg["public"] is False
            and kg["publish"] is False,
            "role_kg_scope",
        )
        require(
            kg["automata_path"] == {"Local": policy[graph_key]["path"]},
            "role_graph_reference",
        )


def project_boundary(root: Path) -> None:
    """Prevent tagged CLI project/ancestor discovery from overriding admitted roles."""
    directory = checked_path(str(root / ".terraphim"), directory=True)
    for item in directory.iterdir():
        require(
            item.name != "config.json"
            and not (item.name.startswith("role-") and item.name.endswith(".json")),
            "project_config",
        )


def load_policy(path: str, expected: str) -> dict:
    """Admit policy bytes first, then every referenced input before any child/write."""
    require(
        type(expected) is str and DIGEST.fullmatch(expected) is not None,
        "policy_digest",
    )
    raw = read_regular(path)
    require(hashlib.sha256(raw).hexdigest() == expected, "policy_digest")
    policy = decode_json(raw)
    exact_fields(
        policy,
        {
            "schemaVersion",
            "projectRoot",
            "agent",
            "roleConfig",
            "startupSettings",
            "correctionRole",
            "guardRole",
            "compiledRules",
            "guardRules",
            "rewriteEnabled",
            "captureFailures",
            "evidence",
        },
        "policy_fields",
    )
    require(
        type(policy["schemaVersion"]) is int and policy["schemaVersion"] == 1,
        "policy_version",
    )
    require(
        type(policy["rewriteEnabled"]) is bool
        and type(policy["captureFailures"]) is bool,
        "policy_flags",
    )
    require(not policy["captureFailures"], "capture_unavailable")
    root = checked_path(policy["projectRoot"], directory=True)
    project_boundary(root)
    for key in ("agent", "roleConfig", "compiledRules", "guardRules"):
        ref = exact_fields(policy[key], {"path", "sha256"}, "reference_fields")
        require(
            type(ref["sha256"]) is str and DIGEST.fullmatch(ref["sha256"]) is not None,
            "reference_digest",
        )
        actual = file_digest(ref["path"])
        require(actual == ref["sha256"], "reference_drift")
        if key == "agent":
            require(
                actual in RELEASED_AGENT_SHA256 and os.access(ref["path"], os.X_OK),
                "agent_release",
            )
        else:
            inside(Path(ref["path"]), root)
            require("$" not in ref["path"] and "~" not in ref["path"], "path_expansion")
    settings = exact_fields(
        policy["startupSettings"], {"directory", "settingsSha256"}, "settings_reference"
    )
    directory = checked_path(settings["directory"], directory=True, private=True)
    inside(directory, root)
    data = read_regular(str(directory / "settings.toml"), private=True)
    require(
        type(settings["settingsSha256"]) is str
        and hashlib.sha256(data).hexdigest() == settings["settingsSha256"],
        "settings_digest",
    )
    validate_settings(data, directory)
    validate_roles(decode_json(read_regular(policy["roleConfig"]["path"])), policy)
    rules = validate_rules(
        decode_json(read_regular(policy["compiledRules"]["path"])), empty=False
    )
    require(bool(rules) or not policy["rewriteEnabled"], "rules_empty")
    validate_rules(decode_json(read_regular(policy["guardRules"]["path"])), empty=True)
    evidence = policy["evidence"]
    require(
        type(evidence) is dict and type(evidence.get("enabled")) is bool,
        "evidence_fields",
    )
    if not evidence["enabled"]:
        exact_fields(evidence, {"enabled"}, "evidence_fields")
    else:
        exact_fields(
            evidence, {"enabled", "directory", "outputFiles"}, "evidence_fields"
        )
        inside(checked_path(evidence["directory"], directory=True, private=True), root)
        outputs = evidence["outputFiles"]
        require(
            type(outputs) is list
            and len(outputs) <= 16
            and all(type(v) is str for v in outputs),
            "evidence_outputs",
        )
        require(len(set(outputs)) == len(outputs), "evidence_outputs")
        for output in outputs:
            target = checked_path(output, prospective=True)
            inside(target, root)
            require(
                not target.is_relative_to(Path(evidence["directory"])),
                "evidence_output_overlap",
            )
    return policy


def child_environment(settings: str, parent: dict | None = None) -> dict:
    """Keep only OS identity/locale necessities and the explicitly admitted settings."""
    parent = os.environ if parent is None else parent
    env = {
        key: parent[key]
        for key in (
            "HOME",
            "USERPROFILE",
            "SYSTEMROOT",
            "WINDIR",
            "LANG",
            "LC_ALL",
            "LC_CTYPE",
            "TZ",
        )
        if key in parent
    }
    env["PATH"] = "/usr/bin:/bin:/usr/sbin:/sbin"
    env["TERRAPHIM_SETTINGS_PATH"] = settings
    return env


def run_child(
    argv: list[str], raw: bytes, cwd: Path, env: dict, timeout: float
) -> bytes:
    """Use real argv-only POSIX children with bounded concurrent pipe I/O and teardown."""
    require(os.name == "posix", "platform_unsupported")
    require(len(raw) <= MAX_BYTES, "agent_input_limit")
    deadline = time.monotonic() + timeout
    output = bytearray()
    error_bytes = 0
    process = subprocess.Popen(
        argv,
        cwd=cwd,
        env=env,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
        close_fds=True,
    )
    selector = selectors.DefaultSelector()
    try:
        assert process.stdin and process.stdout and process.stderr
        for stream, kind in ((process.stdout, "stdout"), (process.stderr, "stderr")):
            os.set_blocking(stream.fileno(), False)
            selector.register(stream, selectors.EVENT_READ, kind)
        if raw:
            os.set_blocking(process.stdin.fileno(), False)
            selector.register(process.stdin, selectors.EVENT_WRITE, "stdin")
        else:
            process.stdin.close()
        offset = 0
        while selector.get_map():
            remaining = deadline - time.monotonic()
            require(remaining > 0, "agent_timeout")
            for key, _mask in selector.select(remaining):
                stream, kind = key.fileobj, key.data
                if kind == "stdin":
                    try:
                        offset += os.write(stream.fileno(), raw[offset : offset + 8192])
                    except BrokenPipeError:
                        offset = len(raw)
                    if offset == len(raw):
                        selector.unregister(stream)
                        stream.close()
                else:
                    data = os.read(stream.fileno(), 8192)
                    if not data:
                        selector.unregister(stream)
                        stream.close()
                    elif kind == "stdout":
                        output.extend(data)
                        require(len(output) <= MAX_BYTES, "agent_output_limit")
                    else:
                        error_bytes += len(data)
                        require(error_bytes <= MAX_BYTES, "agent_output_limit")
        try:
            code = process.wait(timeout=max(0.001, deadline - time.monotonic()))
        except subprocess.TimeoutExpired as exc:
            raise Refusal("agent_timeout") from exc
        require(code == 0, "agent_exit")
        return bytes(output)
    finally:
        selector.close()
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait()
        for stream in (process.stdin, process.stdout, process.stderr):
            if stream:
                stream.close()


def cli_envelope(tool_input: dict) -> dict:
    """Forward only original tool input, never Cursor's outer metadata."""
    return {"tool_name": "Bash", "tool_input": tool_input}


def agent_command(output: dict, original: dict) -> str:
    """Accept a real agent denial or a shape-preserving command-only response."""
    if set(output) == {"hookSpecificOutput"}:
        deny = exact_fields(
            output["hookSpecificOutput"],
            {"hookEventName", "permissionDecision", "permissionDecisionReason"},
            "agent_response",
        )
        require(
            deny["hookEventName"] == "PreToolUse"
            and deny["permissionDecision"] == "deny"
            and type(deny["permissionDecisionReason"]) is str,
            "agent_response",
        )
        raise Refusal("agent_denied")
    require(
        set(output).issubset({"tool_name", "tool_input", "warnings", "validations"})
        and output.get("tool_name") == "Bash",
        "agent_response",
    )
    result = output.get("tool_input")
    require(type(result) is dict and set(result) == set(original), "agent_response")

    def unaffected(value):
        return json.dumps(
            {k: v for k, v in value.items() if k != "command"},
            sort_keys=True,
            ensure_ascii=True,
        )

    require(unaffected(result) == unaffected(original), "agent_mutation")
    if "warnings" in output:
        require(
            type(output["warnings"]) is list
            and all(type(v) is str for v in output["warnings"]),
            "agent_response",
        )
    if "validations" in output:
        require(type(output["validations"]) is dict, "agent_response")
    changed = command(result.get("command"))
    if output.get("warnings"):
        # The child JSON is bounded; only its validated warning count may escape.
        print(
            f"Terraphim: agent_warnings count={len(output['warnings'])}",
            file=sys.stderr,
        )
    return changed


def attributed_command(rules: dict, original: str, replacement: str) -> str:
    """Require literal whole-command attribution; Rust alone performs replacement."""
    require(
        original in rules and rules[original]["display_value"] == replacement,
        "rewrite_unattributed",
    )
    return replacement


def receipt_identities(policy: dict) -> dict:
    """Bind a record to the currently admitted dependencies and adapter bytes."""
    identities = {
        key: policy[key]["sha256"]
        for key in ("agent", "roleConfig", "compiledRules", "guardRules")
    }
    identities.update(
        adapter=file_digest(str(Path(__file__).resolve())),
        settings=policy["startupSettings"]["settingsSha256"],
    )
    return identities


class ReceiptStore:
    """Owned private, atomic records. Applied is never represented as executed."""

    def __init__(
        self,
        directory: Path,
        policy_sha256: str,
        *,
        create: bool = True,
        policy: dict | None = None,
    ):
        self.directory = checked_path(str(directory), directory=True, private=True)
        self.policy_sha256 = policy_sha256
        # Runtime callers always supply the admitted policy. Standalone store
        # primitives used by tests do not establish policy-qualified completion.
        self.project_root = Path(policy["projectRoot"]) if policy is not None else None
        self.expected_outputs = (
            list(policy["evidence"]["outputFiles"]) if policy is not None else None
        )
        self.expected_identities = (
            receipt_identities(policy) if policy is not None else None
        )
        if policy is not None:
            require(
                policy["evidence"]["enabled"] is True
                and str(directory) == policy["evidence"]["directory"],
                "evidence_admission",
            )
        self.marker = self.directory / ".terraphim-cursor-owner.json"
        if not self.marker.exists():
            require(create, "evidence_missing_owner")
            require(not list(self.directory.iterdir()), "evidence_unrelated")
            try:
                fd = os.open(
                    self.marker,
                    os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                    0o600,
                )
            except FileExistsError:
                pass
            else:
                with os.fdopen(fd, "wb") as stream:
                    stream.write(
                        json.dumps(
                            {
                                "schemaVersion": 1,
                                "owner": str(uuid.uuid4()),
                                "policySha256": policy_sha256,
                            }
                        ).encode()
                    )
                    stream.flush()
                    os.fsync(stream.fileno())
        marker = decode_json(read_regular(str(self.marker), private=True))
        exact_fields(
            marker, {"schemaVersion", "owner", "policySha256"}, "evidence_owner"
        )
        require(
            type(marker["schemaVersion"]) is int
            and marker["schemaVersion"] == 1
            and marker["policySha256"] == policy_sha256
            and type(marker["owner"]) is str,
            "evidence_owner",
        )
        require(
            re.fullmatch(r"[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}", marker["owner"])
            is not None,
            "evidence_owner",
        )
        self.owner = marker["owner"]
        self.interrupted_writes = []
        for item in self.directory.iterdir():
            temporary = re.fullmatch(r"([0-9a-f]{64})\.[0-9a-f]{32}\.tmp", item.name)
            require(
                item == self.marker
                or re.fullmatch(r"[0-9a-f]{64}\.(json|lock)", item.name)
                or temporary,
                "evidence_unrelated",
            )
            try:
                checked_path(str(item), private=True)
            except (FileNotFoundError, Refusal) as exc:
                # Another real writer may publish its temporary file or release
                # its lock after this directory snapshot. Only an absent known
                # transient may be ignored; stable records and unsafe paths fail.
                transient = temporary or re.fullmatch(r"[0-9a-f]{64}\.lock", item.name)
                if not transient or (
                    isinstance(exc, Refusal) and str(exc) != "path_missing"
                ):
                    raise
                checked_path(str(self.directory), directory=True, private=True)
                try:
                    item.lstat()
                except FileNotFoundError:
                    continue
                raise
            if temporary:
                self.interrupted_writes.append(
                    {
                        "recordId": None,
                        "callKey": temporary.group(1),
                        "storedState": "interrupted_write",
                        "effectiveState": "incomplete",
                        "reason": "interrupted_atomic_write",
                        "temporaryFile": item.name,
                    }
                )

    @staticmethod
    def key(event: dict) -> str:
        values = [
            event.get(k) for k in ("conversation_id", "generation_id", "tool_use_id")
        ]
        require(
            all(type(v) is str and 0 < len(v) <= 256 for v in values), "evidence_ids"
        )
        return hashlib.sha256(
            json.dumps(values, ensure_ascii=True).encode()
        ).hexdigest()

    def path(self, event: dict) -> Path:
        return self.directory / (self.key(event) + ".json")

    @contextmanager
    def locked(self, key: str):
        path = self.directory / (key + ".lock")
        try:
            fd = os.open(
                path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
            )
        except FileExistsError as exc:
            raise Refusal("evidence_busy") from exc
        try:
            os.write(fd, self.owner.encode())
            yield
        finally:
            os.close(fd)
            path.unlink()

    def read(self, key: str) -> dict:
        value = decode_json(
            read_regular(str(self.directory / (key + ".json")), private=True)
        )
        require(
            value.get("owner") == self.owner
            and value.get("callKey") == key
            and value.get("policySha256") == self.policy_sha256,
            "evidence_owner",
        )
        if self.expected_outputs is not None:
            # Compare before stat/open of any stored output. Receipt bytes are
            # evidence, never authority to expand the policy's file allowlist.
            require(
                value.get("selectedOutputs") == self.expected_outputs
                and value.get("identities") == self.expected_identities,
                "evidence_admission",
            )
            for output in self.expected_outputs:
                inside(Path(output), self.project_root)
        return value

    def write(self, key: str, value: dict) -> None:
        require(not self.interrupted_writes, "evidence_recovery_required")
        raw = json.dumps(value, sort_keys=True, ensure_ascii=True).encode() + b"\n"
        require(len(raw) <= MAX_BYTES, "evidence_size")
        destination = self.directory / (key + ".json")
        temporary = self.directory / (key + "." + uuid.uuid4().hex + ".tmp")
        fd = os.open(
            temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
        )
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            if destination.exists() or destination.is_symlink():
                self.read(key)
            os.replace(temporary, destination)
            directory_fd = os.open(self.directory, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        finally:
            if temporary.exists():
                temporary.unlink()

    def unfinished(self) -> list[dict]:
        """Report incomplete/crashed ownership without changing any stored byte."""
        observations = []
        for path in sorted(self.directory.glob("*.json")):
            if path == self.marker:
                continue
            value = self.read(path.stem)
            require(
                value["state"] in TERMINAL | {"prepared", "applied"}, "evidence_state"
            )
            if value["state"] in (
                "prepared",
                "applied",
                "incomplete",
                "evidence_error",
            ):
                observations.append(
                    {
                        "recordId": value["recordId"],
                        "callKey": value["callKey"],
                        "storedState": value["state"],
                        "effectiveState": "incomplete",
                    }
                )
        return observations + self.interrupted_writes

    def begin(
        self, event: dict, attempted: str, outputs: list[str], identities: dict
    ) -> dict:
        key = self.key(event)
        with self.locked(key):
            require(not self.path(event).exists(), "evidence_duplicate")
            for path in outputs:
                target = checked_path(path, prospective=True)
                require(not target.exists(), "evidence_output_exists")
            value = {
                "schemaVersion": 1,
                "owner": self.owner,
                "callKey": key,
                "recordId": str(uuid.uuid4()),
                "policySha256": self.policy_sha256,
                "state": "prepared",
                "createdAtNs": time.time_ns(),
                "attemptedCommand": command(attempted),
                "appliedCommand": None,
                "identities": identities,
                "selectedOutputs": outputs,
                "artifacts": [],
                "exitCode": None,
                "reason": None,
            }
            self.write(key, value)
            return value

    def transition(
        self,
        record: dict,
        state: str,
        applied: str | None = None,
        reason: str | None = None,
    ) -> dict:
        key = record["callKey"]
        with self.locked(key):
            value = self.read(key)
            require(
                value["recordId"] == record["recordId"]
                and value["state"] not in TERMINAL,
                "evidence_terminal",
            )
            require(
                state in ("applied", "denied", "incomplete", "evidence_error"),
                "evidence_state",
            )
            if state == "applied":
                require(value["state"] == "prepared", "evidence_transition")
                value["appliedCommand"] = command(applied)
            value["state"], value["reason"] = state, reason
            self.write(key, value)
            return value

    def applied(self, record: dict, applied: str) -> dict:
        return self.transition(record, "applied", applied=applied)

    def complete(self, event: dict, actual_command: str, exit_code: int) -> dict:
        """Complete only a separately qualified result, never unparsed host data."""
        require(type(exit_code) is int, "evidence_exit")
        key = self.key(event)
        with self.locked(key):
            value = self.read(key)
            require(
                value["appliedCommand"] == actual_command, "evidence_command_mismatch"
            )
            if value["state"] in TERMINAL:
                require(
                    value["state"] == "completed" and value["exitCode"] == exit_code,
                    "evidence_terminal",
                )
                return value
            require(value["state"] == "applied", "evidence_transition")
            artifacts = []
            try:
                for path in value["selectedOutputs"]:
                    if self.project_root is not None:
                        inside(Path(path), self.project_root)
                    p = checked_path(path)
                    info = p.stat()
                    require(
                        info.st_mtime_ns >= value["createdAtNs"],
                        "evidence_output_stale",
                    )
                    raw = read_regular(path)
                    artifacts.append(
                        {
                            "path": path,
                            "sha256": hashlib.sha256(raw).hexdigest(),
                            "bytes": len(raw),
                        }
                    )
            except (OSError, Refusal):
                value["state"], value["reason"] = (
                    "incomplete",
                    "evidence_output_unavailable",
                )
                self.write(key, value)
                raise Refusal("evidence_output_unavailable")
            value.update(state="completed", exitCode=exit_code, artifacts=artifacts)
            self.write(key, value)
            return value


def qualified_success(event: dict, kind: str) -> int | None:
    """Recognize only the observed released-Cursor success result; discard output.

    Cursor 3.24.18 and 3.25.6 emitted postToolUse with a JSON string containing
    output and exitCode=0. Observed failure events had no numeric exit, so it is
    never inferred here. Unobserved host versions remain unqualified.
    """
    if (
        kind != "postToolUse"
        or event.get("hook_event_name") != kind
        or event.get("cursor_version") not in NATIVE_SUCCESS_VERSIONS
    ):
        return None
    raw = event.get("tool_output")
    if type(raw) is not str:
        return None
    try:
        result = decode_json(raw.encode("utf-8"))
        exact_fields(result, {"output", "exitCode"}, "native_result_shape")
        require(
            type(result["output"]) is str
            and type(result["exitCode"]) is int
            and result["exitCode"] == 0,
            "native_result_shape",
        )
    except (Refusal, UnicodeError):
        return None
    return 0


def handle_event(event: dict, kind: str, policy_path: str, expected: str) -> dict:
    """Translate a bounded host event; no shell command is ever run here."""
    require(kind in ("preToolUse", "postToolUse", "postToolUseFailure"), "event_kind")
    require(
        "hook_event_name" not in event or event["hook_event_name"] == kind,
        "event_mismatch",
    )
    require(
        type(event.get("tool_name")) is str and bool(event["tool_name"]), "event_tool"
    )
    if event["tool_name"] != "Shell":
        return {"permission": "allow"} if kind == "preToolUse" else {}
    policy = load_policy(policy_path, expected)
    root = Path(policy["projectRoot"])
    require(checked_path(event.get("cwd"), directory=True) == root, "event_cwd")
    require(event.get("workspace_roots") == [str(root)], "event_workspace")
    tool = event.get("tool_input")
    require(type(tool) is dict, "event_input")
    original = command(tool.get("command"))
    for cwd_key in ("working_directory", "cwd"):
        if cwd_key in tool:
            require(
                checked_path(tool[cwd_key], directory=True) == root,
                "event_working_directory",
            )
    store = None
    record = None
    if policy["evidence"]["enabled"]:
        ReceiptStore.key(event)  # Validate ownership IDs before creating any file.
        store = ReceiptStore(
            Path(policy["evidence"]["directory"]),
            expected,
            create=kind == "preToolUse",
            policy=policy,
        )
    if kind != "preToolUse":
        # Only the observed success envelope can complete a record. Failures without
        # numeric status remain incomplete and never invoke learn capture.
        if store:
            key = store.key(event)
            if store.path(event).exists():
                record = store.read(key)
                # Observed 3.25.6 guard denial reports the attempted command:
                # no updated input was applied and this terminal receipt stays
                # unchanged. Never promote permission denial to execution.
                if (
                    record["state"] == "denied"
                    and record["appliedCommand"] is None
                    and record["reason"] == "pretool_refused"
                    and kind == "postToolUseFailure"
                    and event.get("hook_event_name") == kind
                    and event.get("cursor_version") == "3.25.6"
                    and event.get("failure_type") == "permission_denied"
                    and event.get("error_message") == "Terraphim: agent_denied"
                ):
                    require(
                        record["attemptedCommand"] == original,
                        "evidence_command_mismatch",
                    )
                    return {}
                require(
                    record["appliedCommand"] == original, "evidence_command_mismatch"
                )
                exit_code = qualified_success(event, kind)
                if exit_code is not None:
                    store.complete(event, original, exit_code)
                elif record["state"] not in TERMINAL:
                    store.transition(
                        record, "incomplete", reason="native_result_unqualified"
                    )
        return {}
    if store:
        record = store.begin(
            event,
            original,
            policy["evidence"]["outputFiles"],
            receipt_identities(policy),
        )
    try:
        argv = [
            policy["agent"]["path"],
            "--config",
            policy["roleConfig"]["path"],
            "hook",
            "--hook-type",
            "pre-tool-use",
            "--role",
            policy["correctionRole"],
        ]
        if policy["rewriteEnabled"]:
            argv.append("--rewrite")
        env = child_environment(policy["startupSettings"]["directory"])
        raw = json.dumps(cli_envelope(tool), ensure_ascii=True).encode()
        changed = agent_command(decode_json(run_child(argv, raw, root, env, 5)), tool)
        response = {"permission": "allow"}
        if changed != original:
            require(policy["rewriteEnabled"], "rewrite_disabled_mutation")
            rules = validate_rules(
                decode_json(read_regular(policy["compiledRules"]["path"])), empty=False
            )
            attributed_command(rules, original, changed)
            replacement = {**tool, "command": changed}
            guard_argv = [
                policy["agent"]["path"],
                "--config",
                policy["roleConfig"]["path"],
                "hook",
                "--hook-type",
                "pre-tool-use",
                "--role",
                policy["guardRole"],
            ]
            guarded = agent_command(
                decode_json(
                    run_child(
                        guard_argv,
                        json.dumps(cli_envelope(replacement)).encode(),
                        root,
                        env,
                        5,
                    )
                ),
                replacement,
            )
            require(guarded == changed, "guard_mutation")
            response["updated_input"] = replacement
        require(load_policy(policy_path, expected) == policy, "policy_drift")
        if store and record:
            store.applied(record, changed)
        return response
    except BaseException:
        if store and record:
            try:
                store.transition(record, "denied", reason="pretool_refused")
            except (OSError, Refusal):
                pass  # Existing prepared/applied bytes remain; never turn an I/O error green.
        raise


def main(argv: list[str] | None = None) -> int:
    """Emit exactly one host response; diagnostics contain bounded reason codes only."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", required=True)
    parser.add_argument("--policy-sha256", required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--event", choices=("preToolUse", "postToolUse", "postToolUseFailure")
    )
    mode.add_argument(
        "--inspect-receipts",
        action="store_true",
        help="Read unfinished owned records; no stdin, children or writes",
    )
    args = parser.parse_args(argv)

    def deadline(_signum, _frame):
        raise Refusal("adapter_timeout")

    previous = signal.signal(signal.SIGALRM, deadline)
    signal.setitimer(signal.ITIMER_REAL, 12)
    try:
        if args.inspect_receipts:
            policy = load_policy(args.policy, args.policy_sha256)
            require(policy["evidence"]["enabled"], "evidence_disabled")
            store = ReceiptStore(
                Path(policy["evidence"]["directory"]),
                args.policy_sha256,
                create=False,
                policy=policy,
            )
            result = {"unfinished": store.unfinished()}
        else:
            event = decode_json(sys.stdin.buffer.read(MAX_BYTES + 1))
            result = handle_event(event, args.event, args.policy, args.policy_sha256)
    except (Refusal, OSError, ValueError, TypeError, KeyError, RecursionError) as exc:
        code = str(exc) if isinstance(exc, Refusal) else "adapter_error"
        if args.inspect_receipts:
            result = {"error": code}
        elif args.event == "preToolUse":
            result = {"permission": "deny", "user_message": "Terraphim: " + code}
        else:
            result = {}
            print("Terraphim: " + code, file=sys.stderr)
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)
    print(json.dumps(result, ensure_ascii=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
