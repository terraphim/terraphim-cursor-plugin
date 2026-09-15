# Terraphim Skills Introduction for Cursor

Three small, open-source command skills introduce Cursor users to Terraphim's local code search, operational learning, and agentic memory commands — plus an onboarding skill that wires them into a new, persistent Terraphim agent.

| Skill | Command family | Purpose |
|---|---|---|
| `terraphim-grep` | `terraphim-grep` | Search bounded local code and documentation, offline by default. |
| `terraphim-agent-learn` | `terraphim-agent learn` | Inspect failures and capture verified operational corrections. |
| `terraphim-agent-memory` | `terraphim-agent memory` | Retrieve role-scoped memory, inspect provenance, and govern its lifecycle. |
| `terraphim-agent-onboarding` | *(procedure)* | Onboard a new Terraphim agent: identity (`SOUL.md`, `IDENTITY.md`), the continuity loop, then the three command skills above. |

These are independently written Apache-2.0 wrappers. They do not contain or redistribute the proprietary Terraphim Skills catalogue.

## Prerequisites

Install current Terraphim command-line tools using the release instructions at <https://github.com/terraphim/terraphim-ai/releases>, then verify the installed surface:

```bash
terraphim-grep --version
terraphim-agent --version
terraphim-agent learn --help
terraphim-agent memory --help
```

The wrappers inspect `--help` at runtime so they remain honest about the locally installed version.

## Local Cursor installation

For local development, copy this repository into Cursor's local plugin directory:

```text
~/.cursor/plugins/local/terraphim-skills-intro
```

Cursor 3.20 rejects a symlink when its resolved target is outside
`~/.cursor/plugins/local`, so use a real directory for a reliable test. For example:

```sh
cp -R /path/to/terraphim-cursor-plugin \
  ~/.cursor/plugins/local/terraphim-skills-intro
```

Reload Cursor, open **Customize**, and confirm that the skills appear. Invoke them by name or ask Cursor to search code, inspect an earlier command failure, retrieve project memory, or onboard a new Terraphim agent.

## Example requests

- “Use Terraphim Grep to find the authorization callback and show two lines of context.”
- “Search project learnings for an earlier failed deployment command.”
- “Retrieve role-scoped memory about OAuth redirect validation and show its provenance.”

The skills default to local, read-only operations. Persistent learning or memory changes remain explicit and scoped.

## Onboarding a new Terraphim agent

The `terraphim-agent-onboarding` skill sequences identity, continuity, and the command toolchain for a new persistent agent. Its full fill-in-the-blank template and the canonical 12-prompt onboarding arc live under [`skills/terraphim-agent-onboarding/references/`](skills/terraphim-agent-onboarding/references/).

## Terraphim Skills

Browse the Terraphim catalogue and non-technical guidance at <https://terraphim-skills.md/>. This introductory plugin remains useful on its own and requires no marketplace account.

## Development

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
```

## Licence

Apache-2.0. See [LICENSE](LICENSE).
