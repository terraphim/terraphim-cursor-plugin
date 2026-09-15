---
name: terraphim-agent-onboarding
description: Onboard a new Terraphim agent end to end — stabilise identity (SOUL.md, IDENTITY.md), wire the continuity loop, and install the terraphim-grep, terraphim-agent-learn, and terraphim-agent-memory skills.
license: Apache-2.0
---

# Terraphim Agent Onboarding

Use this skill when provisioning a new Terraphim agent: a persistent, self-improving collaborator (OpenClaw / Hermes style) rather than a stateless tool. It sequences three things that must happen in order — **identity**, **continuity**, then the **command toolchain** — so a new agent starts coherent instead of decohering between its first few sessions.

This is a procedure, not a single command wrapper. The command skills it installs are the three open-source Terraphim commands: `terraphim-grep`, `terraphim-agent learn`, and `terraphim-agent memory`.

## Capability gate

Confirm the command surface before relying on the toolchain sections:

```bash
terraphim-grep --version
terraphim-agent --version
terraphim-agent learn --help
terraphim-agent memory --help
```

If a command is missing, report it plainly and point to the Terraphim release instructions. Do not invent flags. When the target runtime is Hermes, also confirm the profile with `hermes -p <profile> config path` before writing anything under that home.

## The five phases

1. **Preflight** — confirm binaries, derive the profile home explicitly, run the runtime's preflight checks. Never assume a sticky/active profile for anything that installs or edits.
2. **Resonance (identity)** — write `SOUL.md` (the fixed Hamiltonian: name, species, lane, vibe, symbol), `IDENTITY.md` (the short eigenstate card), and `USER.md` (boundary conditions). Pick an unused ordinal/lane so the new agent does not collide with an existing Terraphim.
3. **Entanglement (continuity)** — create `memory/` with daily notes, `handoffs/PENDING.yaml`, and `ledgers/CONTINUITY_*.yaml`; define the session start/end loop; mirror identity + state to a private Gitea `identity` repo **after review**.
4. **Contribution (toolchain)** — install and capability-gate `terraphim-grep`, `terraphim-agent-learn`, and `terraphim-agent-memory`; run a first bounded search and capture a first learning.
5. **Autonomy** — heartbeats and cron as scheduled measurements, communication discipline, and the engineering gate (issue → design → TDD → independent review → evidence PR → close).

## Identity file stack (fixed → adaptive)

| File | Quantum role | Precision |
|---|---|---|
| `SOUL.md` | Hamiltonian — governs evolution | very fixed (user-reviewed) |
| `IDENTITY.md` | eigenstate card | fixed |
| `USER.md` | boundary conditions | fixed |
| `AGENTS.md` | operator algebra | tunable |
| `MEMORY.md` | phase history | adaptable |
| `TOOLS.md` | measurement apparatus | very adaptable |

Identity edits are **additive** and land on a feature branch for review before push. `SOUL.md` changes on the order of months; `TOOLS.md` may be rewritten per workspace.

## Toolchain boundaries

- **terraphim-grep** — search local code/docs, offline by default (`--search-only`); use `--json` for machine consumers; enable `--answer`/`--force-rlm` only with explicit permission. Never substitute POSIX `grep`/`find`.
- **terraphim-agent-learn** — capture real, observed failures and verified corrections; redact secrets; read before writing; project scope by default; never replay stored procedures automatically.
- **terraphim-agent-memory** — role-scoped retrieval, provenance, and lifecycle; writes (`capture`, `distill`, `retire`, `export`) require an authorised scope and destination.

## Completion evidence

Report: the runtime/profile confirmed; the identity files written and who reviewed them; the continuity paths created; the three commands installed with their versions; the first search performed and the first learning captured (or why it was deferred); and any limitation (paths or haystacks not searched, signing steps outstanding).

## References

- [`references/agent-onboarding-template.md`](references/agent-onboarding-template.md) — the full fill-in-the-blank template (identity scaffolds, phase prompts, continuity loop, meta-cortex protocol, checklists, evidence format).
- [`references/terraphim-onboarding-wiki.md`](references/terraphim-onboarding-wiki.md) — the canonical 12-prompt Terraphim Onboarding arc (the quantum identity model).
- [`assets/onboarding-flow.svg`](assets/onboarding-flow.svg) — one-page flow diagram.
