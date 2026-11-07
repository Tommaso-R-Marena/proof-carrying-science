"""Fixed research worker; no user-selected executables, callbacks or checkers."""
from __future__ import annotations

import base64
import resource
import sys

from pcs.jsonio import strict_json_loads
from research.scientific_intake_v1.intake import canonical, safe_name


def main():
    resource.setrlimit(resource.RLIMIT_AS,(1536*1024**2,1536*1024**2))
    resource.setrlimit(resource.RLIMIT_CPU,(30,30))
    resource.setrlimit(resource.RLIMIT_FSIZE,(16*1024**2,16*1024**2))
    resource.setrlimit(resource.RLIMIT_NOFILE,(128,128))
    data=sys.stdin.buffer.read(24*1024**2+1)
    if len(data)>24*1024**2:raise ValueError("worker input bound")
    request=strict_json_loads(data.decode())
    if set(request)!={"artifacts","check"} or type(request["check"]) is not bool or type(request["artifacts"]) is not dict:
        raise ValueError("invalid worker request")
    artifacts={};total=0
    if len(request["artifacts"])>256:raise ValueError("worker file count")
    for name,value in request["artifacts"].items():
        safe_name(name)
        if not isinstance(value,str):raise ValueError("worker byte encoding")
        raw=base64.b64decode(value,validate=True);total+=len(raw)
        if len(raw)>1_000_000 or total>16_000_000:raise ValueError("worker byte bound")
        artifacts[name]=raw
    from .pipeline import interpret_snapshots
    from .checks import execute
    semantics=interpret_snapshots(artifacts)
    result={"semantics":semantics,"checks":execute(semantics,artifacts) if request["check"] else []}
    encoded=canonical(result)
    if len(encoded)>32*1024**2:raise ValueError("worker output bound")
    sys.stdout.buffer.write(encoded)


if __name__=="__main__":main()
