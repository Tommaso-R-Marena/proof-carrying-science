"""Pinned actual GGUF inference; localhost only, no hosted inference API."""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import tarfile
import time
import urllib.request

from research.llm_firewall_v1.monitor import F_ADD_SEALS,F_GET_SEALS,REQUIRED_SEALS,digest

HERE=Path(__file__).resolve().parent
PINS=json.loads((HERE/'pins.json').read_text())
MODELS=tuple(a['repository'] for a in PINS['artifacts'] if a['kind']=='weights')


def file_hash(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()


def resource(model):
    return next(a for a in PINS['artifacts'] if a.get('repository')==model)


def download(folder:Path):
    """Exact publicly available artifacts, pinned revisions, streamed size/hash gates."""
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True);results=[]
    for a in PINS['artifacts']:
        p=folder/a['name']
        if p.exists():
            if p.stat().st_size!=a['size'] or file_hash(p)!=a['sha256']:
                raise ValueError('Existing artifact differs from reviewed pin')
        else:
            partial=p.with_suffix(p.suffix+'.partial');n=0;h=hashlib.sha256()
            with urllib.request.urlopen(a['url'],timeout=60) as r,partial.open('xb') as out:
                if r.status!=200:raise ValueError('Artifact download unavailable')
                while b:=r.read(1024*1024):
                    n+=len(b)
                    if n>a['size']:raise ValueError('Oversized artifact')
                    h.update(b);out.write(b)
            if n!=a['size'] or h.hexdigest()!=a['sha256']:
                raise ValueError('Downloaded artifact differs from reviewed pin; partial retained')
            partial.rename(p)
        results.append(dict(name=a['name'],sha256=a['sha256'],bytes=a['size'],verified=True))
    runtime=folder/'runtime'/PINS['runtime_folder']
    if not runtime.exists():
        archive=folder/PINS['artifacts'][0]['name']
        with tarfile.open(archive) as tar:
            for m in tar.getmembers():
                if Path(m.name).is_absolute() or '..' in Path(m.name).parts:
                    raise ValueError('Unsafe release archive path')
            tar.extractall(folder/'runtime',filter='data')
    check_runtime(folder)
    return dict(verified=True,resources=results)


def check_runtime(folder):
    root=Path(folder)/'runtime'/PINS['runtime_folder']
    actual={p.relative_to(root).as_posix():file_hash(p) for p in root.rglob('*') if p.is_file()}
    if actual!=PINS['runtime_files']:raise ValueError('Runtime executable/library inventory differs from reviewed release')
    return root


def sealed_snapshot(path:Path,*,size:int,sha256:str):
    """Copy AND hash the consumed bytes, then seal; never infer from original path."""
    fd=os.memfd_create('pcs-local-model-weights',os.MFD_CLOEXEC|os.MFD_ALLOW_SEALING)
    h=hashlib.sha256();n=0
    try:
        with Path(path).open('rb') as src:
            while b:=src.read(1024*1024):
                n+=len(b)
                if n>size:raise ValueError('Oversized weight snapshot')
                h.update(b);view=memoryview(b)
                while view:view=view[os.write(fd,view):]
        if n!=size or h.hexdigest()!=sha256:raise ValueError('Weight snapshot does not match pinned bytes')
        fcntl.fcntl(fd,F_ADD_SEALS,REQUIRED_SEALS)
        if fcntl.fcntl(fd,F_GET_SEALS)&REQUIRED_SEALS!=REQUIRED_SEALS:
            raise ValueError('Kernel weight seals unavailable')
        return fd
    except BaseException:
        os.close(fd);raise


def request_body(model,messages):
    return dict(model=model,messages=messages,temperature=0,seed=42,max_tokens=256,
                response_format={'type':'json_object'},chat_template_kwargs={'enable_thinking':False})


def extract(raw,model):
    d=json.loads(raw)
    if d.get('model')!=model or not str(d.get('system_fingerprint','')).startswith('b11827-970b51ce7'):
        raise ValueError('Unexpected local model/runtime identity')
    cs=d.get('choices')
    if type(cs) is not list or len(cs)!=1 or cs[0].get('finish_reason')!='stop':
        raise ValueError('Complete single local response required')
    m=cs[0]['message'];content=m.get('content')
    if m.get('tool_calls') or m.get('function_call') or m.get('refusal') or type(content) is not str or len(content.encode())>4096:
        raise ValueError('Bounded local JSON text proposal required')
    return content.encode()


class LocalModel:
    def __init__(self,folder:Path,model:str,out:Path):
        if model not in MODELS:raise ValueError('Reviewed model ID required')
        self.folder=Path(folder);self.model=model;self.out=Path(out);self.out.mkdir(parents=True,exist_ok=False)
        self.calls=0;self.process=None;self.fd=None;self.log=None
        self.opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))  # Local loopback only.
        root=check_runtime(self.folder);a=resource(model)
        try:
            self.fd=sealed_snapshot(self.folder/a['name'],size=a['size'],sha256=a['sha256'])
            with socket.socket() as s:
                s.bind(('127.0.0.1',0));self.port=s.getsockname()[1]
            command=[str(root/'llama-server'),'-m','/proc/self/fd/'+str(self.fd),
                     '--host','127.0.0.1','--port',str(self.port),'--threads','2','--threads-batch','2',
                     '--ctx-size','4096','--parallel','1','--n-gpu-layers','0','--offline',
                     '--reasoning','off','--alias',model,'--no-webui']
            self.log=(self.out/'server.log').open('wb')
            # No configured cloud/GitHub credentials or inherited loader overrides.
            self.process=subprocess.Popen(command,pass_fds=(self.fd,),stdout=self.log,stderr=subprocess.STDOUT,
                                          env={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8','OMP_NUM_THREADS':'2'})
            deadline=time.monotonic()+90
            while True:
                if self.process.poll() is not None:raise ValueError('Actual local weight engine exited; see server.log')
                try:
                    if self.http('/health')['status']=='ok':break
                except OSError:pass
                if time.monotonic()>deadline:raise ValueError('Actual local engine failed readiness')
                time.sleep(.1)
            check_runtime(self.folder)
            maps=Path('/proc/'+str(self.process.pid)+'/maps').read_text()
            mappings=[s for s in maps.splitlines() if 'memfd:pcs-local-model-weights' in s]
            if not mappings:raise ValueError('Expected sealed GGUF memory mapping absent')
            self.binding=dict(model=model,weights=a,weight_snapshot_sha256=a['sha256'],
                snapshot_bytes=a['size'],seals=fcntl.fcntl(self.fd,F_GET_SEALS),
                runtime_release=PINS['runtime_release'],runtime_commit=PINS['runtime_commit'],
                runtime_files=PINS['runtime_files'],command=command,weight_mappings=mappings,
                local_cpu=True,gpu_layers=0,remote_model_api=False,compiler_runtime_trusted=True,
                general_model_safety_proved=False,production_authority=False)
            (self.out/'binding.json').write_text(json.dumps(self.binding,indent=2)+'\n')
            (self.out/'props.json').write_text(json.dumps(self.http('/props'),indent=2)+'\n')
        except BaseException:self.close();raise

    def http(self,path,body=None):
        raw=None if body is None else json.dumps(body,separators=(',',':')).encode()
        req=urllib.request.Request('http://127.0.0.1:'+str(self.port)+path,data=raw,headers={'Content-Type':'application/json'})
        with self.opener.open(req,timeout=180) as r:
            value=r.read(1024*1024+1)
            if len(value)>1024*1024 or r.status!=200:raise ValueError('Bounded successful local response required')
        return json.loads(value) if body is None else value

    def complete(self,model,messages):
        if model!=self.model or self.calls>=64 or self.process.poll() is not None:
            raise ValueError('Fixed live local model and request budget required')
        if fcntl.fcntl(self.fd,F_GET_SEALS)&REQUIRED_SEALS!=REQUIRED_SEALS:
            raise ValueError('Sealed weights unavailable')
        body=request_body(model,messages);raw=json.dumps(body,separators=(',',':')).encode()
        if len(raw)>32768:raise ValueError('Prompt budget exceeded')
        i=self.calls;self.calls+=1;folder=self.out/f'call-{i:03d}';folder.mkdir()
        (folder/'request.json').write_bytes(raw);start=time.monotonic()
        response=self.http('/v1/chat/completions',body)
        (folder/'response.json').write_bytes(response)
        provenance=dict(call=i,model=model,weight_sha256=resource(model)['sha256'],
                        runtime_commit=PINS['runtime_commit'],request_sha256=digest(raw),
                        response_sha256=digest(response),seconds=round(time.monotonic()-start,6),
                        usage=json.loads(response).get('usage'),remote_model_api=False)
        (folder/'provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
        return extract(response,model),provenance

    def close(self):
        try:
            if self.process is not None:
                self.process.terminate()
                try:self.process.wait(timeout=10)
                except subprocess.TimeoutExpired:self.process.kill();self.process.wait(timeout=10)
        finally:
            if self.log is not None:self.log.close();self.log=None
            if self.fd is not None:os.close(self.fd);self.fd=None

    def __enter__(self):return self
    def __exit__(self,*_):self.close()
