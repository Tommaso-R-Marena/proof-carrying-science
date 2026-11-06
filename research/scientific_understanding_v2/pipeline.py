"""Additive scientific review using PR201 byte intake, graph, cache and replay."""
from __future__ import annotations
import copy
import hashlib
import html
import json
from pathlib import Path
import time

from pcs.jsonio import strict_json_loads
from research.scientific_intake_v1.pipeline import run as intake_run,replay as intake_replay
from research.scientific_intake_v1.intake import canonical,digest,_regular
from research.scientific_intake_v1.checks import bound_bytes
from research.scientific_intake_v1.cache import CheckCache,checker_context
from .interpretation import interpret
from .checks import obligations,execute_bounded


def context():
    here=Path(__file__).parent
    import sys,importlib.metadata
    versions={}
    for name in ['numpy','scipy']:
        try:versions[name]=importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:versions[name]='UNAVAILABLE'
    return {'parent':checker_context(),'sources':{p.relative_to(here).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(here.rglob('*')) if p.is_file() and (p.parent==here and p.suffix=='.py' and not p.name.startswith('test_') or p.parent==here/'formal' and p.suffix=='.lean')},
            'learning_sources':{p.relative_to(here).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((here/'learning').rglob('*.py'))},
            'retrieval_checkpoint_sha256':hashlib.sha256((here/'learning/artifacts/scientific_encoder.json').read_bytes()).hexdigest(),
            'libraries':versions,'authority':'research-only;scientific-meaning-open'}


def _write(path,v):Path(path).write_bytes(canonical(v)+b'\n')


def portable_inventory(folder):
    inventory=strict_json_loads((Path(folder)/'inventory.json').read_text())
    for a in inventory['artifacts']:a['snapshot_path']=str(Path(folder)/a['object'])
    return inventory


def stable(value):
    if isinstance(value,dict):return {k:stable(v) for k,v in value.items() if k not in {'seconds','cache_hit'}}
    if isinstance(value,list):return [stable(v) for v in value]
    return value


def summary_for(interps,checks,authorized):
    statuses={s:sum(c['status']==s for c in checks) for s in ['VERIFIED_SUPPORTED','REFUTED','UNKNOWN']}
    return {'format':'pcs-scientific-review-v2','authorized_checks':authorized,'claims':len(interps['claims']),
            'equations':len(interps['equations']),'quantities':len(interps['quantities']),'unresolved':len(interps['unresolved']),
            'checks':statuses,'scientific_claims_certified':0,'authority':False,'training_examples_admitted':0,
            'next_actions':['Inspect the source beside each proposed statement.','Resolve missing units and assumptions.','Review numerical discrepancies before relying on a finding.']}


def review_html(interps,checks,inventory,summary):
    arts={a['id']:a for a in inventory['artifacts']};by_item={}
    for check in checks:
        if check.get('interpretation_id'):by_item.setdefault(check['interpretation_id'],[]).append(check)
    rows=[]
    names={'VERIFIED_SUPPORTED':'Supported check passed','REFUTED':'Contradicted by a check','UNKNOWN':'Not established'}
    for c in interps['claims']:
        source=c['source'];a=arts[source['artifact_id']];results=by_item.get(c.get('interpretation_id'),[])
        status='; '.join(sorted({names[x['status']] for x in results})) or 'Scientific judgment needed'
        rows.append('<article><h3>'+html.escape(c.get('kind','Proposed statement'))+'</h3><p>'+html.escape(c.get('statement',''))+'</p><p><strong>'+status+'</strong>. Meaning still needs review.</p><details><summary>Show source</summary><a href="intake/'+a['object']+'">'+html.escape(a['path'])+'</a><pre>'+html.escape(source.get('quote','')[:4000])+'</pre></details></article>')
    special=[]
    for c in checks:
        if c['checker'] in {'model_assurance','document_reproduction'}:
            special.append('<article><h3>'+html.escape(c['checker'].replace('_',' '))+'</h3><p>'+names[c['status']]+'</p><details><summary>Inspect measured evidence and limits</summary><pre>'+html.escape(json.dumps(c['evidence'],indent=2,sort_keys=True))+'</pre></details></article>')
    return '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>PCS scientific review</title><style>body{font:18px system-ui;max-width:65rem;margin:2rem auto;padding:1rem;line-height:1.5}article{border:1px solid #bbb;padding:1rem;margin:1rem 0;border-radius:.5rem}pre{white-space:pre-wrap;overflow-wrap:anywhere}summary{cursor:pointer}</style><h1>What can these files establish?</h1><p>PCS read the project and proposed scientific statements. '+('You authorized the supported checks.' if summary['authorized_checks'] else 'No checks have run yet.')+' A passing check supports its stated mathematical or computational scope. It does not establish biological validity or settle a paper’s meaning.</p><p>'+str(summary['checks']['VERIFIED_SUPPORTED'])+' supported checks passed; '+str(summary['checks']['REFUTED'])+' contradicted; '+str(summary['checks']['UNKNOWN'])+' not established. Your files were not used for training.</p><h2>Computational results</h2>'+''.join(special)+'<h2>Proposed statements and sources</h2>'+''.join(rows)+'</html>'


def graph_for(interps,obs,inventory):
    nodes=[];edges=[]
    for a in inventory['artifacts']:nodes.append({'id':a['id'],'kind':'artifact','sha256':a['sha256'],'path':a['path']})
    for category in ['claims','equations','quantities','tables','assumptions','unresolved']:
        for item in interps[category]:
            nodes.append({'id':item['id'],'kind':category,'authority':False})
            edges.append({'from':item['source']['artifact_id'],'to':item['id'],'relation':'exact_source_binding','sha256':item['source']['sha256']})
            if category=='claims':
                review='meaning-review-'+item['id'];nodes.append({'id':review,'kind':'scientific_meaning_obligation','status':'OPEN','authority':False})
                edges.append({'from':item['id'],'to':review,'relation':'requires','blocking':True})
                if item.get('interpretation_id'):edges.append({'from':item['id'],'to':item['interpretation_id'],'relation':'proposed_interpretation'})
    for o in obs:
        nodes.append({'id':o['id'],'kind':'check_obligation','checker':o['checker'],'authority':False})
        for a in o['artifact_ids']:edges.append({'from':a,'to':o['id'],'relation':'dependency'})
        if o['payload'].get('item'):edges.append({'from':o['payload']['item']['id'],'to':o['id'],'relation':'independent_check'})
    return {'format':'pcs-scientific-knowledge-sidecar-v2','nodes':nodes,'edges':edges,'authority':False,
            'production_claim_ir':'The unchanged intake/graph.json retains existing PCS Claim IR and obligations; these additional meanings remain experimental sidecars.'}


def run(source,output,*,check=False,cache_dir=None):
    output=Path(output).absolute()
    if output.exists():raise ValueError('refuse evidence overwrite')
    if cache_dir and (Path(cache_dir).resolve().is_relative_to(Path(source).resolve()) or Path(cache_dir).resolve().is_relative_to(output)):raise ValueError('cache must be host-owned outside input and evidence')
    output.mkdir(parents=True,mode=0o700)
    intake_run(source,output/'intake',check=False)
    inv=portable_inventory(output/'intake');by_id={a['id']:a for a in inv['artifacts']}
    interps=interpret(inv);obs=obligations(interps,inv);ctx=context();cache=CheckCache(cache_dir,ctx) if cache_dir else None
    checks=[]
    if check:
        for o in obs:
            result=cache.get(o,by_id) if cache else None;hit=result is not None
            if not hit:
                result=execute_bounded(o,by_id)
                if cache:cache.put(o,result,by_id)
            result=copy.deepcopy(result);result['cache_hit']=hit
            if 'item' in o['payload']:result['interpretation_id']=o['payload']['item']['id']
            checks.append(result)
    summary=summary_for(interps,checks,check)
    for name,value in [('interpretations',interps),('obligations',obs),('checks',checks),('summary',summary),('context',ctx),('graph',graph_for(interps,obs,inv))]:_write(output/(name+'.json'),value)
    (output/'review.html').write_text(review_html(interps,checks,inv,summary))
    files={p.relative_to(output).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(output.rglob('*')) if p.is_file()}
    _write(output/'manifest.json',{'format':'pcs-scientific-understanding-package-v2','files':files,'authority':False})
    return summary


def replay(directory,*,recheck=True,expected_manifest_sha256=None):
    directory=Path(directory).absolute();raw=_regular(directory/'manifest.json',2*1024**2)
    if expected_manifest_sha256 is not None and hashlib.sha256(raw).hexdigest()!=expected_manifest_sha256:raise ValueError('pinned manifest changed')
    manifest=strict_json_loads(raw.decode());required={'interpretations.json','obligations.json','checks.json','summary.json','context.json','graph.json','review.html'}
    if manifest['format']!='pcs-scientific-understanding-package-v2' or not required<=manifest['files'].keys() or len(manifest['files'])>320:raise ValueError('invalid manifest')
    blobs={};total=0
    from research.scientific_intake_v1.intake import safe_name
    for name,sha in manifest['files'].items():
        safe_name(name)
        if name not in required and not name.startswith('intake/'):raise ValueError('unknown package member')
        if any(p.is_symlink() for p in [directory/name,*(directory/name).parents] if p.is_relative_to(directory)):raise ValueError('symlink package path')
        data=_regular(directory/name,64*1024**2);total+=len(data)
        if total>256*1024**2:raise ValueError('package aggregate resource bound')
        if hashlib.sha256(data).hexdigest()!=sha:raise ValueError('evidence member changed')
        blobs[name]=data
    intake_replay(directory/'intake',recheck=False,expected_manifest_sha256=manifest['files']['intake/manifest.json'])
    nested=strict_json_loads(blobs['intake/manifest.json'].decode())
    if {n for n in blobs if n.startswith('intake/')}!={'intake/'+n for n in nested['files']}|{'intake/manifest.json'}:raise ValueError('unreferenced intake member')
    ctx=strict_json_loads(blobs['context.json'].decode())
    if ctx!=context():raise ValueError('runtime/source context changed')
    inv=portable_inventory(directory/'intake');interps=interpret(inv);obs=obligations(interps,inv)
    if interps!=strict_json_loads(blobs['interpretations.json'].decode()) or obs!=strict_json_loads(blobs['obligations.json'].decode()):raise ValueError('interpretation or obligation replay mismatch')
    if graph_for(interps,obs,inv)!=strict_json_loads(blobs['graph.json'].decode()):raise ValueError('knowledge graph replay mismatch')
    checks=strict_json_loads(blobs['checks.json'].decode());summary=strict_json_loads(blobs['summary.json'].decode())
    if type(summary['authorized_checks']) is not bool or summary!=summary_for(interps,checks,summary['authorized_checks']):raise ValueError('summary replay mismatch')
    if blobs['review.html'].decode()!=review_html(interps,checks,inv,summary):raise ValueError('display replay mismatch')
    ids=[r['obligation_id'] for r in checks]
    if summary['authorized_checks'] and set(ids)!={o['id'] for o in obs} or not summary['authorized_checks'] and ids or len(ids)!=len(set(ids)):raise ValueError('missing or duplicate checks')
    by_id={a['id']:a for a in inv['artifacts']};by_ob={o['id']:o for o in obs}
    if recheck:
        for old in checks:
            actual=execute_bounded(by_ob[old['obligation_id']],by_id)
            if 'interpretation_id' in old:actual['interpretation_id']=by_ob[old['obligation_id']]['payload']['item']['id']
            if stable(old)!=stable(actual):raise ValueError('independent scientific check mismatch: '+old['obligation_id'])
    return {'status':'REPLAYED' if recheck and checks else 'INTEGRITY_ONLY','replayed_checks':len(checks) if recheck else 0,'cache_used':False,
            'authority':False,'scientific_meaning':'OPEN','manifest_sha256':hashlib.sha256(raw).hexdigest()}
