"""Independent validation of a committed, narrowly scoped intake receipt repair.
This never writes the candidate worktree. Original failing evidence stays intact.
Usage: python validate_receipt_repair.py /candidate/worktree EXPECTED_COMMIT
"""
import json
import os
from pathlib import Path
import subprocess
import sys

BASELINE = 'b916eec1b9d0d5c02c9cc19b070f7a47df5e5d87'
OUT = Path(__file__).resolve().parent


def main():
    candidate = Path(sys.argv[1]).resolve()
    expected = sys.argv[2]
    actual = subprocess.check_output(['git','-C',str(candidate),'rev-parse','HEAD'],text=True).strip()
    assert actual == expected
    changes=set(subprocess.check_output(['git','-C',str(candidate),'diff','--name-only',BASELINE,expected],text=True).splitlines())
    allowed={'pcs/receipt_contract_v06.py','pcs/intake_verify_v06.py','tests/test_intake_verify_v06.py',
             'docs/research/post-integration-2026-10-18/intake-receipt-fix.md'}
    assert changes == allowed, changes
    assert not subprocess.check_output(['git','-C',str(candidate),'status','--porcelain'],text=True).strip()
    # Reuse exactly the original corpus constructors, selecting only deliberate
    # repair deltas and a separate output path. No original evidence is replaced.
    source=(OUT/'reproduce_intake_review.py').read_text()
    source=source.replace("    subprocess.check_call(['git','diff','--exit-code',HEAD,'--','pcs'])\n",'')
    source=source.replace(", 'pcs/receipt_contract_v06.py'",'')
    source=source.replace("'pcs/byte_contract_v06.py','pcs/receipt_contract_v06.py'", "'pcs/byte_contract_v06.py'")
    source=source.replace("OUT = Path(__file__).parent",f"OUT = Path({str(OUT)!r})")
    source=source.replace("'INTAKE_DIFFERENTIAL.json'","'REPAIRED_INTAKE_DIFFERENTIAL.json'")
    source=source.replace("'head':HEAD",f"'head':{expected!r}")
    source=source.replace("if __name__=='__main__':main()",'')
    controls=r'''
from pcs.receipt_contract_v06 import audit_verification_receipt_v06
_tamper=[]
_original_zip=verify_package_zip_end_to_end_v06
_original_dir=verify_package_directory_end_to_end_v06

def _wrap_verifier(fn,route):
    def checked(*args,**kw):
        r=fn(*args,**kw)
        assert audit_verification_receipt_v06(r)['valid'],r
        if r['valid'] is False:
            assert r['lean_authority']['accepted'] is True
            assert r['accepted'] is False and r['authoritative'] is False
            import copy
            mutations=[]
            a=copy.deepcopy(r);a.pop('intake_lock');mutations.append(('delete_veto',a))
            a=copy.deepcopy(r);a['intake_lock']['valid']=True;mutations.append(('false_valid_veto',a))
            a=copy.deepcopy(r);a['stages']['intake_lock']=True;mutations.append(('erase_veto_stage',a))
            a=copy.deepcopy(r);a['stages']['lean_authority']=False;mutations.append(('falsify_real_lean_stage',a))
            a=copy.deepcopy(r);a['errors']=[];mutations.append(('erase_receiving_errors',a))
            a=copy.deepcopy(r);a['failed_stage']='other';mutations.append(('unrelated_failure',a))
            a=copy.deepcopy(r);a.update(valid=True,accepted=True,authoritative=True);mutations.append(('launder_to_accept',a))
            a=copy.deepcopy(r);a['lean_authority']['accepted']=False;a['lean_authority']['verdict']='REJECT';mutations.append(('fabricate_lean_reject',a))
            if r['intake_lock']['present']:
                a=copy.deepcopy(r);a['intake_lock'].pop('member_sha256',None);mutations.append(('delete_member_identity',a))
            for name,a in mutations:
                verdict=audit_verification_receipt_v06(a)
                assert verdict['valid'] is False,(route,name,verdict)
                _tamper.append({'route':route,'mutation':name,'rejected':True})
        return r
    return checked
verify_package_zip_end_to_end_v06=_wrap_verifier(_original_zip,'zip')
verify_package_directory_end_to_end_v06=_wrap_verifier(_original_dir,'directory')
main()
(OUT/'REPAIR_TAMPER_CONTROLS.json').write_text(json.dumps(_tamper,indent=2)+'\n')
'''
    env=dict(os.environ);env['PYTHONPATH']=str(candidate)
    run=subprocess.run([sys.executable,'-c',source+'\n'+controls],cwd=candidate,env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    (OUT/'REPAIR_INDEPENDENT_VALIDATION.log').write_text(run.stdout)
    assert run.returncode == 0,run.stdout
    before=json.loads((OUT/'INTAKE_DIFFERENTIAL.json').read_text())
    after=json.loads((OUT/'REPAIRED_INTAKE_DIFFERENTIAL.json').read_text())
    assert after['cases']==28 and after['receipt_write_failures']==0
    keys=('case','route','old_accepted','new_accepted','new_valid','new_authoritative','failed_stage','lean_accepted','formal_package_authority')
    assert [{k:r[k] for k in keys} for r in before['results']]==[{k:r[k] for k in keys} for r in after['results']]
    tamper=json.loads((OUT/'REPAIR_TAMPER_CONTROLS.json').read_text())
    result={'candidate_commit':expected,'baseline_commit':BASELINE,'source_changes':sorted(changes),'actual_lean_cases':28,
            'original_acceptance_decisions_preserved':True,'rejection_receipt_write_failures_before':20,
            'rejection_receipt_write_failures_after':0,'independent_tamper_checks_rejected':len(tamper),
            'mocked_positive_authority':False,'release_approval':False}
    (OUT/'REPAIR_INDEPENDENT_VALIDATION.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
