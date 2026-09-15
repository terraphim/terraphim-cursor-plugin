# Permissions and side effects

| Skill | Network | Command execution | Default writes | Explicit side effects |
|---|---|---|---|---|
| Terraphim Grep | None by default; configured synthesis may call a model | `terraphim-grep` | None | Paid or external synthesis only when requested |
| Agent Learn | None required for local commands | `terraphim-agent learn` | None | Capture, correction, hooks, replay, or export only when authorised |
| Agent Memory | None required for local commands | `terraphim-agent memory` | None | Capture, distil, retire, or export only when authorised |

The package requires local `terraphim-grep` and `terraphim-agent` binaries. It
contains no executables, secrets, hooks, MCP servers, agents, background tasks, or
proprietary skill bodies. Source is Apache-2.0.

Read-only inspection comes first. A skill must identify a write, execution, model
call, scope change, or export before requesting the corresponding authorisation.
