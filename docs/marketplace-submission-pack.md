# Terraphim Skills Introduction — marketplace submission pack

This document is the reusable, public submission collateral for the Terraphim
introductory skills plugin. Platform-specific manifests are generated from
`distribution/metadata.json`; this copy should remain consistent with that
canonical source.

## Listing identity

- **Name:** Terraphim Skills Introduction
- **Slug:** `terraphim-skills-intro`
- **Publisher:** Terraphim AI
- **Category:** Developer tools
- **Licence:** Apache-2.0
- **Homepage:** <https://terraphim-skills.md/>
- **Public catalogue:** <https://terraphim-skills.md/skills/>
- **Repository:** <https://github.com/terraphim/terraphim-cursor-plugin>

### Tagline

Search code, capture learning, and retrieve memory with Terraphim command-line
tools.

### Short description

Three Community skills introduce local code search, structured learning
capture, and reusable memory. The skills run Terraphim's local command-line
tools and explain every write before it happens.

### Long description

Terraphim Skills Introduction gives coding agents three focused, open-source
workflows:

1. `terraphim-grep` searches local code and documentation with context.
2. `terraphim-agent-learn` turns an explicit lesson into a reusable local
   knowledge entry.
3. `terraphim-agent-memory` retrieves, records, and applies local project
   memory.

The plugin contains instructions, not bundled executables. Users install the
signed Terraphim binaries through Homebrew and can verify both tools before an
agent uses them. Search is read-only by default. Learning and memory writes are
performed only when the user asks for them.

The Community skills stand on their own. They also link neutrally to the
Terraphim Skills catalogue, where users can discover Community, Core, and
Premium workflows without an in-skill checkout or purchase prompt.

## Suggested prompts

- “Use Terraphim Grep to find where OAuth callback state is validated.”
- “Capture what we learned from this incident for the next session.”
- “Search project memory for the deployment constraints, then cite the source.”

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
