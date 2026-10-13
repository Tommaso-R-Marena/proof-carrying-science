"""Durable per-comparison evidence; publication does not confer authority."""
import gzip
import io
import hashlib
import json
import os
from pathlib import Path
import tempfile

MAX_BYTES=32*1024*1024

class EvidenceJournal:
    def __init__(self,folder):
        self.folder=Path(folder)
        self.folder.mkdir(parents=True,exist_ok=True)
        if self.folder.is_symlink():raise ValueError('journal symlink')

    def append(self,index,row):
        if type(index) is not int or not 0<=index<100000:raise ValueError('bounded journal index')
        target=self.folder/f'row-{index:05}.json.gz'
        if target.exists() or target.is_symlink():raise ValueError('immutable row already present')
        raw=json.dumps(row,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
        if len(raw)>MAX_BYTES:raise ValueError('bounded journal row')
        packed=gzip.compress(raw,mtime=0)
        fd,name=tempfile.mkstemp(prefix='.pending-',dir=self.folder)
        try:
            with os.fdopen(fd,'wb') as f:f.write(packed);f.flush();os.fsync(f.fileno())
            os.link(name,target)  # atomic no-clobber publication
            if hasattr(os, 'O_DIRECTORY'):
                directory_fd = os.open(self.folder, os.O_RDONLY | os.O_DIRECTORY)
                try: os.fsync(directory_fd)
                finally: os.close(directory_fd)
        finally:
            Path(name).unlink(missing_ok=True)
        return {'row':target.name,'sha256':hashlib.sha256(packed).hexdigest(),'raw_sha256':hashlib.sha256(raw).hexdigest()}

    def read(self,index,expected_sha256):
        if type(index) is not int or not 0<=index<100000:raise ValueError('bounded journal index')
        p=self.folder/f'row-{index:05}.json.gz'
        if p.is_symlink() or p.stat().st_size>MAX_BYTES:raise ValueError('unsafe journal row')
        data=p.read_bytes()
        if hashlib.sha256(data).hexdigest()!=expected_sha256:raise ValueError('journal digest mismatch')
        with gzip.GzipFile(fileobj=io.BytesIO(data)) as f:raw=f.read(MAX_BYTES+1)
        if len(raw)>MAX_BYTES:raise ValueError('journal expansion bound')
        return json.loads(raw)
