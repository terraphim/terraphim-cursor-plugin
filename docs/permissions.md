# Permissions and side effects

| Skill | Network | Command execution | Default writes | Explicit side effects |
|---|---|---|---|---|
| Terraphim Grep | None by default; configured synthesis may call a model | `terraphim-grep` | None | Paid or external synthesis only when requested |
| Agent Learn | None required for local commands | `terraphim-agent learn` | None | Capture, correction, hooks, replay, or export only when authorised |
| Agent Memory | None required for local commands | `terraphim-agent memory` | None | Explicit-content capture, retirement proposal, or export only when authorised |
| Terraphim Editor | Online editor and documentation use network; local KG suggestions need no model. AI suggestions or synthesis require an explicit choice. | Existing editor UI and `terraphim-grep`; separate `terraphim-agent memory` example | None automatically | Edit/save the chosen document; export clean Markdown and graph JSON; optional authored-memory capture |

The signed instruction skills require separately installed `terraphim-grep`
and `terraphim-agent` binaries and contain no bundled CLI executables, secrets
or proprietary bodies. The optional [Cursor integration candidate](../integrations/cursor/README.md)
contains a hook adapter and inactive configuration examples; installation does
not register a hook, start MCP or enable capture. Source is Apache-2.0.

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

## Optional Cursor project integration

Native acceptance requires the matching release qualification record; source
and examples are not proof. The whole update cannot publish until hooks pass.
Setup is read-first and changes only separately reviewed project entries. The existing
grep MCP reads a selected graph/corpus; returned passages reach Cursor's model.
Synthesis is a separate opt-in. The agent may perform an update request during
startup even for local learning/memory operations; hooks also initialize their
service. Do not infer zero network from local matching.

Rewriting and receipt capture default off. Receipts, when explicitly enabled,
retain commands, status and explicitly selected output-file metadata only, not
general stdout/stderr, transcripts, email, environment or credentials. Automatic
failure capture is unavailable until native result-shape qualification; any
future opt-in learning write is distinct from receipt capture. Removing only
owned config entries preserves user data.
