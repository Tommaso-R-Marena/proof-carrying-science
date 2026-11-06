from pathlib import Path
import copy
import hashlib
import json
import os
import shutil
import subprocess
import sys

import pytest
from .intake import ingest,canonical,digest
from .knowledge import build_graph
from .checks import execute
from .pipeline import run,replay
from .cache import CheckCache


def project(tmp_path):
    p=tmp_path/'input';p.mkdir();(p/'data.csv').write_text('value,unit\n1,mg\n2,mg\n3,mg\n')
    (p/'claims.md').write_text('PCS-CLAIM: rows(data.csv)=3\nPCS-CLAIM: mean(data.csv,value)=2\nPCS-CLAIM: sum(data.csv,value)=7\nTreatment causes a cure.\n')
    (p/'code.py').write_text('import csv\nraise RuntimeError("NEVER RUN")\n')
    return p


def test_end_to_end_real_checks_and_replay(tmp_path):
    p=project(tmp_path);out=tmp_path/'evidence';summary=run(p,out,check=True)
    assert summary['checks']['REFUTED']==1
    assert summary['checks']['VERIFIED_SUPPORTED']>=4
    assert summary['scientific_claims_certified']==summary['training_examples_admitted']==0
    assert replay(out)['replayed_checks']==summary['checker_calls']
    assert 'Your project review' in (out/'review.html').read_text()
    graph=json.loads((out/'graph.json').read_text())
    assert graph['pcs_claim_ir']['claims']
    assert all(c['meaning_status']=='NEEDS_REVIEW' and c['authority'] is False for c in graph['claims'])


def test_no_check_default(tmp_path):
    summary=run(project(tmp_path),tmp_path/'evidence')
    assert summary['checker_calls']==0 and not summary['check_authorized']


def test_cache_authentication_and_selective_invalidation(tmp_path):
    p=project(tmp_path);cache=tmp_path/'cache'
    first=run(p,tmp_path/'first',check=True,cache_dir=cache)
    second=run(p,tmp_path/'second',check=True,cache_dir=cache)
    assert second['checker_calls']==0 and second['cache_hits']==first['checker_calls']
    (p/'unrelated.txt').write_text('No claim in this file.')
    third=run(p,tmp_path/'third',check=True,cache_dir=cache)
    assert third['checker_calls']==0
    (p/'data.csv').write_text('value,unit\n1,mg\n2,mg\n4,mg\n')
    fourth=run(p,tmp_path/'fourth',check=True,cache_dir=cache)
    assert fourth['checker_calls']>0 and fourth['cache_hits']>0
    assert replay(tmp_path/'fourth')['cache_used'] is False
    for entry in cache.glob('*.json'):
        envelope=json.loads(entry.read_text());envelope['payload']['result']['status']='VERIFIED_SUPPORTED'
        envelope['mac']=hashlib.sha256(canonical(envelope['payload'])).hexdigest()
        entry.write_bytes(canonical(envelope))
    fifth=run(p,tmp_path/'fifth',check=True,cache_dir=cache)
    assert fifth['cache_hits']==0


def test_cache_context_change(tmp_path):
    p=project(tmp_path);inventory=ingest(p,tmp_path/'e');arts={a['id']:a for a in inventory['artifacts']}
    o=next(o for o in build_graph(list(arts.values()))['obligations'] if o['checker']=='csv_rows')
    result=execute(o,arts);assert result['status']=='VERIFIED_SUPPORTED'
    a=CheckCache(tmp_path/'cache',{'version':1});a.put(o,result,arts)
    assert a.get(o,arts)
    b=CheckCache(tmp_path/'cache',{'version':2});assert b.get(o,arts) is None


def test_payload_substitution_rejected(tmp_path):
    p=project(tmp_path);inv=ingest(p,tmp_path/'e');arts={a['id']:a for a in inv['artifacts']}
    o=next(o for o in build_graph(inv['artifacts'])['obligations'] if o['checker']=='csv_rows')
    forged=copy.deepcopy(o);forged['payload']['expected']='999'
    assert execute(forged,arts)['status']=='UNKNOWN'
    original=arts[o['source_bindings'][0]['artifact_id']];Path(original['snapshot_path']).write_text('tampered')
    assert execute(o,arts)['status']=='UNKNOWN'


@pytest.mark.parametrize('name',['graph.json','checks.json','inventory.json','objects'])
def test_tampered_evidence_rejected(tmp_path,name):
    out=tmp_path/'e';run(project(tmp_path),out,check=True)
    target=next((out/'objects').iterdir()) if name=='objects' else out/name
    target.write_bytes(target.read_bytes()+b' ')
    with pytest.raises(ValueError):replay(out)


def test_resigned_forged_graph_still_rejected(tmp_path):
    out=tmp_path/'e';run(project(tmp_path),out,check=True)
    g=json.loads((out/'graph.json').read_text());g['claims'][0]['statement']='We invented evidence'
    (out/'graph.json').write_bytes(canonical(g))
    m=json.loads((out/'manifest.json').read_text());m['files']['graph.json']=hashlib.sha256((out/'graph.json').read_bytes()).hexdigest()
    (out/'manifest.json').write_bytes(canonical(m))
    with pytest.raises(ValueError,match='graph replay'):replay(out)


def test_html_injection_is_escaped(tmp_path):
    p=project(tmp_path);(p/'claims.md').write_text('<script>alert(1)</script> causes cure.\n')
    run(p,tmp_path/'e')
    page=(tmp_path/'e/review.html').read_text();assert '<script>' not in page and '&lt;script&gt;' in page


def test_claim_bound_explicit(tmp_path):
    p=project(tmp_path);(p/'claims.md').write_text('\n'.join(f'PCS-CLAIM: rows(data.csv)={i}' for i in range(300)))
    inv=ingest(p,tmp_path/'e');g=build_graph(inv['artifacts'])
    assert g['truncated'] and len(g['claims'])==256


@pytest.mark.skipif(shutil.which('lean') is None,reason='exact Lean required')
def test_real_closed_math_not_imported_proof(tmp_path):
    p=tmp_path/'input';p.mkdir()
    (p/'math.lean').write_text('theorem safe : ∀ (n : Nat), n + 0 = n := by\n  sorry\n#eval IO.println "DO NOT EXECUTE"\n')
    s=run(p,tmp_path/'e',check=True)
    assert s['checks']['VERIFIED_SUPPORTED']==1
    results=json.loads((tmp_path/'e/checks.json').read_text())
    receipt=results[0]['evidence']['receipt']
    assert 'sorryAx' not in receipt['kernel']['axioms']
    assert replay(tmp_path/'e')['replayed_checks']==1

@pytest.mark.skipif(shutil.which('lean') is None,reason='exact Lean required')
def test_exact_upstream_style_type_reconstructed_without_proof_execution(tmp_path):
    p=tmp_path/'input';p.mkdir()
    (p/'math.lean').write_text('@[simp] protected theorem zero_add : ∀ (n : Nat), 0 + n = n\n  | 0 => by sorry\n')
    s=run(p,tmp_path/'e',check=True)
    assert s['checks']['VERIFIED_SUPPORTED']==1
    graph=json.loads((tmp_path/'e/graph.json').read_text())
    assert graph['claims'][0]['statement']=='Declared theorem type: ∀ (n : Nat), 0 + n = n'

@pytest.mark.parametrize('attack',['drop_checks','inflate_summary','false_display','alter_budget'])
def test_resigned_consistent_envelope_cannot_forge_replay_claims(tmp_path,attack):
    out=tmp_path/'e';run(project(tmp_path),out,check=True)
    changed=[]
    if attack=='drop_checks':
        (out/'checks.json').write_bytes(canonical([]));changed.append('checks.json')
        route=json.loads((out/'routing.json').read_text());route['steps']=[]
        (out/'routing.json').write_bytes(canonical(route));changed.append('routing.json')
    elif attack=='inflate_summary':
        summary=json.loads((out/'summary.json').read_text());summary['checks']['VERIFIED_SUPPORTED']=999
        (out/'summary.json').write_bytes(canonical(summary));changed.append('summary.json')
    elif attack=='false_display':
        (out/'review.html').write_text('999 scientific claims certified');changed.append('review.html')
    else:
        route=json.loads((out/'routing.json').read_text());route['budget']=0
        (out/'routing.json').write_bytes(canonical(route));changed.append('routing.json')
    manifest=json.loads((out/'manifest.json').read_text())
    for name in changed:manifest['files'][name]=hashlib.sha256((out/name).read_bytes()).hexdigest()
    (out/'manifest.json').write_bytes(canonical(manifest))
    with pytest.raises(ValueError):replay(out)

def test_original_zip_and_every_member_replayed(tmp_path):
    import zipfile
    archive=tmp_path/'project.zip'
    with zipfile.ZipFile(archive,'w') as z:
        z.writestr('data.csv','x\n1\n2\n');z.writestr('claims.md','PCS-CLAIM: rows(data.csv)=2')
    out=tmp_path/'e';run(archive,out,check=True)
    manifest_digest=hashlib.sha256((out/'manifest.json').read_bytes()).hexdigest()
    assert replay(out,expected_manifest_sha256=manifest_digest)['status']=='REPLAYED'
    inv=json.loads((out/'inventory.json').read_text());obj=inv['original_archive']['object']
    (out/obj).write_bytes(b'not the preserved archive')
    m=json.loads((out/'manifest.json').read_text());m['files'][obj]=hashlib.sha256((out/obj).read_bytes()).hexdigest()
    (out/'manifest.json').write_bytes(canonical(m))
    with pytest.raises(ValueError):replay(out)
    with pytest.raises(ValueError,match='externally pinned'):replay(out,expected_manifest_sha256=manifest_digest)


def test_orphan_objects_not_accepted_as_evidence(tmp_path):
    out=tmp_path/'e';run(project(tmp_path),out,check=True)
    data=b'unsourced';sha=hashlib.sha256(data).hexdigest();name='objects/'+sha;(out/name).write_bytes(data)
    m=json.loads((out/'manifest.json').read_text());m['files'][name]=sha;(out/'manifest.json').write_bytes(canonical(m))
    with pytest.raises(ValueError,match='orphan'):replay(out)

@pytest.mark.skipif(shutil.which('lean') is None,reason='exact Lean required')
def test_list_mathematics_is_checked_through_existing_typed_interface(tmp_path):
    p=tmp_path/'input';p.mkdir()
    (p/'math.md').write_text('For all lists of natural numbers xs, xs appended to the empty list = xs.\nFor all lists of natural numbers xs, xs appended to the empty list = the empty list.\n')
    summary=run(p,tmp_path/'e',check=True)
    assert summary['checks']['VERIFIED_SUPPORTED']==1 and summary['checks']['UNKNOWN']==1
    assert replay(tmp_path/'e')['replayed_checks']==2

def test_biological_multi_field_source_locators_replay_canonically(tmp_path):
    p=tmp_path/'input';p.mkdir();(p/'seq.fasta').write_text('>a\nACDE\n')
    summary=run(p,tmp_path/'e',check=True)
    assert summary['checks']['VERIFIED_SUPPORTED']==1
    assert replay(tmp_path/'e')['replayed_checks']==1
