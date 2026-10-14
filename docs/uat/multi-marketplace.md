# Multi-marketplace UAT protocol

This protocol qualifies the released four-skill **0.2.5 pack** in each intended host.
Released 0.2.4 contains only the earlier three skills; historical results remain
bound to that version. No host passes merely because it shares the source. Run it from a clean temporary profile or test workspace so an
older installation cannot make a failed package appear healthy.

## Preconditions

1. Install and verify the runtime dependencies using
   [Install dependencies](../install-dependencies.md).
2. Confirm the plugin version is `0.2.5`; record the immutable release and
   any platform-specific transformed package provenance separately.
3. Confirm the installed skill set is exactly:
   `terraphim-grep`, `terraphim-agent-learn`, and
   `terraphim-agent-memory`, plus `terraphim-editor`.
4. Use a disposable repository and a dedicated test OS account/container for
   OS-user memory/global installs. A temporary working directory alone does not
   isolate memory. Never override HOME or modify normal user profiles.

## Shared acceptance scenarios

Run all scenarios through the host's agent interface, not only from a shell.

### UAT-1 — dependency guidance

Ask: “Check whether the Terraphim dependencies are installed.”

Pass when the agent actually runs the documented version/help probes and the
outputs identify the expected released binaries. If a binary is absent, show
installation guidance and mark execution BLOCKED; a proposed command is not an
executed result. Do not silently install software.

### UAT-2 — local search

Ask: “Use Terraphim Grep to find the unique marker in this workspace and show
two lines of context.”

Pass when the result comes from `terraphim-grep`, identifies the expected file,
and makes no file changes.

### UAT-3 — learning capture

Execute a harmless command that actually fails, then ask the agent to capture
its observed exit/error, inspect the returned learning ID and record a verified
correction. Pass when saved learning/readback and actual corrected execution
match. Inspect the real project/global scope. `learn correct` annotates the
failure; any compiled rewrite needs a separate correction-store add, compile
and export. Do not infer automatic hook activation.

### UAT-4 — memory retrieval and write boundary

Ask first: “Search Terraphim memory for marketplace smoke tests.” Then ask:
“Record that production payment tests require an amount-bounded mandate.”

Pass when retrieval cites the matching local memory, the first request writes
nothing, and the second explicit request creates a retrievable entry.

### UAT-5 — catalogue boundary

Ask: “Where can I find more Terraphim skills?”

Pass when the agent provides <https://terraphim-skills.md/skills/> as neutral
discovery. It must not initiate checkout, fabricate access, or present Premium
content as bundled.

### UAT-6 — editor synonym-to-search

Use the actual separately released editor with the host: create Concern for
Risk, swap, save, close/reopen, export clean Markdown and the actual document
knowledge graph. Verify both terms share a concept ID. Search the unchanged
Risk-only corpus by Concern with and without that graph; inspect the actual
zero-to-expected passage change and source files. Synthesis is a separate
provider opt-in, with retrieved passages and generated wording saved distinctly.
Use the [companion](../../skills/terraphim-editor/SKILL.md) and packaged workflow.
A prepared graph is a fixture, not proof of a new editor action. Agent-memory
examples remain separate from the short editor-to-search demo.

## Host-specific installation and evidence

| Host | Installation route | Required evidence |
| --- | --- | --- |
| Cursor | Existing marketplace listing or repository plugin install | Plugin version, four discovered skills, UAT-1 through UAT-6 |
| Kimi Code | Install the tagged repository with `/plugins install`, or open `/plugins marketplace` with `marketplaces/kimi.json`; use `kimi plugin install` for the compatibility CLI | Plugin listing, exactly four skills after reload, plus UAT-1 through UAT-6 |
| AutoClaw | Import each ZIP from `dist/autoclaw/` | Successful import, checksum match, one skill per archive, UAT for all four skills |
| ZCode | Install from the repository using `.zcode-plugin/plugin.json` | Plugin listing and UAT-1 through UAT-6 |
| Hermes Agent | Add the repository's `skills/` entries to the configured skills directory | Four discovered skills and UAT-1 through UAT-6 |
| skills.sh | Install/discover from the public repository URL | Four discovered skills and UAT-1 through UAT-6 |
| Claude Code | Add the local/publisher marketplace, then install `terraphim-skills-intro` | Strict plugin validation, installed listing, UAT-1 through UAT-6 |
| Kilo | Official skill importer/catalog and native project/global installation after admission | Four skills, relative resources, scope/collision/ownership lifecycle, actual MCP results and UAT-1 through UAT-6; each method/OS independently qualified |
| Grok Build (xAI) | Install from the curated catalogue after submission approval | Full commit pin, generated component index, security checks, and UAT-1 through UAT-6 |

Capture the host and version, plugin version, command transcript or screenshots,
and the final pass/fail result. Redact local paths or memory content that is not
intended for publication.

## Stop conditions

Do not publish for a host when any of these conditions holds:

- a manifest fails the host's current validator;
- extra skills or proprietary files are included;
- dependency installation happens without user approval;
- a read-only search changes files;
- the plugin implies that Community installation grants Core or Premium access;
- the AutoClaw checksum or reproducibility check fails.
