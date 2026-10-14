# Terraphim Skills Introduction — marketplace submission pack

This document is the reusable, public submission collateral for the Terraphim
introductory skills plugin. Platform-specific manifests are generated from
`distribution/metadata.json`; this copy should remain consistent with that
canonical source. The signed four-skill pack **0.2.5** is released; its public
archives and original signatures have been verified. The previous **0.2.4**
pack has three skills. Native host qualification and Kilo catalog admission
remain separate gates.

## Listing identity

- **Name:** Terraphim Skills Introduction
- **Slug:** `terraphim-skills-intro`
- **Publisher:** Terraphim AI
- **Category:** Developer tools
- **Licence:** Apache-2.0
- **Homepage:** <https://terraphim-skills.md/>
- **Public catalogue:** <https://terraphim-skills.md/skills/>
- **Installation guide:** <https://terraphim-skills.md/docs/non-technical/>
- **MCP guide:** <https://terraphim-skills.md/docs/mcp/>
- **Privacy policy:** <https://terraphim-skills.md/legal/privacy/>
- **Terms of service:** <https://terraphim-skills.md/legal/terms/>

### Tagline

Create wording alternatives, search a shared synonym graph, capture learning,
and retrieve memory with Terraphim.

### Short description

Four Community skills connect editor alternatives, local search, structured
learning capture, and reusable memory. The skills run Terraphim's local command-line
tools and explain every write before it happens.

### Long description

Terraphim Skills Introduction gives coding agents four focused, open-source
workflows:

1. `terraphim-grep` searches local code and documentation with context.
2. `terraphim-agent-learn` turns an explicit lesson into a reusable local
   knowledge entry.
3. `terraphim-agent-memory` works with the current user's OS-local memory
   store; the checked example captures authored text and reads it back by ID.
4. `terraphim-editor` guides the existing editor: create and swap alternatives,
   save/reopen, export synonym JSON and search related decisions.

The plugin contains instructions, not bundled executables. Users install the
signed Terraphim binaries through Homebrew or the checksummed release archives
and verify both versions before an agent uses them. Search is read-only by default. Learning and memory writes are
performed only when the user asks for them.

The Community skills stand on their own. They also link neutrally to the
Terraphim Skills catalogue, where users can discover Community, Core, and
Premium workflows without an in-skill checkout or purchase prompt.

## Include both CLI examples

Use the [shared CLI workflow](cli-workflows.md) in each publication. It includes:

- A Markdown concept note with `synonyms:: concern`, an actual exported JSON
  graph, and `terraphim-grep Concern --search-only --haystack all --paths ./corpus
  --thesaurus ./risk-concern.knowledge-graph.json --json -n 3`.
- `terraphim-agent --format json memory capture --content 'Risk requires a
  Decision: approve a second supplier as the mitigation.' --provenance-tag
  'public-project-brief'`, followed by `memory show <actual-memory-id> --json`.

The complete copyable commands and output checks are in the guide. They were
run using released Clients 1.21.20 binaries. The memory capture is an explicit
write; a search graph export does not configure or isolate the memory store.
Link the [editor and grep story](https://terraphim.ai/how-tos/synonym-search/)
and [agent memory story](https://terraphim.ai/posts/cold-start-tax-agentic-memory/)
so readers can continue from either tool.

## Suggested prompts

- “Use Terraphim Grep to find where OAuth callback state is validated.”
- “Capture what we learned from this incident for the next session.”
- “Save the deployment lesson in local memory, then show its actual saved ID and content.”

## Runtime prerequisites

```sh
brew tap terraphim/terraphim
brew install terraphim-grep terraphim-agent
terraphim-grep --version
terraphim-agent --version
terraphim-agent learn --help
terraphim-agent memory --help
```

See [Install dependencies](install-dependencies.md) for signed-release and
non-Homebrew options.

## Permissions and data handling

- No credentials are bundled.
- No telemetry is added by this plugin.
- Search reads only paths the user supplies.
- Learning and memory commands write only after an explicit request.
- The user controls the local Terraphim configuration and storage location.

See [Permissions](permissions.md) for the complete boundary.

## Editorial collateral

Use the canonical article only:
<https://terraphim.ai/posts/disciplined-engineering-ai-systems/>.

The repository includes Terraphim-owned V-model artwork in both formats:

- `assets/v-model-overview.svg`
- `assets/v-model-overview.png`

## Platform artefacts

| Host | Artefact | Delivery route |
| --- | --- | --- |
| Cursor | `.cursor-plugin/plugin.json` | Existing Cursor marketplace listing; do not resubmit |
| Kimi Code | `kimi.plugin.json`, compatibility `plugin.json`, and `marketplaces/kimi.json` | Direct install and publisher-owned marketplace |
| AutoClaw | `dist/autoclaw/*.zip` and `SHA256SUMS` | Import one skill ZIP at a time |
| ZCode | `.zcode-plugin/plugin.json` and `marketplaces/zcode.json` | Personal marketplace; separate curated-marketplace PR |
| Hermes Agent | `skills/*/SKILL.md` | Repository/local skills directory |
| skills.sh | `skills/*/SKILL.md` | Repository URL discovery/install |
| Claude Code | `.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json` | Direct install and publisher-owned marketplace |
| Kilo | Four imported skills and three optional existing MCP integrations | In preparation; separate upstream admission and actual host checks required |
| Grok Build (xAI) | `.grok-plugin/marketplace.json` entry in xAI's catalogue | Submission pending maintainer review; see [distribution status](distribution.md) |

An artefact being present does not imply that a third-party catalogue has
accepted or featured the plugin. Record curated acceptance only after the host
confirms it.

## Submission checklist

1. Run `python3 scripts/generate_distribution.py --check`.
2. Run `python3 -m unittest discover -s tests -p 'test_*.py'`.
3. Build AutoClaw archives and verify `dist/autoclaw/SHA256SUMS`.
4. Install and exercise the plugin with the host-specific UAT protocol.
5. Confirm the listing uses the canonical homepage, repository, licence, and
   article URL above.
6. Confirm the listing does not claim bundled binaries, automatic dependency
   installation, proprietary skill content, or curated acceptance.
7. Publish the SSH-signed tag with the trusted release key; the release workflow
   verifies that signature, revalidates the pack in a read-only job, then uses a
   separate write-scoped job to attach the deterministic AutoClaw archives,
   checksums, and V-model artwork.
8. Save the host's submission URL and status in the release evidence.
