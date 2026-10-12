"""Self-contained lossless catalog interning for bounded public proof packets.

Repeated kernel premise arrays become references to their full canonical value.
The receiver checks every digest and bounds logical expansion. No proof, state,
assumption, action or provenance field is dropped. This grants no authority.
"""
from copy import deepcopy
from .induction_ir import digest

FORMAT='pcs-interned-public-lean-v1'
MAX_EXPANDED_BYTES=4_000_000

def intern(response):
    catalogs={}
    def visit(value):
        if type(value) is list:return [visit(v) for v in value]
        if type(value) is not dict:return value
        result={}
        for key,v in value.items():
            if key=='available_lemmas' and type(v) is list:
                identity=digest(v);catalogs[identity]=deepcopy(v);result[key]={'pcs_catalog_ref':identity}
            else:result[key]=visit(v)
        return result
    payload=visit(response)
    return {'format':FORMAT,'payload':payload,'catalogs':catalogs,'expanded_limit_bytes':MAX_EXPANDED_BYTES}

def expand(envelope):
    import json
    if set(envelope)!={'format','payload','catalogs','expanded_limit_bytes'} or envelope['format']!=FORMAT or envelope['expanded_limit_bytes']!=MAX_EXPANDED_BYTES:
        raise ValueError('unsupported interned packet')
    catalogs=envelope['catalogs']
    if type(catalogs) is not dict or len(catalogs)>8:raise ValueError('catalog bound')
    def check_catalog(value,depth=0):
        if depth>64:raise ValueError('packet nesting bound')
        if type(value) is dict:
            if 'pcs_catalog_ref' in value:raise ValueError('nested catalog reference')
            for child in value.values():check_catalog(child,depth+1)
        elif type(value) is list:
            for child in value:check_catalog(child,depth+1)
    for value in catalogs.values():check_catalog(value)
    if any(type(v) is not list or digest(v)!=key for key,v in catalogs.items()):raise ValueError('catalog digest mismatch')
    sizes={key:len(json.dumps(v,separators=(',',':'),ensure_ascii=False).encode()) for key,v in catalogs.items()}
    remaining=MAX_EXPANDED_BYTES
    def charge(n):
        nonlocal remaining
        remaining-=n
        if remaining<0:raise ValueError('expanded packet bound')
    def visit(value,depth=0):
        if depth>64:raise ValueError('packet nesting bound')
        if type(value) is list:
            charge(2+max(0,len(value)-1));return [visit(v,depth+1) for v in value]
        if type(value) is not dict:
            charge(len(json.dumps(value,ensure_ascii=False).encode()));return value
        if set(value)=={'pcs_catalog_ref'}:
            key=value['pcs_catalog_ref']
            if type(key) is not str or key not in catalogs:raise ValueError('missing catalog reference')
            charge(sizes[key])
            return deepcopy(catalogs[key])
        charge(2+max(0,len(value)-1)+sum(len(json.dumps(k,ensure_ascii=False).encode())+1 for k in value))
        return {k:visit(v,depth+1) for k,v in value.items()}
    result=visit(envelope['payload'])
    return result
