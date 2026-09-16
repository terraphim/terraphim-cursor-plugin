# Validation evidence — v0.2.2

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
