# Validation evidence — v0.2.1

## Purpose

Patch release `v0.2.1` preserves the reviewed `v0.2.0` Community pack and fixes
release automation so GitHub Actions fetches the signed annotated tag object
before running `git verify-tag`.

## Regression addressed

The first `v0.2.0` release run checked out only the tagged commit. Git therefore
reported `cannot verify a non-tag object of type commit` even though the pushed
tag was signed and verified locally. The release checkout now uses full history,
including annotated tag objects, while keeping persisted Git credentials
disabled.

## Required evidence

- generator drift check passes;
- all distribution unit tests pass, including the tag-fetch regression test;
- Ruff, actionlint, Claude strict validation, and `git diff --check` pass;
- AutoClaw archives reproduce byte-for-byte and their checksums match;
- the signed `v0.2.1` tag verifies against `.github/trusted-release-signers`;
- the GitHub release workflow succeeds and publishes the six expected assets.
