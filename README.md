# Terraphim Skills Introduction

Three small, open-source skills bring Terraphim's local code search, operational
learning, and agent memory workflows to Cursor, Kimi Code, AutoClaw, ZCode,
Hermes Agent, skills.sh, and Claude Code.

| Skill | Command family | Purpose |
|---|---|---|
| `terraphim-grep` | `terraphim-grep` | Search bounded local code and documentation, offline by default. |
| `terraphim-agent-learn` | `terraphim-agent learn` | Inspect failures and capture verified operational corrections. |
| `terraphim-agent-memory` | `terraphim-agent memory` | Retrieve role-scoped memory, inspect provenance, and govern its lifecycle. |

These Apache-2.0 command wrappers do not bundle executables, secrets, hooks, or
proprietary skill content. They remain useful without a marketplace account.

## Install the command dependencies

On macOS or Linux with Homebrew:

```bash
brew tap terraphim/terraphim
brew install terraphim-grep terraphim-agent
terraphim-grep --version
terraphim-agent --version
terraphim-agent learn --help
terraphim-agent memory --help
```

The formulae install the signed, checksummed Terraphim Clients v1.21.14 release.
See [dependency installation](docs/install-dependencies.md) for updates, removal,
non-Homebrew installation, signature checks, and PATH troubleshooting. The skills
never install dependencies automatically.

## Install in your agent

| Host | Installation |
|---|---|
| Cursor | Already submitted; install from Cursor Marketplace, or use the local-copy instructions below. |
| Kimi Code | Install this repository or add `marketplaces/kimi.json` as a custom marketplace. |
| AutoClaw | Import one checksummed ZIP per skill with **Skills & Connectors → Skills → Create → Add skill file**. |
| ZCode | Add `marketplaces/zcode.json` as a personal marketplace and install `terraphim-skills-intro`; curated listing is a separate maintainer-reviewed PR. |
| Hermes Agent | Add `terraphim/terraphim-cursor-plugin` as a tap, then inspect and install the three skills. |
| skills.sh | Run `npx skills add terraphim/terraphim-cursor-plugin`; use `DISABLE_TELEMETRY=1` to opt out of anonymous telemetry. |
| Claude Code | Add the repository as a marketplace, then install the plugin as shown below. |

Claude Code commands:

```text
claude plugin marketplace add terraphim/terraphim-cursor-plugin
claude plugin install terraphim-skills-intro@terraphim-skills
```

Availability in a host's curated public marketplace is separate from direct or
custom installation. See the [distribution guide](docs/distribution.md) for exact
install, update, discovery, and removal steps and current publication status.

## Local Cursor installation

For local development, copy this repository into:

```text
~/.cursor/plugins/local/terraphim-skills-intro
```

Cursor 3.20 rejects a symlink when its resolved target is outside
`~/.cursor/plugins/local`, so use a real directory:

```sh
cp -R /path/to/terraphim-cursor-plugin \
  ~/.cursor/plugins/local/terraphim-skills-intro
```

Reload Cursor, open **Customize**, and confirm that all three skills appear.

## Example requests

- “Use Terraphim Grep to find the authorization callback and show two lines of context.”
- “Search project learnings for an earlier failed deployment command.”
- “Retrieve role-scoped memory about OAuth redirect validation and show its provenance.”

The skills default to local, read-only operations. Persistent learning or memory
changes remain explicit and scoped. Review [permissions and side effects](docs/permissions.md)
before enabling writes or configured model synthesis.

## Continue with Terraphim Skills

Browse the [Community, Core, and Premium catalogue](https://terraphim-skills.md/skills/).
The public introduction contains no proprietary instructions or entitlement token.
Following a related-skill link never creates a checkout or transaction. Access and
purchase decisions remain on Terraphim's authenticated site and MCP services.

## Development

```bash
python3 scripts/generate_distribution.py --check
python3 -m unittest discover -s tests -p 'test_*.py'
python3 scripts/generate_distribution.py --autoclaw-dist dist/autoclaw
```

## Licence

Apache-2.0. See [LICENSE](LICENSE).
