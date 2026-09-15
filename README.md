# Terraphim Skills Introduction for Cursor

Three small, open-source skills introduce Cursor users to Terraphim's local code search, operational learning, and agentic memory commands.

| Skill | Command family | Purpose |
|---|---|---|
| `terraphim-grep` | `terraphim-grep` | Search bounded local code and documentation, offline by default. |
| `terraphim-agent-learn` | `terraphim-agent learn` | Inspect failures and capture verified operational corrections. |
| `terraphim-agent-memory` | `terraphim-agent memory` | Retrieve role-scoped memory, inspect provenance, and govern its lifecycle. |

These are independently written Apache-2.0 command wrappers. They do not contain or redistribute the proprietary Terraphim Skills catalogue.

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

For local development, place or symlink this repository at:

```text
~/.cursor/plugins/local/terraphim-skills-intro
```

Reload Cursor, open **Customize**, and confirm that all three skills appear. Invoke them by name or ask Cursor to search code, inspect an earlier command failure, or retrieve project memory.

## Example requests

- “Use Terraphim Grep to find the authorization callback and show two lines of context.”
- “Search project learnings for an earlier failed deployment command.”
- “Retrieve role-scoped memory about OAuth redirect validation and show its provenance.”

The skills default to local, read-only operations. Persistent learning or memory changes remain explicit and scoped.

## Terraphim Skills

Browse the Terraphim catalogue and non-technical guidance at <https://terraphim-skills.md/>. This introductory plugin remains useful on its own and requires no marketplace account.

## Development

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
```

## Licence

Apache-2.0. See [LICENSE](LICENSE).
