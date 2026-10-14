# v0.2.4 CLI qualification

Checked 14 October 2026 using the checksummed **Clients 1.21.20 Linux aarch64**
release binaries in a disposable, network-disabled container. No normal host
profiles were mounted. Memory used a task-only `XDG_CONFIG_HOME`; `HOME` was
unchanged. This is CLI/package qualification, not a native host acceptance claim.

| Scenario | Actual result |
|---|---|
| Search Concern without the graph | Zero passages; `answer: null` |
| Search with the editor-exported Risk/Concern JSON | Three Risk passages; `answer: null` |
| Explicit authored-memory capture and show | Same generated ID, exact text and source tag |
| Memory validation | Reports `heuristic-v1` |
| Memory export | Saved artifact contains the actual captured ID |
| Retirement | Saved pending proposal; captured item still readable afterward |
| Failure learning in an explicit project `.terraphim` directory | Actual failing command captured; verified correction saved against its ID |
| Failure annotation vs rewrite rule | Annotation alone leaves compiled rule data empty |
| Explicit `learn correction add` + compile/export | Saved rule maps the actual failing numeric printf format to the executed string format; KG Markdown contains `synonyms::` |

The numeric printf command exited 1. The separately executed corrected command
returned `release-fixture` plus a newline. The saved compiled mapping and exported
Markdown are [available beside the search and memory outputs](v0.2.4/), with
[SHA256 checksums](v0.2.4/SHA256SUMS). These are saved program outputs, not example
inputs presented as successful execution.

All three skill manifests are version **1.0.3**, signed by the existing publisher
key `261c6820525270bfe2a5daaa5bf3f581bd9bc193e1a0148010e870a3a63ad959`.
`tsm 0.1.16 verify --trusted-key` independently verified the signatures and all
four declared files in each skill. Both CLI workflow instructions and the graph
are included in each individual skill archive.

The 26 repository tests, generated-manifest check, and two independent archive
builds passed. Historical release tags and downloadable assets were not changed.
The existing CI verifies the signed Git tag and reproducible ZIPs before release.
