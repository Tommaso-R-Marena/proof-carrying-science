"""Staged research workflow and cache-independent evidence replay."""
from __future__ import annotations
import copy
import hashlib
import html
import json
from pathlib import Path
import time

from pcs.jsonio import strict_json_loads
from .intake import ingest, canonical, digest, adapter_observation, _regular, MAX_FILE, MAX_TOTAL, MAX_ARCHIVE, safe_name, _archive
from .knowledge import build_graph
from .checks import execute, bound_bytes
from .cache import CheckCache,checker_context
from .routing import plan


def _write(path,value):Path(path).write_bytes(canonical(value)+b'\n')

def stable_result(result):
    value=copy.deepcopy(result);value.pop('seconds',None)
    return value


def _public_inventory(inventory):
    result=copy.deepcopy(inventory)
    for artifact in result['artifacts']:artifact.pop('snapshot_path',None)
    return result


def render_review(graph,results,check):
    artifacts={a['id']:a for a in graph['artifacts']}
    counts={name:sum(r['status']==name for r in results) for name in ('VERIFIED_SUPPORTED','REFUTED','UNKNOWN','UNSUPPORTED')}
    checked = {next(o['claim_id'] for o in graph['obligations'] if o['id']==r['obligation_id']):r for r in results}
    descriptions = {'VERIFIED_SUPPORTED':'Supported check passed', 'REFUTED':'The files contradict this statement',
                    'UNKNOWN':'Check could not establish this statement', 'UNSUPPORTED':'Needs a different kind of evidence'}
    rows=[]
    for claim in graph['claims']:
        source_artifact=artifacts[claim['source']['artifact_id']]
        result=checked.get(claim['id'])
        status=descriptions.get(result['status'],'Not checked') if result else 'Needs review' if claim['kind']=='unsupported' else 'Not checked'
        location=html.escape(json.dumps(claim['source']['locator'],ensure_ascii=False,sort_keys=True))
        link='<a href="'+source_artifact['object']+'">'+html.escape(source_artifact['path'])+'</a>'
        assumptions=next(a['statements'] for a in graph['assumptions'] if a['claim_id']==claim['id'])
        rows.append('<tr><td>'+html.escape(claim['statement'])+'<details><summary>Source and assumptions</summary>'+link+'<p>'+location+'</p><p>'+html.escape(' '.join(assumptions))+'</p></details></td><td>'+status+'<p>Scientific meaning still needs review.</p></td></tr>')
    file_rows=''.join('<tr><td><a href="'+a['object']+'">'+html.escape(a['path'])+'</a></td><td>'+html.escape(a['adapter'])+'</td><td>'+html.escape(a['status'])+'</td></tr>' for a in artifacts.values())
    introduction=('PCS organized your files and ran the supported checks you authorized.' if check else 'PCS organized your files and proposed statements to review. No checks have run yet.')
    page='<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>PCS project review</title><style>body{font:18px system-ui;max-width:70rem;margin:3rem auto;padding:1rem;line-height:1.5}td,th{padding:.6rem;text-align:left;vertical-align:top;border-bottom:1px solid #ccc}table{width:100%;overflow-wrap:anywhere}summary{cursor:pointer}</style><h1>Your project review</h1><p>'+introduction+' These checks do not establish that a scientific conclusion is true. Your files have not been used for model training.</p><p>'+str(len(artifacts))+' files; '+str(counts['VERIFIED_SUPPORTED'])+' supported checks passed; '+str(counts['REFUTED'])+' statements contradicted by the files.</p><p>Start with contradicted statements, then review each proposed meaning and assumption. Original files and machine-readable evidence are included.</p><h2>Statements to review</h2><table><tr><th>Proposed statement</th><th>Result</th></tr>'+''.join(rows)+'</table><h2>Original files</h2><table><tr><th>File</th><th>Reader</th><th>Extraction status</th></tr>'+file_rows+'</table></html>'
    return page


def run(source,output,*,check=False,cache_dir=None,mode='deterministic',budget=100.):
    started=time.monotonic();output=Path(output).absolute()
    inventory=ingest(source,output)
    artifacts={a['id']:a for a in inventory['artifacts']}
    if cache_dir and (Path(cache_dir).resolve().is_relative_to(Path(source).resolve()) or Path(cache_dir).resolve().is_relative_to(output.resolve())):raise ValueError('cache must be outside imported source and evidence package')
    graph=build_graph(inventory['artifacts']);route=plan(graph['obligations'],inventory['artifacts'],mode=mode,budget=budget)
    context=checker_context();cache=CheckCache(cache_dir,context) if cache_dir else None
    results=[];hits=calls=0
    if check:
        obligations={o['id']:o for o in graph['obligations']}
        for step in route['steps']:
            obligation=obligations[step['obligation_id']]
            try:result=cache.get(obligation,artifacts) if cache else None
            except (OSError,ValueError,KeyError):result=None
            hit=result is not None
            if hit:hits+=1
            else:
                calls+=1;result=execute(obligation,artifacts)
                if cache:
                    try:cache.put(obligation,result,artifacts)
                    except (OSError,ValueError):pass
            results.append({**result,'cache_hit':hit})
    counts={name:sum(r['status']==name for r in results) for name in ('VERIFIED_SUPPORTED','REFUTED','UNKNOWN','UNSUPPORTED')}
    summary={'format':'pcs-scientific-summary-v1','artifact_count':len(artifacts),'parsed':sum(a['status']=='EXTRACTED' for a in artifacts.values()),
             'parse_errors':sum(a['status']=='ERROR' for a in artifacts.values()),'claims':len(graph['claims']),'obligations':len(graph['obligations']),
             'check_authorized':check,'checks':counts,'checker_calls':calls,'cache_hits':hits,'deferred':len(route['deferred']),
             'graph_truncated':graph['truncated'],'seconds':time.monotonic()-started,
             'scientific_claims_certified':0,'training_examples_admitted':0,'authority':'NONE',
             'next_actions':['Review proposed meanings and assumptions.','Investigate refuted claims.','Supply independent evidence for unsupported scientific statements.']}
    # Export portable locations only. Local absolute snapshot paths are not part
    # of the evidence contract and are reconstructed beneath the package root.
    public=_public_inventory(inventory);_write(output/'inventory.json',public)
    public_graph=copy.deepcopy(graph)
    for a in public_graph['artifacts']:a.pop('snapshot_path',None)
    _write(output/'graph.json',public_graph);_write(output/'routing.json',route)
    _write(output/'checks.json',results);_write(output/'context.json',context);_write(output/'summary.json',summary)
    page=render_review(graph,results,check)
    (output/'review.html').write_text(page)
    names=['inventory.json','graph.json','routing.json','checks.json','context.json','summary.json','review.html']
    names+=['objects/'+p.name for p in sorted((output/'objects').iterdir())]
    manifest={'format':'pcs-scientific-package-v1','files':{name:hashlib.sha256((output/name).read_bytes()).hexdigest() for name in names},
              'authority':'NONE','integrity_scope':'Self-contained hashes detect changes relative to a trusted manifest; no external signature or origin authenticity is claimed.'}
    _write(output/'manifest.json',manifest)
    return summary


def replay(directory,*,recheck=True,expected_manifest_sha256=None):
    """Rebuild interpretations and run actual checks, ignoring cached verdicts."""
    directory=Path(directory).absolute()
    manifest_raw=_regular(directory/'manifest.json',2*1024*1024)
    manifest_sha=hashlib.sha256(manifest_raw).hexdigest()
    if expected_manifest_sha256 is not None and manifest_sha!=expected_manifest_sha256:raise ValueError('externally pinned manifest mismatch')
    manifest=strict_json_loads(manifest_raw.decode())
    required={'inventory.json','graph.json','routing.json','checks.json','context.json','summary.json','review.html'}
    if manifest.get('format')!='pcs-scientific-package-v1' or not required<=manifest['files'].keys() or len(manifest['files'])>300:raise ValueError('invalid manifest')
    package_bytes={};package_total=0
    for name,sha in manifest['files'].items():
        safe_name(name)
        if name not in required and not __import__('re').fullmatch(r'objects/[0-9a-f]{64}',name):raise ValueError('unexpected package path')
        # Reject symlink ancestors as well as final files.
        if any(p.is_symlink() for p in [directory,*(directory/name).parents] if p.is_relative_to(directory)):raise ValueError('symlink package parent')
        raw=_regular(directory/name,MAX_ARCHIVE if name.startswith('objects/') else 64*1024*1024)
        package_total+=len(raw)
        if package_total>256*1024*1024:raise ValueError('evidence package aggregate resource bound')
        if hashlib.sha256(raw).hexdigest()!=sha:raise ValueError('package byte integrity failed')
        if name.startswith('objects/') and name[8:]!=sha:raise ValueError('content-address object mismatch')
        package_bytes[name]=raw
    inventory=strict_json_loads(package_bytes['inventory.json'].decode());artifacts=[]
    if len(inventory['artifacts'])>256 or sum(a['size'] for a in inventory['artifacts'])>MAX_TOTAL:raise ValueError('inventory resource bound')
    if len({a['id'] for a in inventory['artifacts']})!=len(inventory['artifacts']):raise ValueError('duplicate artifact identity')
    if len({safe_name(a['path']) for a in inventory['artifacts']})!=len(inventory['artifacts']):raise ValueError('ambiguous artifact path')
    index_sha=digest([{k:a[k] for k in ('id','path','sha256','size','object','origin')} for a in inventory['artifacts']])
    if index_sha!=inventory['inventory_sha256']:raise ValueError('inventory index mismatch')
    archive=inventory['original_archive'];expected_objects={a['object'] for a in inventory['artifacts']}
    if archive:
        if archive['object']!='objects/'+archive['sha256'] or archive['object'] not in package_bytes:raise ValueError('preserved archive binding mismatch')
        archive_raw=package_bytes[archive['object']]
        if len(archive_raw)!=archive['size']:raise ValueError('preserved archive size mismatch')
        entries=list(_archive(archive_raw))
        originals={name:(hashlib.sha256(raw).hexdigest(),len(raw),origin) for name,raw,origin in entries}
        recorded={a['path']:(a['sha256'],a['size'],a['origin']) for a in inventory['artifacts']}
        if originals!=recorded:raise ValueError('archive member provenance replay mismatch')
        expected_objects.add(archive['object'])
    elif any(a['origin'].get('kind')=='zip_member' for a in inventory['artifacts']):raise ValueError('missing preserved original archive')
    if expected_objects!={name for name in package_bytes if name.startswith('objects/')}:raise ValueError('orphan or missing source object')
    for a in inventory['artifacts']:
        if a['object']!='objects/'+a['sha256'] or a['object'] not in manifest['files']:raise ValueError('invalid object binding')
        if a['id']!='artifact-'+digest([a['path'],a['sha256']])[:24]:raise ValueError('artifact identity mismatch')
        artifact={**a,'snapshot_path':str(directory/a['object'])};bound_bytes(artifact)
        parsed=adapter_observation(a['path'],artifact['snapshot_path'])
        for s in parsed.get('segments',[]):
            s.update(artifact_id=a['id'],source_sha256=a['sha256'],transformation={'adapter':parsed['adapter'],'version':parsed['version'],'original_preserved':True})
            s['locator']['source_sha256']=a['sha256']
        bound_bytes(artifact)
        if parsed!={k:a[k] for k in parsed}:raise ValueError('extraction replay mismatch')
        artifacts.append(artifact)
    rebuilt=build_graph(artifacts)
    for a in rebuilt['artifacts']:a.pop('snapshot_path',None)
    graph=strict_json_loads(package_bytes['graph.json'].decode())
    if rebuilt!=graph:raise ValueError('knowledge graph replay mismatch')
    context=strict_json_loads(package_bytes['context.json'].decode())
    if context!=checker_context():raise ValueError('checker source or toolchain context changed')
    old=strict_json_loads(package_bytes['checks.json'].decode());by_id={a['id']:a for a in artifacts};obligations={o['id']:o for o in graph['obligations']}
    route=strict_json_loads(package_bytes['routing.json'].decode())
    expected_route=plan(graph['obligations'],graph['artifacts'],mode=route['requested_mode'],budget=route['budget'])
    if route!=expected_route:raise ValueError('routing replay mismatch')
    summary=strict_json_loads(package_bytes['summary.json'].decode())
    if type(summary.get('check_authorized')) is not bool:raise ValueError('invalid authorization record')
    if any(type(r.get('cache_hit')) is not bool for r in old):raise ValueError('invalid cache observation')
    counts={name:sum(r['status']==name for r in old) for name in ('VERIFIED_SUPPORTED','REFUTED','UNKNOWN','UNSUPPORTED')}
    expected_summary={'artifact_count':len(artifacts),'parsed':sum(a['status']=='EXTRACTED' for a in artifacts),
        'parse_errors':sum(a['status']=='ERROR' for a in artifacts),'claims':len(graph['claims']),
        'obligations':len(graph['obligations']),'checks':counts,'deferred':len(route['deferred']),
        'graph_truncated':graph['truncated'],'checker_calls':sum(not r['cache_hit'] for r in old),
        'cache_hits':sum(r['cache_hit'] for r in old),'scientific_claims_certified':0,'training_examples_admitted':0,'authority':'NONE'}
    if any(summary.get(k)!=v for k,v in expected_summary.items()):raise ValueError('summary replay mismatch')
    if package_bytes['review.html'].decode()!=render_review(graph,old,summary['check_authorized']):raise ValueError('display replay mismatch')
    seen=set();calls=0
    for expected in old:
        oid=expected['obligation_id']
        if oid in seen or oid not in obligations:raise ValueError('duplicate or unknown checked obligation')
        seen.add(oid)
        if recheck:
            actual=execute(obligations[oid],by_id);calls+=1
            clean=stable_result(expected);clean.pop('cache_hit',None)
            if stable_result(actual)!=clean:raise ValueError('independent check replay mismatch: '+oid)
    if (summary['check_authorized'] and seen!={s['obligation_id'] for s in route['steps']}) or (not summary['check_authorized'] and seen):raise ValueError('missing or unauthorized executed route step')
    return {'format':'pcs-scientific-replay-v1','artifacts':len(artifacts),'claims':len(graph['claims']),
            'replayed_checks':calls,'cache_used':False,'scientific_meaning':'OPEN','authority':False,
            'manifest_sha256':manifest_sha,'origin_attested':False,
            'status':('REPLAYED' if calls else 'NO_SUPPORTED_CHECKS_REPLAYED') if recheck else 'INTEGRITY_ONLY'}
