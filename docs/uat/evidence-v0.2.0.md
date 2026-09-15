# Validation evidence — v0.2.0

Date: 2026-09-15

This record distinguishes automated proof from checks that still require a
specific desktop host or third-party marketplace decision.

## Package and dependency proof

- `terraphim-grep --version`: `1.21.14`
- `terraphim-agent --version`: `1.21.14`
- `terraphim-agent learn --help`: passed
- `terraphim-agent memory --help`: passed
- Every command and option shown in the three `SKILL.md` files was checked
  against the installed v1.21.14 command help.
- Generated-manifest drift check: passed.
- `tsm validate` passed for all three signed Community skill directories at
  skill version `1.0.1`.
- Python contract/regression suite: 22 tests passed, including local Markdown
  link resolution.
- Ruff lint and formatting checks: passed.
- Markdown structure lint (with the repository's long-line and compact-table
  style accepted): passed.
- GitHub Actions workflow lint: passed.
- Release CI uses exact action commit pins, disables persisted checkout
  credentials, verifies the SSH-signed tag against the committed trusted public
  key, and separates read-only validation from the write-scoped publication job.
- `git diff --check`: passed.

## Host proof

### Claude Code

- CLI validator: `claude plugin validate --strict .` passed.
- A temporary isolated Claude configuration added this repository as the
  `terraphim-skills` marketplace.
- `terraphim-skills-intro@terraphim-skills` installed successfully at version
  `0.2.0`.
- The installed copy contained exactly the three allowlisted `SKILL.md` files.

### Kimi Code

- Kimi CLI `1.44.0` installed the repository in an isolated `KIMI_SHARE_DIR`.
- `kimi plugin info terraphim-skills-intro` reported version `0.2.0`.
- The installed copy contained exactly the three allowlisted `SKILL.md` files.
- The pack includes Kimi's native `kimi.plugin.json`, a compatible root
  `plugin.json`, and the current version-2 custom marketplace contract.

### skills.sh

- The current `skills` CLI inspected the local repository with telemetry
  disabled.
- It reported `Found 3 skills` and listed only `terraphim-grep`,
  `terraphim-agent-learn`, and `terraphim-agent-memory`.

### ZCode

- The plugin was staged into a clean checkout of `zai-org/zcode-plugins`.
- The official `scripts/validate.py` accepted all 22 entries, including
  `terraphim-skills-intro`.
- The official `scripts/build_dist.py` built
  `plugins/terraphim-skills-intro/0.2.0/plugin.zip` successfully.
- Curated availability remains pending until Z.ai maintainers merge a separate
  submission pull request.

### AutoClaw

- Three deterministic archives were built, one per skill.
- `unzip -t` passed for every archive.
- `shasum -a 256 -c SHA256SUMS` passed for all three archives.
- Desktop import and agent invocation still require the Zhipu AutoClaw desktop
  application; archive validation is not represented as desktop UAT.

### Hermes Agent

- Hermes Agent `v1.0.0` accepted `terraphim/terraphim-cursor-plugin` as a tap
  at the expected `skills/` path.
- Live search could not complete because Hermes uses GitHub's Contents API and
  the unauthenticated host IP returned HTTP 403 `API rate limit exceeded`.
- The Git remote and `main` branch were independently reachable. This is an
  external rate-limit constraint, not proof of package failure or a completed
  Hermes runtime UAT.

### Cursor

- Cursor manifest contract tests passed and the existing real-directory local
  installation warning remains documented.
- Cursor marketplace submission was completed before this multi-host revision.
  A post-release Cursor update check remains a publication task, not a local
  package-validation result.

## Publication boundary

Direct/custom installation is proven only where stated above. Curated
marketplace acceptance is controlled by each marketplace owner and must not be
claimed until that owner confirms it. The public package contains Community
skill instructions only; Core and Premium content remains on the Terraphim
Skills service.
