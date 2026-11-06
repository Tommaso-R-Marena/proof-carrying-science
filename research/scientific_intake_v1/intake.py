"""Bounded byte-preserving project intake. Imported code is data, never execution."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path,PurePosixPath
import stat
import subprocess
import sys
import unicodedata
import zipfile

MAX_FILES=256
MAX_FILE=5*1024*1024
MAX_TOTAL=64*1024*1024
MAX_ARCHIVE=32*1024*1024
MAX_RATIO=100

class IntakeError(ValueError):pass

def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
def digest(value):return hashlib.sha256(canonical(value)).hexdigest()


def safe_name(name):
    if type(name) is not str or not name or '\\' in name or ':' in name or any(ord(c)<32 for c in name):raise IntakeError('ambiguous file name')
    p=PurePosixPath(name)
    if p.is_absolute() or any(c in ('','.','..') for c in name.split('/')) or len(p.parts)>16:raise IntakeError('unsafe path')
    for part in p.parts:
        if part.rstrip(' .')!=part or part.split('.')[0].upper() in {'CON','PRN','AUX','NUL',*[f'COM{i}' for i in range(1,10)],*[f'LPT{i}' for i in range(1,10)]}:raise IntakeError('nonportable path')
    normalized=unicodedata.normalize('NFKC',name)
    if normalized!=name and (normalized.count('/')!=name.count('/') or any(c in ('','.','..') for c in normalized.split('/')) or any(x in normalized for x in ('..','\\',':'))):raise IntakeError('ambiguous Unicode path')
    return normalized.casefold()


def _read_fd(fd,limit):
    before=os.fstat(fd)
    if not stat.S_ISREG(before.st_mode) or before.st_nlink!=1 or before.st_size>limit:raise IntakeError('nonregular, linked or oversized input')
    chunks=[];size=0
    while True:
        data=os.read(fd,min(65536,limit+1-size))
        if not data:break
        chunks.append(data);size+=len(data)
        if size>limit:raise IntakeError('input exceeds resource bound')
    after=os.fstat(fd)
    if (before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns,before.st_ctime_ns)!=(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns):raise IntakeError('input changed during snapshot')
    return b''.join(chunks)


def _regular(path,limit):
    fd=os.open(path,os.O_RDONLY|os.O_NONBLOCK|os.O_NOFOLLOW|os.O_CLOEXEC)
    try:return _read_fd(fd,limit)
    finally:os.close(fd)


def _walk(directory_fd,prefix='',budget=None):
    budget = [MAX_FILES*2] if budget is None else budget
    names=[]
    with os.scandir(directory_fd) as entries:
        for entry in entries:
            budget[0]-=1
            if budget[0]<0:raise IntakeError('directory entry bound')
            names.append(entry.name)
    for name in sorted(names):
        rel=prefix+name;safe_name(rel)
        info=os.stat(name,dir_fd=directory_fd,follow_symlinks=False)
        if stat.S_ISDIR(info.st_mode):
            fd=os.open(name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=directory_fd)
            try:yield from _walk(fd,rel+'/',budget)
            finally:os.close(fd)
        elif stat.S_ISREG(info.st_mode):
            fd=os.open(name,os.O_RDONLY|os.O_NONBLOCK|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=directory_fd)
            try:yield rel,_read_fd(fd,MAX_FILE),{'kind':'directory_file','relative_path':rel}
            finally:os.close(fd)
        else:raise IntakeError('symlink or special entry is unsupported')


def _archive(raw):
    import io
    archive_hash=hashlib.sha256(raw).hexdigest()
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        infos=archive.infolist()
        if len(infos)>MAX_FILES*2:raise IntakeError('archive entry bound')
        seen=set();files=set();total=0
        for info in infos:
            if info.orig_filename != info.filename:raise IntakeError('truncated archive filename')
            name=info.filename.rstrip('/') if info.is_dir() else info.filename
            normalized=safe_name(name)
            if normalized in seen:raise IntakeError('duplicate or ambiguous archive entry')
            if any(normalized.startswith(p+'/') for p in files) or (not info.is_dir() and any(p.startswith(normalized+'/') for p in seen)):raise IntakeError('archive file/directory collision')
            seen.add(normalized)
            if not info.is_dir():files.add(normalized)
            mode=(info.external_attr>>16)&0xffff
            if stat.S_IFMT(mode) not in (0,stat.S_IFREG,stat.S_IFDIR):raise IntakeError('archive symlink or special entry')
            if info.flag_bits&1 or info.compress_type not in (zipfile.ZIP_STORED,zipfile.ZIP_DEFLATED):raise IntakeError('unsupported encrypted/compressed archive')
            if info.is_dir():continue
            total+=info.file_size
            if info.file_size>MAX_FILE or total>MAX_TOTAL or info.file_size>MAX_RATIO*max(1,info.compress_size):raise IntakeError('archive expansion bound')
            with archive.open(info) as stream:data=stream.read(MAX_FILE+1)
            if len(data)!=info.file_size or len(data)>MAX_FILE:raise IntakeError('archive size mismatch')
            yield name,data,{'kind':'zip_member','archive_sha256':archive_hash,'member':name}


def adapter_observation(name,path,*,timeout=15):
    """Isolated parser process, not an unconditional OS security sandbox."""
    env={'PATH':os.environ.get('PATH',''),'PYTHONPATH':str(Path(__file__).resolve().parents[2]),'LANG':'C.UTF-8'}
    command=[sys.executable,'-m','research.scientific_intake_v1.worker',name]
    try:
        raw=_regular(path,MAX_FILE)
        p=subprocess.run(command,input=raw,capture_output=True,timeout=timeout,env=env,cwd=Path(__file__).resolve().parents[2])
        if p.returncode or len(p.stdout)>16*1024*1024:raise IntakeError('parser failed or exceeded bound')
        from pcs.jsonio import strict_json_loads
        return strict_json_loads(p.stdout.decode('utf-8'))
    except (OSError,ValueError,subprocess.TimeoutExpired) as exc:
        return {'adapter':'isolated-parser','version':'1','status':'ERROR','segments':[],'warnings':[type(exc).__name__],'capabilities':{'executed_imported_code':False}}


def ingest(source,output):
    source=Path(source).absolute();output=Path(output).absolute()
    if source.is_symlink():raise IntakeError('source cannot be a symlink')
    if output.exists():raise IntakeError('refuse output overwrite')
    resolved=source.resolve()
    if output.resolve().is_relative_to(resolved):raise IntakeError('output cannot be inside source')
    output.mkdir(parents=True,mode=0o700);objects=output/'objects';objects.mkdir(mode=0o700)
    original_archive=None
    if source.is_dir():
        fd=os.open(source,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC)
        entries=_walk(fd)
    elif source.suffix.lower()=='.zip':
        fd=None;raw=_regular(source,MAX_ARCHIVE)
        archive_sha=hashlib.sha256(raw).hexdigest();(objects/archive_sha).write_bytes(raw)
        original_archive={'sha256':archive_sha,'size':len(raw),'object':'objects/'+archive_sha}
        entries=_archive(raw)
    else:
        fd=None;entries=iter([(source.name,_regular(source,MAX_FILE),{'kind':'single_file','relative_path':source.name})])
    artifacts=[];seen=set();total=0;extracted_total=0;segment_total=0
    try:
        for name,raw,origin in entries:
            identity=safe_name(name)
            if identity in seen:raise IntakeError('duplicate normalized path')
            seen.add(identity);total+=len(raw)
            if len(artifacts)>=MAX_FILES or total>MAX_TOTAL:raise IntakeError('project resource bound')
            sha=hashlib.sha256(raw).hexdigest();snapshot=objects/sha
            if snapshot.exists():
                if snapshot.read_bytes()!=raw:raise IntakeError('snapshot object collision/corruption')
            else:
                with snapshot.open('xb') as stream:stream.write(raw)
            record={'id':'artifact-'+digest([name,sha])[:24],'path':name,'sha256':sha,'size':len(raw),
                    'object':'objects/'+sha,'snapshot_path':str(snapshot),'origin':origin,
                    'training_policy':'DENIED_BY_DEFAULT','imported_code_executed':False}
            parsed=adapter_observation(name,snapshot)
            extracted_total+=len(canonical(parsed));segment_total+=len(parsed.get('segments',[]))
            if extracted_total>MAX_TOTAL or segment_total>50000:
                parsed={**parsed,'status':'ERROR','segments':[],'warnings':['PROJECT_EXTRACTION_RESOURCE_BOUND']}
            for segment in parsed.get('segments',[]):
                segment['artifact_id']=record['id'];segment['source_sha256']=sha
                segment['locator']['source_sha256']=sha
                segment['transformation']={'adapter':parsed['adapter'],'version':parsed['version'],'original_preserved':True}
            record.update(parsed);artifacts.append(record)
    finally:
        if fd is not None:os.close(fd)
    result={'format':'pcs-scientific-inventory-v1','artifacts':artifacts,'original_archive':original_archive,
            'total_bytes':total,'bounds':{'files':MAX_FILES,'file_bytes':MAX_FILE,'project_bytes':MAX_TOTAL,'extracted_bytes':MAX_TOTAL,'segments':50000},
            'inventory_sha256':digest([{k:r[k] for k in ('id','path','sha256','size','object','origin')} for r in artifacts]),
            'training_policy':'DENIED_BY_DEFAULT','authority':'NONE'}
    (output/'inventory.json').write_bytes(canonical(result)+b'\n')
    return result
