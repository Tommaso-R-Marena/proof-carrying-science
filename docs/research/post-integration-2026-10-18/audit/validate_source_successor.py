"""Independent temporary-Git source-integrity challenge; no authority mocks.
Run with candidate path and exact commit. Never edits candidate source.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

OUT=Path(__file__).resolve().parent


def main():
    candidate=Path(sys.argv[1]).resolve(); expected=sys.argv[2]
    assert subprocess.check_output(['git','-C',str(candidate),'rev-parse','HEAD'],text=True).strip()==expected
    sys.path.insert(0,str(candidate))
    spec=importlib.util.spec_from_file_location('_review_successor_gate',candidate/'research/integration_v1/source_gate.py')
    gate=importlib.util.module_from_spec(spec);spec.loader.exec_module(gate)
    profile_path='docs/integration/2026-10-18/SOURCE_PROFILE.json'
    profile=json.loads((candidate/profile_path).read_bytes())
    paths=set(profile['files'])|{profile_path,gate.SUCCESSOR_PATH,gate.GATE_PATH,'pcs/receipt_contract_v06.py','docs/integration/2026-10-18/OPEN_PR_LEDGER.json'}
    results=[]
    mutations=['positive','gate_and_manifest','contract_and_manifest','test_and_manifest','missing_gate','formal_replacement','parent_path','nested_duplicate','untracked_manifest','symlink_manifest','symlink_profile','unchanged_formal_source']
    with tempfile.TemporaryDirectory(prefix='pcs-independent-successor-') as tmp:
        root=Path(tmp)
        for name in paths:
            p=root/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(candidate/name,p)
        subprocess.check_call(['git','init','-q',str(root)])
        subprocess.check_call(['git','add','.'],cwd=root)
        subprocess.check_call(['git','-c','user.name=PCS independent audit','-c','user.email=pcs-audit@example.invalid','commit','-qm','fixed candidate source snapshot'],cwd=root)
        gate.ROOT=root;gate.REPORTS=root/'docs/integration/2026-10-18'
        for mutation in mutations:
            subprocess.check_call(['git','reset','--hard','-q','HEAD'],cwd=root)
            manifest=root/gate.SUCCESSOR_PATH;j=json.loads(manifest.read_bytes())
            if mutation in {'gate_and_manifest','contract_and_manifest','test_and_manifest'}:
                name={'gate_and_manifest':gate.GATE_PATH,'contract_and_manifest':'pcs/receipt_contract_v06.py','test_and_manifest':'tests/test_intake_verify_v06.py'}[mutation]
                p=root/name;p.write_bytes(p.read_bytes()+b'\n# Independent unreviewed substitution\n')
                j['files'][name]['new_sha256']=hashlib.sha256(p.read_bytes()).hexdigest()
                manifest.write_text(json.dumps(j))
            elif mutation=='missing_gate':
                del j['files'][gate.GATE_PATH];manifest.write_text(json.dumps(j))
            elif mutation in {'formal_replacement','parent_path'}:
                name='formal/PCS/V2/ProofGatedPolicy.lean' if mutation=='formal_replacement' else '../escape.py'
                j['files'][name]=j['files'].pop(gate.GATE_PATH);manifest.write_text(json.dumps(j))
            elif mutation=='nested_duplicate':
                raw=manifest.read_text();key='"old_sha256":';raw=raw.replace(key,'"old_sha256":"'+'ab'*32+'",'+key,1);manifest.write_text(raw)
            elif mutation=='untracked_manifest':subprocess.check_call(['git','rm','--cached','-q',gate.SUCCESSOR_PATH],cwd=root)
            elif mutation in {'symlink_manifest','symlink_profile'}:
                p=manifest if mutation=='symlink_manifest' else root/profile_path
                target=root/'untracked-copy';target.write_bytes(p.read_bytes());p.unlink();p.symlink_to(target)
            elif mutation=='unchanged_formal_source':
                p=root/'formal/PCS/V2/ProofGatedPolicy.lean';p.write_bytes(p.read_bytes()+b'\n-- Independent source substitution\n')
            result=gate.check_profile();expected_pass=mutation=='positive'
            results.append({'mutation':mutation,'expected_pass':expected_pass,'actual_pass':result['passed'],'matches_expectation':result['passed'] is expected_pass,'failures':result['failures'],'files_checked':result['files_checked'],'additional_files_checked':result.get('additional_files_checked')})
    report={'candidate_commit':expected,'independent_identity_cases':len(results),'matches':sum(x['matches_expectation'] for x in results),'unexpected_accepts':[x['mutation'] for x in results if x['actual_pass'] and not x['expected_pass']],'production_authority':False,'test_scope':'Actual file/Git controls; imported gate executes against isolated snapshot, no verifier authorization is mocked.','results':results}
    path=OUT/f'SOURCE_SUCCESSOR_REVIEW_{expected[:7]}.json';path.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='results'},indent=2))


if __name__=='__main__':main()
