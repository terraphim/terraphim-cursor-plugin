# Connect the editor's words to search in Cursor

**Native acceptance requires the matching release qualification record.**
Source and inactive examples are not runtime proof or a public marketplace
listing. The complete plugin update cannot publish until actual Cursor hook
checks pass: **“Hold the update until hooks pass”**.

The [read-first setup command](commands/terraphim-setup.md) explains the choices.
It installs nothing and changes no configuration by itself. The four signed
instruction skills remain intact. The editor is the separately installed
Terraphim It VSIX; this plugin does not embed another editor.

## 1. Identify the separate dependencies

Use the exact public archives and executable hashes in
[release-inputs.json](release-inputs.json): **terraphim-agent/terraphim-grep
1.21.20**, **Continue grep MCP 0.1.1**, Python 3.11+ and `mcp==1.30.0`. Verify both
archive checksums and extracted executable digests before use. Homebrew may
supply another version; a newer version is not an automatic substitute for this
qualification. Original skill signatures authenticate skill files, not CLI
archives. Obtain a dependency only after choosing the corresponding release;
this plugin has no downloader or automatic installer.

For a source/development install, the supported project `workspaceOpen` hook
can return `pluginPaths` containing the reviewed absolute plugin directory.
Review and merge that one entry into existing project hooks; do not install it
globally or replace other entries. This route needs its own actual discovery
proof in the matching qualification record. See the official
[plugin](https://cursor.com/docs/plugins) and
[workspace hook](https://cursor.com/docs/hooks) contracts.

The initial native target is macOS ARM64. Installed app metadata alone is not a
vendor-signature or native acceptance result. Linux CLI/MCP tests do not qualify
native Linux Cursor; Windows, WSL and cloud agents remain unqualified.

If preparing the existing MCP runtime manually, create a dedicated venv in your
chosen tools directory and install its exact SDK requirement:

```sh
python3 -m venv /absolute/path/to/venv
/absolute/path/to/venv/bin/python -m pip install 'mcp==1.30.0'
```

These commands write that venv and download the SDK from its package registry.
Review them before execution. Use the released `server.py` directly; do not run
Continue's `install.py` or create `.continue` settings in Cursor.

## 2. Create the synonym, then export it

Open a public project brief in the existing editor. Select **Risk**, create
**Concern**, swap the wording, save and reopen. Export clean Markdown and the
knowledge graph into fresh, separate files; inspect the saved annotation and
verify Risk and Concern share the same concept ID in the JSON.

A concept note can use Logseq-compatible Markdown:

```markdown
# Risk
synonyms:: Concern
```

The grep `--thesaurus` flag takes the editor's exported **JSON**, not that
Markdown note. Export does not configure MCP, register an agent role, import
memory or activate a correction. The [public fixtures](examples/README.md) are
inputs only; native acceptance requires a newly exported graph.

Search the three files in [examples/corpus](examples/corpus/brief.md), not the
concept-note directory. For a literal baseline, run the separate CLI in Cursor
Shell from your chosen corpus workspace:

```sh
terraphim-grep Concern --search-only --haystack all --paths ./corpus --json -n 3
```

Expect zero passages because the corpus contains only Risk. The MCP server has
**no graph-free mode**; do not use an MCP response as this literal baseline.

## 3. Review one project MCP entry

[mcp.json.example](mcp.json.example) contains a retrieval-only entry for
`.cursor/mcp.json`. Every `/absolute/path/to/...` value is illustrative; replace
it with an existing, reviewed absolute path. Its binary digest is the actual
macOS ARM64 1.21.20 executable digest. Choose the matching manifest record on
another qualified platform instead of copying that digest blindly.

Inspect existing `mcpServers` first. Merge only the proposed entry. A name
collision requires another chosen name or manual reconciliation; do not replace
the whole file or a user's entry, and do not write global configuration. Keep
an exact before/after copy. After creating or changing the entry, open
**Customize → MCPs → Configure** and explicitly **Enable** the reviewed server;
Cursor may leave a new or changed entry disabled. Confirm its tools are listed
before calling them. Enabling or restarting the connection starts a local
process that reads the chosen graph and corpus.

Call `terraphim_retrieve` with `{"query":"Concern","limit":3}`. Inspect actual
`output.chunks`, filenames, line numbers and graph/binary digests; the intended
result is the three Risk passages with `answer:null`. This guide does not claim
that new Cursor result has already occurred. Query is nonblank and at most
2,000 characters; limit is an integer 1–50, not a boolean. The corpus is live,
not a filesystem sandbox. Returned passages are visible to Cursor's selected
model even when grep retrieval itself is local.

The answer tool is absent by default. Only after explicitly choosing a provider
and its permitted context, add `--allow-synthesis` to the reviewed args and
restart. That flag does not supply credentials. Invoke `terraphim_answer` with
the same query and compare its cited sources with retrieval. Do not paste
provider secrets into these examples or replace a failed provider call with
invented prose.

A changed graph at the same path must refuse until reviewed and restarted. A
new graph path also needs an entry edit. A different binary needs a verified
release and updated executable digest. No watcher silently admits changed
bytes. The transport retains its two-call, 90-second and 8 MiB bounds.

## 4. Keep memory and learning explicit

The [checked CLI workflow](../../docs/cli-workflows.md) supplies the authored
capture/show commands. In 1.21.20, memory uses
`TERRAPHIM_DEFAULT_DATA_PATH` or the OS config directory, followed by
`terraphim/evolution/cli-agent.json`; cwd and the exported graph do not isolate
it. Capture also writes through the configured DeviceStorage backend. For an
isolated qualification, set `TERRAPHIM_SETTINGS_PATH` to an existing private
settings directory with only the reviewed local dashmap profile, and set
`TERRAPHIM_DEFAULT_DATA_PATH` per memory command to the chosen disposable memory
root. Verify the actual stored JSON and new-process readback; never replace
HOME/CODEX_HOME or touch normal memory. Omit that data override for project
learning commands and require a real project `.terraphim` directory. Serialize
capture/show; this release does not provide concurrent-writer guarantees.

Learning annotations, authored correction rules, compilation and activation are
separate steps. Annotation alone must produce zero compiled mappings; a
reviewed explicit correction must produce a nonempty mapping and a `synonyms::`
note. Read actual files and returned IDs. No tag alone, `memory distill`,
`learn install-hook`, or export establishes execution or native activation.

## 5. Optional hooks remain inactive

[hooks.json.example](hooks.json.example) and
[policy.json.example](policy.json.example) are illustrations, not active files.
The policy defaults `rewriteEnabled:false`, `captureFailures:false` and
`evidence:{"enabled":false}`. **Automatic failure capture is unavailable** until
the actual selected Cursor result shape is qualified; do not enable it.

After native qualification, a deliberate setup can merge only the owned Shell
hook entries into project `.cursor/hooks.json`. Preserve existing entries,
resolve collisions manually and use the complete actual policy SHA256 in each
`--policy-sha256` argument. The example hash covers the exact example bytes;
changing paths/configuration requires fresh review and new hashes. Its quoted
commands illustrate spaces in paths. An edited hook configuration changes the
trust decision; this is not an OS sandbox.

The [role/settings examples](examples/README.md) keep exactly two roles, an
explicit compiled correction graph and an empty guard graph. Their absolute
local startup settings and existing owner-only directories must be admitted
before invoking the agent. Require a real empty project `.terraphim` discovery
layer with no `config.json` or `role-*.json`; never delete existing user config
to meet this condition. Keep data under the admitted project; remove ambient
storage/provider overrides from the child environment. A role JSON `--config`
alone does not isolate settings or learning writes.

The adapter delegates replacement to the released agent; it does not execute
the Shell command. A changed command needs exact rule attribution and a second
unmodified guard check. With rewriting off, preserve input. A hook rewrite is
not an execution result: compare attempted command, applied command, actual
host status and fresh selected output file before calling it successful.

The adapter admits the selected project in both the event cwd and
`tool_input.cwd` (or `working_directory` when supplied), preserving other input
fields. Its completion parser recognizes only the observed Cursor 3.24.18 and
3.25.6 success envelopes; unknown versions remain unqualified. The observed
failure event has a missing exit code; it cannot
prove a numeric failed-command result or authorize automatic learning capture.
A matching observed 3.25.6 guard-denial completion leaves its already-denied
receipt unchanged; it never becomes an executed or successful command.

The command examples specify `failClosed:true` and a 15-second host timeout.
Actual crash, timeout and denial behavior must be tested on the selected
Cursor; defaults must not be assumed. Each agent call has a five-second budget
and the adapter a 12-second total budget including startup. The pinned agent
performs an update check and initializes its service for hooks: startup may
use network and exceed those deadlines. Retain that failure and hold release;
do not invent a switch or package-manager receipt to suppress the check.
[Cursor's hook contract](https://cursor.com/docs/hooks) describes the host
interface; the matching release qualification record supplies execution proof.

## 6. Opt-in receipts and removal

The selected privacy scope is **“Commands, status and explicitly selected output
files only”**. Receipt capture remains off. If separately enabled after review,
use a private directory and explicit fresh-file allowlist; retain only commands,
actual status and admitted file identities/digests (up to 1 MiB per file).
Exclude general stdout/stderr, transcripts, email, environment and credentials.
Commands themselves can be sensitive; review them before enabling this option.

An applied rewrite is not completed execution. Missing/late/mismatched events,
a changed selected output, or a receipt-write failure retain incomplete/error
evidence. No retry executes the command. Separate optional failure capture,
when available, would persist redacted learning data; receipt permission does
not automatically grant that permission.

Inspect unfinished receipts without starting children, reading stdin, changing
records or retrying a Shell command:

```sh
python3 /absolute/path/to/plugin/integrations/cursor/hook_adapter.py \
  --policy /absolute/path/to/project/terraphim-policy.json \
  --policy-sha256 "$reviewed_policy_sha256" --inspect-receipts
```

Use the reviewed policy digest, not a value copied from a different setup.
Inspection requires evidence to be enabled in that policy. Stored `prepared`
or `applied` records are reported as effectively incomplete; partial atomic
write files remain preserved for manual investigation. No automatic deletion
or retry repairs them. After reviewed policy changes, choose a new empty
private evidence directory and rehash the policy/hook entry. Inspect old
receipts with their original unchanged policy, digest and matching reviewed
adapter/dependencies; a different policy or adapter cannot adopt those records.

Disable by removing only the entries you added, then restart the relevant
connection. Preserve other hooks/MCP entries, documents, graphs, original
skills, memories, learnings and old releases. Public marketplace admission is
still separate from a local install or GitHub CI release.
