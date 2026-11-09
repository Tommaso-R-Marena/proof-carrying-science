"""Bound extracted PDF/DOCX text to original snapshots without false byte spans."""
from __future__ import annotations
from copy import deepcopy
import hashlib

from .semantics import interpret_artifacts
from research.scientific_intake_v1.intake import canonical


def digest(value):return hashlib.sha256(canonical(value)).hexdigest()


def augment(meaning,inventory):
    """Interpret bounded existing adapter segments; originals remain originals.

    Parent intake replay independently re-extracts these segments. A derived
    quotation's byte offsets refer to extracted text, never the original PDF.
    """
    result=deepcopy(meaning);virtual={};bindings={};total=0
    artifact_ids={(a['path'],a['sha256']):a['id'] for a in meaning['artifacts']}
    for artifact in inventory['artifacts']:
        if artifact.get('adapter') not in {'pdf','docx'} or artifact.get('status')!='EXTRACTED':continue
        for index,segment in enumerate(artifact.get('segments',[])):
            text=segment.get('text','');raw=text.encode('utf-8')
            if not raw or len(raw)>100000 or len(virtual)>=200 or total+len(raw)>1000000:continue
            name='extracted-'+digest([artifact['path'],artifact['sha256'],index])[:24]+'.txt'
            virtual[name]=raw;total+=len(raw)
            bindings[name]=(artifact,index,segment,hashlib.sha256(raw).hexdigest())
    if not virtual:return result
    derived=interpret_artifacts(virtual);ids={}
    def transform(value):
        if isinstance(value,list):return [transform(v) for v in value]
        if not isinstance(value,dict):return value
        value={k:transform(v) for k,v in value.items()}
        if value.get('path') in bindings and 'quote' in value and 'sha256' in value:
            a,index,segment,sha=bindings[value['path']]
            begin,end=value.pop('byte_start',None),value.pop('byte_end',None)
            value.update(path=a['path'],sha256=a['sha256'],artifact_id=artifact_ids[(a['path'],a['sha256'])],
                transformation={'kind':'adapter_extracted_text','adapter':a['adapter'],'version':a['version'],
                    'segment_index':index,'segment_sha256':sha,'extracted_byte_start':begin,'extracted_byte_end':end,
                    'locator':segment.get('locator',{}),'original_bytes_preserved':True})
        return value
    categories=['claims','symbols','dependencies','obligations','unresolved']
    for category in categories:
        for old in derived.get(category,[]):
            new=transform(old);oldid=new.get('id')
            if oldid:
                new['origin_id']=oldid;new['id']='derived-'+digest([category,new])[:24];ids[oldid]=new['id']
            result[category].append(new)
    def remap(v):
        if isinstance(v,str):return ids.get(v,v)
        if isinstance(v,list):return [remap(x) for x in v]
        if isinstance(v,dict):return {k:(x if k in {'id','origin_id'} else remap(x)) for k,x in v.items()}
        return v
    for category in categories:result[category]=[remap(v) for v in result[category]]
    result['document_extraction']={'virtual_segments':len(virtual),'extracted_bytes':total,'scope':'Bounded interpretation of adapter text, not OCR or original PDF byte quotations'}
    result['summary']={key:len(result[key]) for key in ['artifacts','claims','symbols','dependencies','obligations','unresolved']}
    return result
