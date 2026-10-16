# Install Terraphim command dependencies

Released pack 0.2.6 contains three CLI instruction skills and an editor
companion; it uses the existing online/editor extension and the
same two separately installed CLIs. No skill installs software automatically.
The editor and Kilo catalog routes require their own installation checks.

## Homebrew installation

On macOS or Linux with Homebrew:

```bash
brew tap terraphim/terraphim
brew install terraphim-grep terraphim-agent
terraphim-grep --version
terraphim-agent --version
terraphim-agent learn --help
terraphim-agent memory --help
```

The formula versions can differ from the releases used in individual examples.
The [graph search and authored-memory workflow](cli-workflows.md) was checked
with Terraphim Clients 1.21.20 and links to its release archives and checksums.
Check the installed versions and help before running its commands. If the existing
binaries support the workflow you need, do not reinstall them.

## Update

```bash
brew update
brew upgrade terraphim-grep terraphim-agent
```

Run the four probes again after upgrading. The installed `--help` output is the
authority for available options.

## Remove

```bash
brew uninstall terraphim-grep terraphim-agent
brew untap terraphim/terraphim
```

Removing the binaries does not remove learning or memory data. Review local data
locations before deleting user-created state.

## Without Homebrew

Follow the [Terraphim installation guide](https://terraphim-skills.md/docs/non-technical/)
to download the correct archive and `SHA256SUMS`.
Verify the archive checksum before extracting it, then verify the executable
digest pinned by the integration you chose. The selected Clients 1.21.20
evidence establishes checksums, not a blanket archive signature or notarization
claim. Check any supplied platform signature separately; do not bypass Gatekeeper.

## Troubleshooting

- If a host cannot resolve a binary, restart it after installation so it receives
  the current `PATH`.
- Homebrew usually installs to `/opt/homebrew/bin` on Apple Silicon,
  `/usr/local/bin` on Intel macOS, and `/home/linuxbrew/.linuxbrew/bin` on Linux.
- Do not copy credentials or private memory into diagnostics.
- Do not use `xattr` or Gatekeeper-bypass commands. Verify the official archive
  and report a signature failure instead.

The [Cursor setup candidate](../integrations/cursor/README.md) pins Clients
1.21.20, Continue grep MCP 0.1.1 and Python's `mcp==1.30.0`. Its
[release input manifest](../integrations/cursor/release-inputs.json) records
actual archive/executable digests. No dependency is installed automatically;
that setup and its native qualification remain separate from these instructions.
