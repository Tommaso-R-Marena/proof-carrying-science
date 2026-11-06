"""Fixed, bounded computation worker. Imported source remains data."""
import json
import resource
import sys
from .checks import execute


def main():
    resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,2*1024**3))
    resource.setrlimit(resource.RLIMIT_CPU,(25,25))
    resource.setrlimit(resource.RLIMIT_FSIZE,(16*1024**2,16*1024**2))
    raw=sys.stdin.buffer.read(16*1024**2+1)
    if len(raw)>16*1024**2:raise ValueError('worker input bound')
    from pcs.jsonio import strict_json_loads
    request=strict_json_loads(raw.decode())
    result=execute(request['obligation'],request['artifacts'])
    encoded=json.dumps(result,sort_keys=True,allow_nan=False)
    if len(encoded)>16*1024**2:raise ValueError('worker output bound')
    print(encoded)
if __name__=='__main__':main()
