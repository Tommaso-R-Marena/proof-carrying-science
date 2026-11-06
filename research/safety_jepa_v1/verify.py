"""Bounded artifact integrity checks, not mathematical or scientific authority."""
import argparse
import hashlib
import json
from pathlib import Path,PurePosixPath
import stat
from pcs.jsonio import strict_json_loads


def verify(directory):
    root=Path(directory).resolve()
    with (root/'SHA256.json').open('rb') as stream:raw=stream.read(1_000_001)
    if len(raw)>1_000_000:raise ValueError('manifest bound exceeded')
    m=strict_json_loads(raw.decode())
    if set(m)!={'format','authority','files'} or m['format']!='pcs-safety-jepa-evidence-v1' or m['authority']!='NONE':
        raise ValueError('unsupported manifest')
    census={str(p.relative_to(root)) for p in root.rglob('*') if p.is_file() and p!=root/'SHA256.json'}
    if set(m['files'])!=census:raise ValueError('artifact census mismatch')
    for name,record in m['files'].items():
        path=PurePosixPath(name)
        if path.is_absolute() or '..' in path.parts or '\\' in name:raise ValueError('invalid artifact path')
        target=root/name
        if target.is_symlink() or not target.resolve().is_relative_to(root) or not stat.S_ISREG(target.lstat().st_mode):
            raise ValueError('nonregular or escaping artifact')
        if type(record['size']) is not int or not 0<=record['size']<=16_000_000:raise ValueError('artifact byte bound')
        with target.open('rb') as stream:raw=stream.read(16_000_001)
        if len(raw)!=record['size'] or hashlib.sha256(raw).hexdigest()!=record['sha256']:raise ValueError('artifact digest mismatch')
    return {'files_verified':len(m['files']),'authority':'NONE'}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--directory',required=True)
    print(json.dumps(verify(p.parse_args().directory),sort_keys=True))
if __name__=='__main__':main()
