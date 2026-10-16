"""Read-only scoped hashes for parent-controlled cleanup; never reads config contents into output."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import sqlite3
import stat
from urllib.parse import quote

EVIDENCE = Path(__file__).resolve().parent
VALIDATION = EVIDENCE.parents[1]
PROJECT = Path('/private/tmp/terraphim-cursor-validation-20261016/public-project')
KEY = 'cursor/thirdPartyExtensibilityEnabled'


def identity(path):
    p = Path(path)
    row = {'path': str(p), 'exists': p.exists()}
    if not p.exists() and not p.is_symlink():
        return row
    info = p.lstat()
    row.update(symlink=stat.S_ISLNK(info.st_mode), regularFile=stat.S_ISREG(info.st_mode))
    if row['regularFile']:
        raw = p.read_bytes()
        row.update(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
    return row


def storage_key(path):
    row = {'path': str(path), 'key': KEY, 'exists': path.exists()}
    if not path.exists():
        return row
    connection = sqlite3.connect('file:' + quote(str(path), safe='/') + '?mode=ro', uri=True)
    try:
        connection.execute('PRAGMA query_only=ON')
        found = connection.execute('SELECT value FROM ItemTable WHERE key = ?', (KEY,)).fetchall()
        assert len(found) <= 1
        row['present'] = bool(found)
        if found:
            value = json.loads(found[0][0]); assert type(value) is bool
            row['value'] = value
    finally:
        connection.close()
    return row


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--label', required=True, choices=['before-cleanup','after-cleanup'])
    args = parser.parse_args()
    destination = EVIDENCE / (args.label + '-preservation.json')
    assert not destination.exists(), 'Preserve previous evidence'
    baseline = json.loads((VALIDATION/'native-isolation/snapshot.json').read_bytes())
    inherited = [identity(row['path']) for row in baseline['inheritedConfigurationHashes']]
    public = [PROJECT/'brief.md', PROJECT/'validate_brief.py']
    for directory in ['corpus','outputs']:
        public.extend(p for p in (PROJECT/directory).rglob('*') if p.is_file())
    receipt = {
        'observedAt': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'scope': 'Read-only fixed inherited-config hashes, one exact database key and task-owned public files. No broad profile or transcript enumeration.',
        'inheritedConfigurations': inherited,
        'inheritedConfigurationsMatchOriginalSnapshot': inherited == baseline['inheritedConfigurationHashes'],
        'storage': {name: storage_key(Path(row['path'])) for name,row in baseline['storage'].items()},
        'publicFiles': [identity(p) for p in sorted(public)],
        'ownedActiveConfigHashes': [identity(PROJECT/'.cursor/hooks.json'),identity(PROJECT/'.cursor/mcp.json')],
        'projectDiscoveryEntries': sorted(p.name for p in (PROJECT/'.terraphim').iterdir()),
        'c05OriginalFiles': [
            {'expected': row,
             'current': identity(row['path']),
             'matches': all(identity(row['path']).get(k) == row[k] for k in ('path','bytes','sha256'))}
            for row in json.loads((VALIDATION/'native-cli/receipt.json').read_bytes())['files']
        ],
        'configurationWritten': False,
        'limitations': ['Original configuration observation began after the isolated Third-Party Imports toggle; no pre-toggle normal-profile proof is invented.','Owned active configs are expected to change during approved validation and cleanup.']
    }
    if args.label == 'after-cleanup':
        before=json.loads((EVIDENCE/'before-cleanup-preservation.json').read_bytes())
        actual={r['path']:r for r in receipt['publicFiles']}
        receipt['previouslySavedPublicFilesPreserved']=all(actual.get(r['path'])==r for r in before['publicFiles'])
        receipt['newPublicFiles']=[r['path'] for r in receipt['publicFiles'] if r['path'] not in {b['path'] for b in before['publicFiles']}]
    destination.write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({'path':str(destination),'inheritedConfigurationsMatchOriginalSnapshot':receipt['inheritedConfigurationsMatchOriginalSnapshot'],'previouslySavedPublicFilesPreserved':receipt.get('previouslySavedPublicFilesPreserved')}))


if __name__ == '__main__':
    main()
