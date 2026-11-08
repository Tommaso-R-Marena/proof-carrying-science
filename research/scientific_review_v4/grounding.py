"""Exact raw-byte or explicitly transformed-source evidence validation."""
from __future__ import annotations
import hashlib
from research.scientific_semantics_v3.evaluation import bound_source as raw_bound


def source_key(source,artifacts):
    p=source.get('path')
    if p in artifacts:return p
    matches=[k for k in artifacts if isinstance(p,str) and p.endswith('/'+k)]
    if len(matches)!=1:raise KeyError('ambiguous source path')
    return matches[0]


def bound_source(source,artifacts,inventory=None):
    try:
        key=source_key(source,artifacts);raw=artifacts[key]
        if hashlib.sha256(raw).hexdigest()!=source['sha256']:return False
        normalized={**source,'path':key}
        if source.get('transformation',{}).get('kind')!='adapter_extracted_text':return raw_bound(normalized,artifacts)
        t=source['transformation']
        if t.get('kind')!='adapter_extracted_text' or inventory is None:return False
        records=[a for a in inventory['artifacts'] if a['path']==key and a['sha256']==source['sha256']]
        if len(records)!=1:return False
        artifact=records[0]
        if artifact['adapter']!=t['adapter'] or artifact['version']!=t['version']:return False
        i=t['segment_index']
        if type(i) is not int or i<0:return False
        segment=artifact['segments'][i];data=segment['text'].encode('utf-8')
        if hashlib.sha256(data).hexdigest()!=t['segment_sha256'] or segment['locator']!=t['locator']:return False
        a,b=t['extracted_byte_start'],t['extracted_byte_end']
        return type(a) is int and type(b) is int and 0<=a<b<=len(data) and data[a:b].decode('utf-8')==source['quote']
    except (KeyError,ValueError,TypeError,IndexError,UnicodeError):return False


def same_source(a,b,artifacts,inventory=None):
    if not bound_source(a,artifacts,inventory) or not bound_source(b,artifacts,inventory):return False
    if source_key(a,artifacts)!=source_key(b,artifacts) or a['sha256']!=b['sha256']:return False
    if a.get('transformation',{}).get('kind')=='adapter_extracted_text' or b.get('transformation',{}).get('kind')=='adapter_extracted_text':
        # A PDF quote cannot match a raw JATS quote merely by similar words.
        if a.get('transformation',{}).get('segment_sha256')!=b.get('transformation',{}).get('segment_sha256'):return False
        aa,bb=a['transformation'],b['transformation']
        if any(aa.get(k)!=bb.get(k) for k in ['adapter','version','segment_index','locator']):return False
        return max(aa['extracted_byte_start'],bb['extracted_byte_start'])<min(aa['extracted_byte_end'],bb['extracted_byte_end'])
    return max(a['byte_start'],b['byte_start'])<min(a['byte_end'],b['byte_end'])
