"""Authenticated host-local memoization, never a scientific authority.

The key lives outside imported projects. HMAC detects accidental corruption and
unauthorized edits without that key; same-user/host compromise remains open.
Independent replay ignores all cached verdicts and invokes the checker again.
"""
from __future__ import annotations
import hashlib
import hmac
import os
from pathlib import Path
import secrets
import stat
import sys
import tempfile

from pcs.jsonio import strict_json_loads
from .intake import canonical, digest, _regular
from .checks import bindings_valid


def checker_context():
    package=Path(__file__).parent;root=package.parents[1]
    sources={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest()
             for p in sorted(package.glob('*.py')) if not p.name.startswith('test_')}
    # Include reused semantic/authority source closure, not just wrapper version.
    for name in ('pcs/proof_translation_v06.py','pcs/jsonio.py','pcs/experimental/prover/environment.py',
                 'pcs/experimental/prover/language.py','pcs/experimental/prover/ir.py',
                 'pcs/experimental/prover/induction_ir.py','pcs/experimental/prover/induction_language.py','formal/PCSProofProbe.lean'):
        sources[name]=hashlib.sha256((root/name).read_bytes()).hexdigest()
    import shutil,subprocess
    lean=shutil.which('lean')
    toolchain={'available':False}
    if lean:
        try:
            version=subprocess.check_output([lean,'--version'],text=True,timeout=10).strip()
            prefix=subprocess.check_output([lean,'--print-prefix'],text=True,timeout=10).strip()
            binary=Path(prefix)/'bin/lean'
            # Lean imported library integrity remains an explicit host/toolchain assumption.
            toolchain={'available':True,'version':version,'binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest()}
        except (OSError,subprocess.SubprocessError):toolchain={'available':False}
    return {'format':'pcs-scientific-checker-context-v1','sources':sources,'python':sys.version,'lean':toolchain,
            'policy':'closed-source-checks-only;scientific-authority-denied;no-imported-training'}


class CheckCache:
    def __init__(self,path,context=None):
        self.path=Path(path).absolute()
        if self.path.is_symlink():raise ValueError('cache symlink')
        self.path.mkdir(parents=True,exist_ok=True,mode=0o700)
        info=self.path.stat()
        if info.st_uid!=os.getuid() or info.st_mode&0o077:raise ValueError('cache directory must be host-private')
        keypath=self.path/'host-key'
        if not keypath.exists():
            try:
                fd=os.open(keypath,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_NOFOLLOW,0o600)
                try:os.write(fd,secrets.token_bytes(32))
                finally:os.close(fd)
            except FileExistsError:pass
        self.key=_regular(keypath,32)
        if len(self.key)!=32 or keypath.stat().st_mode&0o077:raise ValueError('invalid cache key')
        self.context=context or checker_context()
    def _key(self,obligation):return digest({'obligation':obligation,'context':self.context})
    def get(self,obligation,artifacts):
        bindings_valid(obligation,artifacts)
        key=self._key(obligation)
        try:
            envelope=strict_json_loads(_regular(self.path/(key+'.json'),2*1024*1024).decode())
            if set(envelope)!={'payload','mac'}:return None
            expected=hmac.new(self.key,canonical(envelope['payload']),hashlib.sha256).hexdigest()
            if not hmac.compare_digest(expected,envelope['mac']):return None
            p=envelope['payload']
            if p['key']!=key or p['context_sha256']!=digest(self.context) or p['result']['obligation_id']!=obligation['id']:return None
            if p['result']['status'] not in {'VERIFIED_SUPPORTED','REFUTED'}:return None
            return p['result']
        except (OSError,ValueError,KeyError,TypeError):return None
    def put(self,obligation,result,artifacts):
        bindings_valid(obligation,artifacts)
        if result['status'] not in {'VERIFIED_SUPPORTED','REFUTED'}:return
        key=self._key(obligation)
        payload={'key':key,'context_sha256':digest(self.context),'result':result}
        encoded=canonical({'payload':payload,'mac':hmac.new(self.key,canonical(payload),hashlib.sha256).hexdigest()})
        fd,name=tempfile.mkstemp(prefix='.pending-',dir=self.path)
        try:
            with os.fdopen(fd,'wb') as stream:stream.write(encoded);stream.flush();os.fsync(stream.fileno())
            os.replace(name,self.path/(key+'.json'))
        finally:
            if os.path.exists(name):os.unlink(name)
