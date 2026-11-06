"""Fixed parser worker. No source imports, shell execution or training from data."""
import json
from pathlib import Path
import resource
import sys


def main():
    resource.setrlimit(resource.RLIMIT_AS,(768*1024*1024,768*1024*1024))
    resource.setrlimit(resource.RLIMIT_CPU,(10,10))
    resource.setrlimit(resource.RLIMIT_FSIZE,(16*1024*1024,16*1024*1024))
    from .adapters import extract
    name,=sys.argv[1:]
    raw=sys.stdin.buffer.read(5*1024*1024+1)
    if len(raw)>5*1024*1024:raise ValueError('input limit')
    result=extract(name,raw)
    encoded=json.dumps(result,sort_keys=True,separators=(',',':'),allow_nan=False)
    if len(encoded.encode())>16*1024*1024:raise ValueError('output limit')
    print(encoded)
if __name__=='__main__':main()
