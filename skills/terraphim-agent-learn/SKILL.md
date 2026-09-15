---
name: terraphim-agent-learn
description: Inspect and capture command failures or user corrections with terraphim-agent learn. Use when a user asks to preserve a concrete operational lesson, search earlier failures, or attach a correction; use terraphim-agent-memory for broader memory retrieval and lifecycle work.
license: Apache-2.0
---

# Terraphim Agent Learn

Use `terraphim-agent learn` for concrete operational learning: failed commands, their errors, explicit corrections, and reviewed procedures. Default to project scope and read-only inspection.

## Capability gate

```bash
command -v terraphim-agent
terraphim-agent --version
terraphim-agent learn --help
```

Inspect the selected subcommand's `--help` before a write or replay. The installed binary is authoritative.

## Read before writing

Start with a bounded project-scoped inspection:

```bash
terraphim-agent learn list --recent 10
terraphim-agent learn query "cargo build"
```

Use `--exact` when identifiers must match literally. Use `--semantic` only when the project has a suitable knowledge graph. Use `--global` only when the user explicitly asks to search or modify global learning state.

## Capture a failed command

Capture only a real, observed failure. Redact tokens, credentials, personal data, customer data, and sensitive paths from both the command and error before storing them.

```bash
terraphim-agent learn capture --error "<redacted error>" --exit-code 1 "<redacted failed command>"
```

Record the smallest useful error. Do not store full logs when a short diagnostic and exit code preserve the lesson.

## Correct an existing learning

First identify the exact learning, then attach the verified correction:

```bash
terraphim-agent learn query "<failure pattern>" --exact
terraphim-agent learn correct "<learning-id>" --correction "<verified correction>"
```

Use `learn correction` for an explicit user preference or workflow correction that is not tied to one failed command. Inspect `terraphim-agent learn correction --help` before writing.

## Procedures and hooks

- `learn procedure replay` executes stored commands. Never replay automatically; inspect the procedure and obtain authorization appropriate to its effects.
- `learn install-hook` changes an agent's configuration. Use it only when the user explicitly asks to install the hook.
- `learn export-kg` writes files. Confirm the exact output directory and review the generated knowledge before treating it as trusted.

## Completion evidence

For read-only work, report the matching learning IDs and why they are relevant. For a write, report the new or corrected ID, scope, and redactions without repeating sensitive input.
