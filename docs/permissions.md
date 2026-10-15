# Permissions and side effects

| Skill | Network | Command execution | Default writes | Explicit side effects |
|---|---|---|---|---|
| Terraphim Grep | None by default; configured synthesis may call a model | `terraphim-grep` | None | Paid or external synthesis only when requested |
| Agent Learn | None required for local commands | `terraphim-agent learn` | None | Capture, correction, hooks, replay, or export only when authorised |
| Agent Memory | None required for local commands | `terraphim-agent memory` | None | Explicit-content capture, retirement proposal, or export only when authorised |
| Terraphim Editor | Online editor and documentation use network; local KG suggestions need no model. AI suggestions or synthesis require an explicit choice. | Existing editor UI and `terraphim-grep`; separate `terraphim-agent memory` example | None automatically | Edit/save the chosen document; export clean Markdown and graph JSON; optional authored-memory capture |

The package requires local `terraphim-grep` and `terraphim-agent` binaries. It
contains no executables, secrets, hooks, MCP servers, agents, background tasks, or
proprietary skill bodies. Source is Apache-2.0.

Read-only inspection comes first. A skill must identify a write, execution, model
call, scope change, or export before requesting the corresponding authorisation.

## Editor companion

The [signed editor skill](../skills/terraphim-editor/SKILL.md) guides the existing
online editor or separately installed Terraphim It extension; the instruction
plugin does not provide another editor UI. At the user's request, editing and
saving changes the selected annotated document. Export clean Markdown and the
synonym graph to separate files, preserve existing user files, and read back the
saved outputs before reporting success.

Opening the online editor, following documentation links and installing separate
dependencies require network access. Authored alternatives and local KG
suggestions need no remote model. Before using AI suggestions or `terraphim-grep
--answer`, identify the configured provider and the text or retrieved context it
will receive. Loading this skill does not enable a provider or install tools.

The optional memory example writes explicit authored text to the current user's
OS-local memory store; changing the working directory does not isolate that
store. Exporting a graph does not import memory or activate a correction hook.
