# Multi-marketplace distribution

This repository is the canonical source for all hosts. The signed [v0.2.5
release](https://github.com/terraphim/terraphim-cursor-plugin/releases/tag/v0.2.5)
contains four skills and deterministic AutoClaw archives, including the new
editor-to-search companion. Its public packages and original signatures have
been verified. The version-pinned host examples below retain their historical
`0.2.4` qualification; that earlier pack has three skills. A new source release
does not qualify a new host installation or Kilo catalog admission.

## CLI workflows to include in every listing

Each marketplace description should link to [the checked grep and agent
examples](cli-workflows.md) and name both separate dependencies:
`terraphim-grep` searches the editor-exported Risk/Concern synonym graph;
`terraphim-agent` captures explicit lesson text and reads back its actual memory
ID. The guide supplies a small exported graph, baseline and graph-enabled
commands, and a capture/show pair tested with Clients 1.21.20.

Link to the [synonym-search tutorial](https://terraphim.ai/how-tos/synonym-search/)
and [agent memory tutorial](https://terraphim.ai/posts/cold-start-tax-agentic-memory/).
Show the graph output and saved memory result as distinct artifacts; the graph
export does not configure the agent's memory store. Skills remain instruction
wrappers, and curated availability does not establish native host qualification.

## Availability model

- **Direct/custom install** is controlled by the user and available from the
  immutable GitHub release.
- **Curated marketplace listing** is controlled by each marketplace maintainer and
  remains pending until that marketplace confirms indexing or approval.
- A prior Cursor submission is recorded, but acceptance or rejection is unconfirmed.
  Use the local-copy route below while its public listing remains unverified;
  do not submit a duplicate application.
- The Grok Build submission is open at
  <https://github.com/xai-org/plugin-marketplace/pull/730> and pins the exact
  signed release commit; public listing remains under maintainer review.
- AutoClaw local ZIP import is supported. ZhipuAI Skills Center inclusion is a
  separate external review; ClawHub is not treated as proof of that inclusion.

## Release integrity

Release tags match `v*`, are SSH-signed by a checked-in trusted signer, and are
verified against the exact GitHub event commit before assets are published. The
repository's active tag ruleset must restrict updates and deletions for `v*` so
the tag cannot move between verification and release publication.

## Kimi Code

Install the immutable release URL through Kimi Code's `/plugins install`, or
open `/plugins marketplace` with
`https://raw.githubusercontent.com/terraphim/terraphim-cursor-plugin/v0.2.4/marketplaces/kimi.json`
and install
`terraphim-skills-intro`. Run `/plugins reload` (or start a new session), then
confirm that exactly the three documented skills appear. The native manifest is
`kimi.plugin.json`; root `plugin.json` provides compatibility with Kimi CLI
releases whose shell-level `kimi plugin install` command expects that filename.
Update by installing the newer tag; remove through Kimi's plugin manager.

## AutoClaw

Download the three ZIP files and `SHA256SUMS` from the `v0.2.4` release. Verify
each digest, then use **Skills & Connectors → Skills → Create → Add skill file**.
Import each ZIP separately. Restart AutoClaw and confirm the skills persist. Remove
them through the same Skills screen. If Homebrew binaries are missing from the GUI
`PATH`, restart AutoClaw after installing the dependencies.

## ZCode

Open ZCode's **Discover** view and add
`https://raw.githubusercontent.com/terraphim/terraphim-cursor-plugin/v0.2.4/marketplaces/zcode.json`
as a personal marketplace source, install `terraphim-skills-intro`, then confirm the Plugin
Skills view shows exactly three skills. Curated discovery requires a separate
[pull request to `zai-org/zcode-plugins`](https://github.com/zai-org/zcode-plugins/pull/13);
this repository does not claim acceptance before the maintainers merge it.
Update or remove the installed plugin through ZCode's plugin manager.

## Hermes Agent

Add the repository as a GitHub tap, then inspect each skill before installing:

```bash
hermes skills tap add terraphim/terraphim-cursor-plugin
hermes skills inspect terraphim/terraphim-cursor-plugin/skills/terraphim-grep
hermes skills inspect terraphim/terraphim-cursor-plugin/skills/terraphim-agent-learn
hermes skills inspect terraphim/terraphim-cursor-plugin/skills/terraphim-agent-memory
```

Record the immutable `v0.2.4` provenance. Remove the skills with Hermes' normal
skill-management command.

## skills.sh

Use an isolated agent target and run:

```bash
npx skills add terraphim/terraphim-cursor-plugin
```

Set `DISABLE_TELEMETRY=1` to opt out of anonymous telemetry. Confirm exactly three
skills are offered and that their files match tag `v0.2.4`. Update by repeating the
command for the new tag; remove the installed skill directories through the target
agent's documented skill manager.

## Grok Build (xAI)

The [xAI marketplace submission](https://github.com/xai-org/plugin-marketplace/pull/730)
uses a full commit SHA for the signed release source. Its catalogue validation,
and component-index checks pass when reproduced locally against the submitted
head. GitHub-hosted Actions await maintainer approval; the hosted Socket security
and Semgrep checks are green. The listing becomes generally available only after
xAI maintainers merge the pull request.

## Claude Code

```text
claude plugin marketplace add terraphim/terraphim-cursor-plugin
claude plugin install terraphim-skills-intro@terraphim-skills
```

Run `claude plugin validate --strict .` before release. Use `claude plugin list`
to verify the installed version and normal Claude plugin commands to update or
remove it.

## Cursor

Use the [local-copy instructions](../README.md#local-cursor-installation) to
install the instruction plugin. Cursor 3.20 rejects external symlink targets,
so retain the real-directory copy route.

A previous marketplace submission was recorded by 16 September 2026. A public
[Cursor Marketplace](https://cursor.com/marketplace) search for `terraphim` on
15 October 2026 returned **No results found**. Neither acceptance nor rejection
has been confirmed. Keep the existing submission and seek its status before
submitting another application. The separately distributed Terraphim It VSIX
editor does not establish marketplace admission of this instruction plugin.

## Catalogue boundary

Each host links to <https://terraphim-skills.md/skills/>. Community skills are
freely obtainable; Core and Premium content follows the catalogue's entitlement
rules. Public packages never embed proprietary bodies, tokens, checkout URLs, or
automatic transactions.

## Kilo integration in preparation

The released pack supplies four instruction skills: editor, grep, authored memory and
explicit command learning. The editor companion uses the existing online/editor
extension and hands its exported synonym JSON to the separately installed
`terraphim-grep`. A separate example uses `terraphim-agent` to save/read authored
memory. No Kilo plugin binary or new server is introduced.

Kilo imports will use the official importer, a full source commit and copied
Apache licence, with verified source signatures kept separate from transformed
Kilo archive provenance. The existing remote Skills service, released Continue
grep transport and Rust KG MCP are distinct optional integrations. Actual Kilo
installation, OAuth/provider methods and catalog admission remain unqualified
until their individual output checks pass. No current Kilo listing is claimed.

### Skill signatures and CLI download checksums

The TSM signature verifies the original signed skill files. It does not authenticate
separately installed `terraphim-grep` or `terraphim-agent` binaries. The Clients
v1.21.20 download evidence establishes checksums; no archive-signature claim is
made here. The Kilo imports of grep, memory and learn 1.0.3 correct the inherited
phrase “signed, checksummed release archives” to “checksummed release archives”.
Their provenance records the exact old/new text and source version/commit, and
the verifier permits only that reviewed correction. Original signed source files
and existing release assets remain unchanged.

## CI delivery and external catalog gates

An SSH-signed version tag runs original TSM signature verification, tests and
reproducible archive checks before creating an immutable GitHub release. CI now
reads every public release asset back and compares it with the reviewed source;
`published-release-readback` retains the actual download hashes. The read-only
**Verify published marketplace pack** workflow can check an existing signed tag
without recreating a release. A failed download or byte mismatch fails the job.

Kimi and ZCode publisher manifests pin this source release. Claude, Cursor,
Hermes and skills.sh use the checked repository manifests or skill trees;
AutoClaw uses its per-skill ZIPs. These delivery artifacts are generated and
verified together, while native installation remains a separate host check.

Curated Kilo, Grok and ZCode catalogs require their maintainers to accept the
existing submissions. Kilo's updater fix and four-skill submission remain
separate pull requests. CI must not report those pending admissions as published
listings. A successful source release does not merge another repository's PR.

The Terraphim API catalog is a separate publishing surface. Its deployed publish
endpoint requires a publisher OAuth grant for the CLI audience; the current
service has no GitHub OIDC publisher exchange. Existing catalog uploads use
`tsm push`, and service/site deployment CI does not upload new skill content.
Unattended catalog publication remains a gate until a supported scoped CI
publisher identity is available; no human token is copied into this repository.
