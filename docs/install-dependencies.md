# Install Terraphim command dependencies

The three skills are workflow instructions. They call two local binaries and never
install software automatically.

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

The formulae use immutable, signed and checksummed v1.21.14 archives. If both
binaries already pass the four probes, do not reinstall them.

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

Download the correct archive and `SHA256SUMS` from the
[v1.21.14 release](https://github.com/terraphim/terraphim-clients/releases/tag/v1.21.14).
Verify the archive checksum before extracting it. macOS archives are signed and
notarized; do not bypass Gatekeeper. Linux archives are signed through the release
checksum and signature chain.

## Troubleshooting

- If a host cannot resolve a binary, restart it after installation so it receives
  the current `PATH`.
- Homebrew usually installs to `/opt/homebrew/bin` on Apple Silicon,
  `/usr/local/bin` on Intel macOS, and `/home/linuxbrew/.linuxbrew/bin` on Linux.
- Do not copy credentials or private memory into diagnostics.
- Do not use `xattr` or Gatekeeper-bypass commands. Verify the official archive
  and report a signature failure instead.
