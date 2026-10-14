#!/usr/bin/env python3
"""Read back every immutable public release asset and compare reviewed bytes."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

REPOSITORY = 'terraphim/terraphim-cursor-plugin'
MAX_ASSET_BYTES = 32 * 1024 * 1024

class ReleaseError(RuntimeError):
    """Published bytes do not satisfy the reviewed release contract."""

def _read(url: str, timeout: float, limit: int) -> bytes:
    try:
        with urlopen(Request(url, headers={'User-Agent': 'terraphim-release-readback/1'}), timeout=timeout) as response:
            if response.status != 200:
                raise ReleaseError(f'HTTP {response.status} for {url}')
            data = response.read(limit + 1)
            if len(data) > limit:
                raise ReleaseError(f'response exceeds byte limit: {url}')
            return data
    except HTTPError as error:
        error.close()
        raise ReleaseError(f'HTTP {error.code} for {url}') from error
    except (URLError, TimeoutError, OSError) as error:
        raise ReleaseError(f'cannot read {url}: {error}') from error

def verify_release(root: Path, tag: str, *, api_url: str | None = None,
                   asset_base: str | None = None, timeout: float = 15) -> dict:
    """Compare actual metadata and downloads with an already verified source tag."""
    if not re.fullmatch(r'v[0-9]+\.[0-9]+\.[0-9]+(?:-[A-Za-z0-9.-]+)?', tag):
        raise ReleaseError('invalid release tag')
    if timeout <= 0:
        raise ReleaseError('timeout must be positive')
    try:
        version = json.loads((root/'distribution/metadata.json').read_text())['plugin']['version']
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise ReleaseError('invalid source distribution metadata') from error
    if tag != f'v{version}':
        raise ReleaseError('source version differs from release tag')
    paths = [*sorted((root/'dist/autoclaw').glob('*.zip')), root/'dist/autoclaw/SHA256SUMS',
             root/'assets/v-model-overview.svg', root/'assets/v-model-overview.png']
    if len(paths) < 4 or any(not path.is_file() for path in paths):
        raise ReleaseError('source release assets missing')
    expected = {path.name:path for path in paths}
    api_url = api_url or f'https://api.github.com/repos/{REPOSITORY}/releases/tags/{tag}'
    asset_base = asset_base or f'https://github.com/{REPOSITORY}/releases/download/{tag}/'
    try:
        release = json.loads(_read(api_url, timeout, 1024 * 1024))
    except (ValueError, UnicodeError) as error:
        raise ReleaseError('release metadata is not JSON') from error
    if not isinstance(release, dict) or release.get('tag_name') != tag or release.get('draft') is not False:
        raise ReleaseError('release identity differs or is still a draft')
    assets = release.get('assets')
    if not isinstance(assets, list) or any(not isinstance(item, dict) for item in assets):
        raise ReleaseError('release assets are invalid')
    names = [item.get('name') for item in assets]
    if any(not isinstance(name, str) for name in names) or len(names) != len(set(names)) or set(names) != set(expected):
        raise ReleaseError('release asset set differs from reviewed source')
    results = {}
    for item in assets:
        name = item['name'];url = asset_base + quote(name, safe='');source = expected[name].read_bytes()
        if item.get('browser_download_url') != url or item.get('state') != 'uploaded' or item.get('size') != len(source):
            raise ReleaseError(f'invalid publication metadata for {name}')
        if len(source) > MAX_ASSET_BYTES:
            raise ReleaseError(f'source asset exceeds byte limit: {name}')
        downloaded = _read(url, timeout, MAX_ASSET_BYTES)
        if downloaded != source:
            raise ReleaseError(f'public asset differs from reviewed source: {name}')
        results[name] = {'bytes': len(downloaded), 'sha256': hashlib.sha256(downloaded).hexdigest(), 'url': url}
    return {'status': 'PASS', 'repository': REPOSITORY, 'tag': tag, 'assets': results,
            'scope': 'Actual public downloads equal verified source assets; curated listing and native host acceptance are separate.'}

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--tag', required=True)
    parser.add_argument('--receipt', type=Path, required=True)
    args = parser.parse_args()
    try:
        result = verify_release(args.root, args.tag);status = 0
    except ReleaseError as error:
        result = {'status': 'FAIL', 'tag': args.tag, 'error': str(error)};status = 1
    args.receipt.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result))
    return status

if __name__ == '__main__':
    sys.exit(main())
