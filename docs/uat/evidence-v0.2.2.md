# Validation evidence — v0.2.2

Date: 2026-09-16

## Purpose

Patch release `v0.2.2` preserves the reviewed Community pack and makes release
signature verification independent of the tag reference created by
`actions/checkout`.

## Regression addressed

The `v0.2.1` workflow fetched complete history, but GitHub Actions still left
the event's local tag name pointing at the peeled commit. The remote
`refs/tags/v0.2.1` remained an intact signed annotated tag. Validation now
fetches the remote tag into `refs/release-tags/<version>`, proves its peeled
commit equals `GITHUB_SHA`, and verifies the signature on that private ref in
both the read-only validation job and the write-scoped publication job.

The repository must also have an active tag ruleset for `v*` that restricts tag
updates and deletions without granting routine bypass. This closes the remaining
time-of-check/time-of-use window between re-verification and GitHub's release
creation API. Release publication must not proceed without that operational
control.

## Required evidence

- generator drift and all distribution tests pass;
- Ruff, actionlint, Claude strict validation, and `git diff --check` pass;
- AutoClaw archives reproduce byte-for-byte and their checksums match;
- the signed `v0.2.2` tag verifies against `.github/trusted-release-signers`;
- the active `v*` tag ruleset restricts updates and deletions;
- GitHub release validation verifies the private tag ref and publishes the six
  expected assets.

## Observed release evidence

- The active [Immutable release tags ruleset](https://github.com/terraphim/terraphim-cursor-plugin/rules/23531392)
  targets `refs/tags/v*`, enforces update, deletion, and non-fast-forward
  restrictions, has no bypass actors, and reports that the current user can
  never bypass it.
- Pull request [#4](https://github.com/terraphim/terraphim-cursor-plugin/pull/4)
  merged as `6ea3bf47fd7585d8bc518d782b371f281e20e12b` after its validation check passed.
- The annotated `v0.2.2` tag peels to that exact merge commit and verifies as a
  good SSH signature for `alex@metacortex.engineer` with trusted ED25519 key
  fingerprint `SHA256:sfUIepNnrxdFgZDGWa9u8Kjzrdqh8pxvoovhGgBvJoQ`.
- [Release workflow run 35069801681](https://github.com/terraphim/terraphim-cursor-plugin/actions/runs/35069801681)
  completed successfully.
- [GitHub release v0.2.2](https://github.com/terraphim/terraphim-cursor-plugin/releases/tag/v0.2.2)
  is public, non-draft, and non-prerelease with the three deterministic skill
  ZIPs, `SHA256SUMS`, and the SVG and PNG V-model artwork.
- A fresh download passed `shasum -a 256 -c SHA256SUMS` and `unzip -t` for all
  three archives.

## Host validation

- **Kimi Code 1.44.0:** installed the immutable v0.2.2 checkout in an isolated
  `KIMI_SHARE_DIR`; `plugin info` reported v0.2.2 and exactly the three intended
  `SKILL.md` files were present.
- **Claude Code 2.1.270:** strict validation passed; an isolated configuration
  added the publisher marketplace and installed
  `terraphim-skills-intro@terraphim-skills` v0.2.2 with exactly three skills.
- **skills.sh:** live repository discovery with telemetry disabled reported
  `Found 3 skills` and listed only the three Community skills.
- **Hermes Agent v1.0.0:** an isolated `HERMES_HOME` added the GitHub tap,
  inspected all skills, classified each as `SAFE`, installed all three, and
  listed exactly three hub-installed Community skills.
- **AutoClaw:** all three release ZIPs pass their checksums, archive integrity,
  and deterministic rebuild checks. Real desktop import remains outstanding
  because the validation Mac was locked; archive proof is not represented as
  desktop UAT.
- **ZCode:** the official validator accepts 22 plugins including Terraphim and
  `build_dist.py` creates an integrity-tested v0.2.2 package containing the
  canonical Apache-2.0 `LICENSE` and `NOTICE`. Submission
  [PR #13](https://github.com/zai-org/zcode-plugins/pull/13) is open; its Actions
  require maintainer approval and real GUI UAT remains transparently outstanding.
- **Grok Build (xAI):** submission
  [PR #730](https://github.com/xai-org/plugin-marketplace/pull/730) pins the exact
  v0.2.2 commit. Catalogue validation and component-index checks pass when
  reproduced locally against the submitted head. GitHub-hosted Actions await
  maintainer approval; the hosted Socket security and Semgrep checks are green.
  Maintainer merge remains external.

The package contains Community skill instructions only. Curated marketplace
acceptance remains a third-party decision and is never inferred from direct
installation or a successful submission check.
