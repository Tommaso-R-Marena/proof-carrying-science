"""Independent deterministic replay of the bundled dual-operating envelope."""
import hashlib
import json
from pathlib import Path
from studio.relational_kernel import canonical
from studio.dual_envelope_v10 import DualAssuranceGate

BASE=Path(__file__).resolve().parents[1]
def main():
    old=(BASE/'samples/demo_trained_iris_mlp.onnx').read_bytes()
    new=(BASE/'samples/demo_trained_iris_updated.onnx').read_bytes()
    policy=json.loads((BASE/'validation/v09_demo_envelope_reviewer_policy.json').read_text())
    real=json.loads((BASE/'validation/v09_demo_envelope_evidence.json').read_text())
    direct=json.loads((BASE/'validation/v10_direct_fp32_partition_evidence.json').read_text())
    words=json.loads((BASE/'validation/v09_demo_input_words.json').read_text())
    expected='aec03cc456c9f6c77e548cffa1dc1503d795c1934d97d114afe4b4a0d7418c6d'
    if hashlib.sha256(canonical(policy)).hexdigest()!=expected:
        raise SystemExit('FAIL: source control fixture fingerprint changed')
    guard=DualAssuranceGate(old,new,real,direct,policy,expected)
    review=guard.review()
    if review['status']!='PROVED_CONDITIONALLY' or review['direct_float32_comparisons']!=6 or review['real_certificate_comparisons']!=6:
        raise SystemExit('FAIL: both complete proof families must verify')
    for index,cls in [('22',0),('62',1),('118',2)]:
        decision=guard.admit(words[index])
        result=guard.reference_infer(words[index])
        if decision['status']!='ADMIT_CONDITIONALLY' or decision['class_index']!=cls or result['status']!='EXECUTED_CONDITIONALLY':
            raise SystemExit('FAIL: certified anchor did not pass screened software reference')
    if guard.admit(['00000000']*4)['status']!='ABSTAIN' or guard.reference_infer(['00000000']*4)['status']!='ABSTAIN':
        raise SystemExit('FAIL: outside input should not run')
    print(json.dumps({'status':'REPLAY_PASSED','review':review,
        'conditionally_admitted_fixtures':3,'outside_fixture_abstained':True,
        'note':'Local Python research replay; NOT Lean or ONNX Runtime verified'},indent=2,sort_keys=True))

if __name__=='__main__':main()
