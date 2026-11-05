"""Bounded-buffer deterministic JSON/gzip recording; no neural dependency."""
import gzip,json,os,tempfile
from pathlib import Path

def write(p,value):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    # Stream bounded buffers instead of allocating the full JSON string, a
    # second UTF-8 copy and a compressed copy simultaneously.
    with tempfile.NamedTemporaryFile(dir=p.parent,delete=False) as stage:
        raw_path=Path(stage.name);buffer=[];size=0;buffer_size=0
        try:
            for part in json.JSONEncoder(sort_keys=True,indent=2).iterencode(value):
                buffer.append(part);buffer_size+=len(part)
                if buffer_size>=65536:
                    data=''.join(buffer).encode();stage.write(data);size+=len(data);buffer=[];buffer_size=0
            data=(''.join(buffer)+'\n').encode();stage.write(data);size+=len(data)
        except BaseException:raw_path.unlink(missing_ok=True);raise
    try:
        if size<=512000:os.replace(raw_path,p)
        else:
            compressed=p.with_suffix(p.suffix+'.gz')
            with tempfile.NamedTemporaryFile(dir=p.parent,delete=False) as target:
                target_path=Path(target.name)
                with gzip.GzipFile(filename='',fileobj=target,mode='wb',mtime=0) as stream,raw_path.open('rb') as source:
                    while chunk:=source.read(1048576):stream.write(chunk)
            os.replace(target_path,compressed)
    finally:raw_path.unlink(missing_ok=True)

