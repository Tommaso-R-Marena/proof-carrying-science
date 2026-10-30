"""Independent bounded old/new receiving differential; actual receiver-owned Lean.
Run from repository root with PYTHONPATH=. and PCS_LEAN_AUTHORITY_BIN set.
Temporary signed inputs are synthetic; no affirmative verifier is mocked.
"""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import types

from pcs.canonical_json import canonicalize_jcs_bytes
from pcs.canonical_zip_v06 import canonical_zip_bytes_v06
from pcs.intake import INTAKE_LOCK_PACKAGE_MEMBER_V06 as MEMBER, freeze_intake
from pcs.package_v06 import build_package_manifest_v06, sign_package_manifest_v06
from pcs.verifier_io_v06 import verify_package_directory_end_to_end_v06, write_verification_receipt_v06
from pcs.verifier_zip_v06 import load_package_zip_v06, verify_package_zip_end_to_end_v06

BASE = 'fabc704efdbda4c8822881366e4db3d3e31f066a'
HEAD = 'b916eec1b9d0d5c02c9cc19b070f7a47df5e5d87'
OUT = Path(__file__).parent


def original_module(path, name):
    # The three core dependencies and policy are independently byte-checked.
    src = subprocess.check_output(['git', 'show', f'{BASE}:{path}'])
    m = types.ModuleType(name)
    m.__file__ = str(Path(path).resolve())
    exec(compile(src, m.__file__, 'exec'), m.__dict__)
    return m


def main():
    subprocess.check_call(['git','merge-base','--is-ancestor',HEAD,'HEAD'])
    subprocess.check_call(['git','diff','--exit-code',HEAD,'--','pcs'])
    for path in ('pcs/verifier_v06.py','pcs/lean_authority_v06.py','pcs/policy_v06.py',
                 'pcs/byte_contract_v06.py','pcs/receipt_contract_v06.py'):
        assert Path(path).read_bytes() == subprocess.check_output(['git','show',f'{BASE}:{path}'])
    oldzip = original_module('pcs/verifier_zip_v06.py','pcs._independent_baseline_zip')
    olddir = original_module('pcs/verifier_io_v06.py','pcs._independent_baseline_dir')
    spec=importlib.util.spec_from_file_location('_intake_test_helpers','tests/test_intake_verify_v06.py')
    helper=importlib.util.module_from_spec(spec); spec.loader.exec_module(helper)
    results=[]
    with tempfile.TemporaryDirectory(prefix='pcs-intake-independent-') as tmp:
        root=Path(tmp)
        bundle,pub,fp,lock,key=helper._attest_honest_bundle(root)
        loaded=load_package_zip_v06(bundle)
        changed=copy.deepcopy(lock['intake']);changed['claims'][0]['statement']='Independent post-hoc substitution'
        wrong=freeze_intake(changed,frozen_at=lock['frozen_at'])
        hashbad=copy.deepcopy(lock);hashbad['intake_semantic_hash']='00'*32
        extra=copy.deepcopy(lock);extra['undeclared']=True
        cases=[
            ('matching_optional',canonicalize_jcs_bytes(lock),{}),
            ('matching_required',canonicalize_jcs_bytes(lock),{'require_intake_lock':True}),
            ('matching_expected',canonicalize_jcs_bytes(lock),{'expected_intake_semantic_hash':lock['intake_semantic_hash']}),
            ('missing_optional',None,{}),
            ('missing_required',None,{'require_intake_lock':True}),
            ('missing_expected',None,{'expected_intake_semantic_hash':lock['intake_semantic_hash']}),
            ('wrong_expected',canonicalize_jcs_bytes(lock),{'expected_intake_semantic_hash':'ab'*32}),
            ('inconsistent_claim',canonicalize_jcs_bytes(wrong),{}),
            ('invalid_json',b'{',{}),
            ('invalid_utf8',b'\xff',{}),
            ('wrong_root_type',b'[]',{}),
            ('duplicate_keys',b'{"lock_format":"a","lock_format":"b"}',{}),
            ('bad_semantic_hash',canonicalize_jcs_bytes(hashbad),{}),
            ('unknown_member_field',canonicalize_jcs_bytes(extra),{}),
        ]
        for label,raw,options in cases:
            files=dict(loaded['package_files'])
            if raw is None: files.pop(MEMBER,None)
            else: files[MEMBER]=raw
            cert=json.loads(files['certificate.json'])
            inventory={n:{'sha256':hashlib.sha256(b).hexdigest(),'size':len(b)} for n,b in files.items()}
            manifest=build_package_manifest_v06(cert,inventory)
            members={**files,'certificate_signature.json':loaded['certificate_signature_bytes'],
                     'package_manifest.json':canonicalize_jcs_bytes(manifest),
                     'package_signature.json':canonicalize_jcs_bytes(sign_package_manifest_v06(manifest,key))}
            archive=root/(label+'.zip');archive.write_bytes(canonical_zip_bytes_v06(members))
            directory=root/label;directory.mkdir()
            for n,b in members.items():
                dst=directory/n;dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(b)
            for route,old,new,input_path in [
                ('zip',oldzip.verify_package_zip_end_to_end_v06,verify_package_zip_end_to_end_v06,archive),
                ('directory',olddir.verify_package_directory_end_to_end_v06,verify_package_directory_end_to_end_v06,directory)]:
                old_result=old(input_path,pub,expected_fingerprint=fp)
                new_result=new(input_path,pub,expected_fingerprint=fp,**options)
                row={'case':label,'route':route,'old_accepted':old_result['accepted'],
                     'new_accepted':new_result['accepted'],'new_valid':new_result['valid'],
                     'new_authoritative':new_result['authoritative'],'failed_stage':new_result.get('failed_stage'),
                     'lean_accepted':new_result.get('lean_authority',{}).get('accepted'),
                     'formal_package_authority':new_result.get('formal_coverage',{}).get('package_authority')}
                try:
                    write_verification_receipt_v06(new_result,root/(label+'-'+route+'-receipt.json'))
                    row['receipt_writable']=True
                except Exception as exc:
                    row['receipt_writable']=False;row['receipt_error']=f'{type(exc).__name__}: {exc}'
                assert not new_result['accepted'] or old_result['accepted'],row
                expected=label in ('matching_optional','matching_required','matching_expected','missing_optional')
                assert new_result['accepted'] is expected,row
                results.append(row)
    authority=Path(os.environ['PCS_LEAN_AUTHORITY_BIN'])
    report={'format':'pcs-pr153-independent-intake-differential-v1','base':BASE,'head':HEAD,
        'authority_binary_sha256':hashlib.sha256(authority.read_bytes()).hexdigest(),
        'authority_assumption':'Previously compiled receiver-owned executable, exact source preserved; this review does not independently rebuild or attest the compiler.',
        'cases':len(results),'old_accepts':sum(r['old_accepted'] for r in results),
        'new_accepts':sum(r['new_accepted'] for r in results),
        'receipt_write_failures':sum(not r['receipt_writable'] for r in results),
        'bounded_subset_observed':True,'formal_subset_theorem':False,'results':results}
    (OUT/'INTAKE_DIFFERENTIAL.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='results'},indent=2))


if __name__=='__main__':main()
