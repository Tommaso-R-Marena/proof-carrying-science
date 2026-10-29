"""Independently compile, kernel replay and execute the finite policy-update cases.

This is a research checker, not policy promotion or a protected storage service.
"""
import argparse
import json
from pathlib import Path
import subprocess
from .receiver import Checker, HERE, sha, _inventory

NAMES = tuple('PCSPolicyVersioning.' + n for n in (
    'updateOK_sound','update_available','selected_checkpoint_decreases','successor_updateOK',
    'versioned_safe_and_budget','versioned_length_bound','versioned_terminal_certificate',
    'versioned_completion_at_budget','RankReset.policyA_checked','RankReset.policyB_checked',
    'RankReset.stepA','RankReset.stepB','RankReset.every_rotating_step_locally_checked',
    'RankReset.rotating_never_goal','RankReset.rank_reset_refused','RankReset.productive_update_allowed',
    'RankReset.shifted_goal_locally_checked','RankReset.shifted_goal_refused'))
LAB_NAMES = tuple('PolicyLab.' + n for n in ('inflation_locally_checked','inflation_refused','incumbent_allowed'))
DRIVER = '''import Data
import PolicyVersioning
namespace PolicyLab
open PCSProgress PCSPolicyVersioning
def inflated : Spec := { PCSProgressData.spec with
  ranks := PCSProgressData.spec.ranks.map (fun p => (p.1, if p.2 = 0 then 0 else p.2 + 1)) }
theorem inflation_locally_checked : check inflated = true := by decide
theorem inflation_refused : updateOK PCSProgressData.spec inflated 0 (rank PCSProgressData.spec 0) = false := by decide
theorem incumbent_allowed : updateOK PCSProgressData.spec PCSProgressData.spec 0 (rank PCSProgressData.spec 0) = true := by decide
end PolicyLab
#print axioms PolicyLab.inflation_locally_checked
#print axioms PolicyLab.inflation_refused
#print axioms PolicyLab.incumbent_allowed

def main : IO Unit := do
  let task := PCSPolicyVersioning.RankReset.task
  let a := PCSPolicyVersioning.RankReset.policyA
  let b := PCSPolicyVersioning.RankReset.policyB
  IO.println (PCSPolicyVersioning.updateOK task b 1 (PCSProgress.rank a 1))
  IO.println (PCSPolicyVersioning.updateOK task b 0 (PCSProgress.rank a 0))
  IO.println (PCSPolicyVersioning.updateOK task PCSPolicyVersioning.RankReset.shiftedGoal 0 2)
  IO.println (PCSProgress.check PolicyLab.inflated)
  IO.println (PCSPolicyVersioning.updateOK PCSProgressData.spec PolicyLab.inflated 0 (PCSProgress.rank PCSProgressData.spec 0))
  IO.println (PCSPolicyVersioning.updateOK PCSProgressData.spec PCSProgressData.spec 0 (PCSProgress.rank PCSProgressData.spec 0))
'''.encode()


def qualify(output):
    host = Path(__file__).read_bytes()
    source = (HERE/'PolicyVersioning.lean').read_bytes()
    from scripts.audit_lean_source import audit
    failures = audit([HERE/'PolicyVersioning.lean'])
    if failures:raise ValueError('Research source admission refused: '+repr(failures))
    checker = Checker(output)
    closures = {}
    written = {'PolicyVersioning.lean':source, 'PolicyLab.lean':DRIVER}
    for name,blob in written.items():
        path = checker.output/name
        with path.open('xb') as stream:stream.write(blob)
        checker.check()
        log = checker.call([checker.tools['lean'],'-j1','-M2048','-D','Elab.async=false',
            '--root='+str(checker.output),'-o',name[:-5]+'.olean',name])
        closures.update(_inventory(log,NAMES if name=='PolicyVersioning.lean' else LAB_NAMES))
        checker.call([checker.tools['leanchecker'],'--fresh',name[:-5]])
        checker.check()
        checker.objects.update({p.name:sha(p.read_bytes()) for p in checker.output.glob(name[:-5]+'.olean*')})
        if path.read_bytes()!=blob:raise ValueError('Policy proof source changed')
    # Native evaluation is separately cross-checked against kernel-proved cases.
    execution = checker.call([checker.tools['lean'],'-j1','-M2048','--run','PolicyLab.lean'])
    lines = execution.splitlines()
    values = lines[-6:]
    if values != ['false','true','false','true','false','true']:
        raise ValueError('Executable policy decisions disagree with checked cases')
    checker.check()
    if Path(__file__).read_bytes()!=host or (HERE/'PolicyVersioning.lean').read_bytes()!=source or any((checker.output/n).read_bytes()!=b for n,b in written.items()):
        raise ValueError('Policy sources changed during checking')
    result = dict(format='pcs-policy-versioning-qualification-v1',kernel_checked=True,
        library_theorems=18,lab_contract_theorems=3,axiom_closures=closures,
        rank_reset_allowed=False,productive_update_allowed=True,changed_goal_allowed=False,
        real_agent_lab_inflation_locally_checked=True,real_agent_lab_inflation_update_allowed=False,
        real_agent_lab_incumbent_allowed=True,native_decisions=values,
        checker_host_sha256=sha(host),source_sha256={n:sha(b) for n,b in written.items()},
        foundational_source_sha256={n:sha(b) for n,b in checker.sources.items()},
        pcs_authority=False,inference_performed=False,
        scope='Finite-controller updates and carried budgets under fixed modeled outcomes, safety, forbidden effects and goals; authentic state/budget storage and deployment correspondence remain obligations')
    (checker.output/'policy-versioning.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output',type=Path)
    args=parser.parse_args()
    try:print(json.dumps(qualify(args.output)))
    except (OSError,ValueError,subprocess.SubprocessError):
        print(json.dumps(dict(status='REFUSED_OR_UNAVAILABLE',complete=False,pcs_authority=False)))
        raise SystemExit(20)
