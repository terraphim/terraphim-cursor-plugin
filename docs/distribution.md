# Multi-marketplace distribution

This repository is the canonical source for all hosts. Release `v0.2.2` contains
exactly three skills and deterministic AutoClaw archives.

## Availability model

- **Direct/custom install** is controlled by the user and available from the
  immutable GitHub release.
- **Curated marketplace listing** is controlled by each marketplace maintainer and
  remains pending until that marketplace confirms indexing or approval.
- Cursor is already submitted and is a regression target, not a new submission.
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
`https://raw.githubusercontent.com/terraphim/terraphim-cursor-plugin/v0.2.2/marketplaces/kimi.json`
and install
`terraphim-skills-intro`. Run `/plugins reload` (or start a new session), then
confirm that exactly the three documented skills appear. The native manifest is
`kimi.plugin.json`; root `plugin.json` provides compatibility with Kimi CLI
releases whose shell-level `kimi plugin install` command expects that filename.
Update by installing the newer tag; remove through Kimi's plugin manager.

## AutoClaw

Download the three ZIP files and `SHA256SUMS` from the `v0.2.2` release. Verify
each digest, then use **Skills & Connectors → Skills → Create → Add skill file**.
Import each ZIP separately. Restart AutoClaw and confirm the skills persist. Remove
them through the same Skills screen. If Homebrew binaries are missing from the GUI
`PATH`, restart AutoClaw after installing the dependencies.

## ZCode

Open ZCode's **Discover** view and add
`https://raw.githubusercontent.com/terraphim/terraphim-cursor-plugin/v0.2.2/marketplaces/zcode.json`
as a personal marketplace source, install `terraphim-skills-intro`, then confirm the Plugin
Skills view shows exactly three skills. Curated discovery requires a separate
pull request to `zai-org/zcode-plugins`; this repository does not claim that
acceptance before the maintainers merge it. Update or remove the installed
plugin through ZCode's plugin manager.

## Hermes Agent

Add the repository as a GitHub tap, then inspect each skill before installing:

```bash
hermes skills tap add terraphim/terraphim-cursor-plugin
hermes skills inspect terraphim/terraphim-cursor-plugin/skills/terraphim-grep
hermes skills inspect terraphim/terraphim-cursor-plugin/skills/terraphim-agent-learn
hermes skills inspect terraphim/terraphim-cursor-plugin/skills/terraphim-agent-memory
```

Record the immutable `v0.2.2` provenance. Remove the skills with Hermes' normal
skill-management command.

## skills.sh

Use an isolated agent target and run:

```bash
npx skills add terraphim/terraphim-cursor-plugin
```

Set `DISABLE_TELEMETRY=1` to opt out of anonymous telemetry. Confirm exactly three
skills are offered and that their files match tag `v0.2.2`. Update by repeating the
command for the new tag; remove the installed skill directories through the target
agent's documented skill manager.

## Claude Code

```text
claude plugin marketplace add terraphim/terraphim-cursor-plugin
claude plugin install terraphim-skills-intro@terraphim-skills
```

Run `claude plugin validate --strict .` before release. Use `claude plugin list`
to verify the installed version and normal Claude plugin commands to update or
remove it.

## Cursor

Install from Cursor Marketplace. For local testing, follow the real-directory
copy instructions in the README; Cursor 3.20 rejects external symlink targets.

## Catalogue boundary

Each host links to <https://terraphim-skills.md/skills/>. Community skills are
freely obtainable; Core and Premium content follows the catalogue's entitlement
rules. Public packages never embed proprietary bodies, tokens, checkout URLs, or
automatic transactions.
