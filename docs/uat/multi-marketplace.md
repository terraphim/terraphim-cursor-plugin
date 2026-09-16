# Multi-marketplace UAT protocol

This protocol validates the same three public Community skills in every
supported host. Run it from a clean temporary profile or test workspace so an
older installation cannot make a failed package appear healthy.

## Preconditions

1. Install and verify the runtime dependencies using
   [Install dependencies](../install-dependencies.md).
2. Confirm the plugin version is `0.2.2`.
3. Confirm the installed skill set is exactly:
   `terraphim-grep`, `terraphim-agent-learn`, and
   `terraphim-agent-memory`.
4. Use a disposable repository containing one searchable marker and a writable
   local Terraphim memory store.

## Shared acceptance scenarios

Run all scenarios through the host's agent interface, not only from a shell.

### UAT-1 — dependency guidance

Ask: “Check whether the Terraphim dependencies are installed.”

Pass when the agent runs or proposes the documented version/help probes. If a
binary is absent, it must show the Homebrew commands and must not silently
install software.

### UAT-2 — local search

Ask: “Use Terraphim Grep to find the unique marker in this workspace and show
two lines of context.”

Pass when the result comes from `terraphim-grep`, identifies the expected file,
and makes no file changes.

### UAT-3 — learning capture

Ask: “Capture this explicit lesson with Terraphim Agent: use the staging API
for marketplace smoke tests.”

Pass when the agent explains the intended write, invokes the documented
`terraphim-agent learn` flow only after the request, and the lesson can be
retrieved afterward.

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

## Host-specific installation and evidence

| Host | Installation route | Required evidence |
| --- | --- | --- |
| Cursor | Existing marketplace listing or repository plugin install | Plugin version, three discovered skills, UAT-1 through UAT-5 |
| Kimi Code | Install the tagged repository with `/plugins install`, or open `/plugins marketplace` with `marketplaces/kimi.json`; use `kimi plugin install` for the compatibility CLI | Plugin listing, exactly three skills after reload, plus UAT-1 through UAT-5 |
| AutoClaw | Import each ZIP from `dist/autoclaw/` | Successful import, checksum match, one skill per archive, UAT for all three skills |
| ZCode | Install from the repository using `.zcode-plugin/plugin.json` | Plugin listing and UAT-1 through UAT-5 |
| Hermes Agent | Add the repository's `skills/` entries to the configured skills directory | Three discovered skills and UAT-1 through UAT-5 |
| skills.sh | Install/discover from the public repository URL | Three discovered skills and UAT-1 through UAT-5 |
| Claude Code | Add the local/publisher marketplace, then install `terraphim-skills-intro` | Strict plugin validation, installed listing, UAT-1 through UAT-5 |
| Grok Build (xAI) | Install from the curated catalogue after submission approval | Full commit pin, generated component index, security checks, and UAT-1 through UAT-5 |

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
