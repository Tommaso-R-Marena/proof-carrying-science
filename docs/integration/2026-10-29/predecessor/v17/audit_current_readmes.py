"""Inventory versioned READMEs and check local links in current entry points.

No historical/vendor/source-bound bytes are rewritten to refresh navigation.
This is documentation checking, never verification or publication authority.
"""
from pathlib import Path
import hashlib
import json
import re
import subprocess
import sys
from urllib.parse import unquote,urlsplit

ROOT=Path(__file__).resolve().parents[1]
CURRENT=frozenset(('README.md','formal/README.md','site/README.md','research/README.md',
    'research/integration_v2/README.md','research/public_study_validation_v1_results/README.md',
    'docs/integration/2026-10-29/README.md'))


def audit():
    names=subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode().split('\0')
    rows=[];errors=[]
    for name in sorted(n for n in names if 'readme' in Path(n).name.lower()):
        path=ROOT/name;raw=path.read_bytes()
        if name in CURRENT:scope='CURRENT_ENTRY_POINT'
        elif '/vendor/' in name or '/upstream/' in name:scope='PRESERVED_UPSTREAM_SOURCE'
        else:scope='PRESERVED_VERSIONED_SOURCE_OR_EVIDENCE'
        rows.append(dict(path=name,sha256=hashlib.sha256(raw).hexdigest(),scope=scope))
        if name not in CURRENT:continue
        for link in re.findall(r'(?<!!)\[[^\]]+\]\(([^\s)]+)\)',raw.decode()):
            link=link.strip('<>');uri=urlsplit(link)
            if uri.scheme or link.startswith(('#','/')):continue
            target=(path.parent/unquote(uri.path)).resolve()
            if not target.is_relative_to(ROOT) or not target.exists():errors.append(dict(path=name,link=link))
    if not CURRENT.issubset({r['path'] for r in rows}):raise ValueError('current entry points must be tracked')
    return dict(format='pcs-readme-audit-v1',current_entry_points=sorted(CURRENT),readmes=len(rows),
        local_current_links_valid=not errors,errors=errors,files=rows,
        historical_bytes_rewritten=False,live_publication_state='GitHub integration PR and protected checks; dated records retain source-freeze scope')


if __name__=='__main__':
    result=audit();raw=json.dumps(result,indent=2)+'\n'
    if len(sys.argv)>1:Path(sys.argv[1]).write_text(raw)
    else:print(raw,end='')
    raise SystemExit(0 if result['local_current_links_valid'] else 1)
