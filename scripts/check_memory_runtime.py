"""Fresh kernel check of the published six-step transfer and a false claim."""
import gzip,json
from pathlib import Path
from pcs.experimental.prover.memory_cli import run,run_std
from pcs.experimental.prover.memory_environment import replay_memory_receipt

ROOT=Path(__file__).resolve().parents[1]
def check():
    folder=ROOT/'research/verified-memory-v1'
    example=json.loads(gzip.decompress((ROOT/'research/verified-memory-demonstration/learned.json.gz').read_bytes()))
    current=run(example['training_feedback']['original_statement'],folder,feedback=False)
    assert current['status']=='verified' and len(current['search']['receipt']['actions'])>=2
    goal=current['formalization']['candidates'][0]['ir']
    receipt=replay_memory_receipt(goal,current['search']['receipt'])
    negative=run('For all natural numbers a and b, (a + b) equals a.',folder,feedback=False)
    assert negative['status']=='verified_counterexample'
    assert negative['counterexample']['receipt']['kernel']['axioms']==[]
    strong=run_std('For all natural numbers a, b and c, if (a + b) equals (a + c) then b equals c.')
    assert strong['status']=='verified' and strong['search']['receipt']['format']=='pcs-std-baseline-proof-v1'
    print(json.dumps({'actual_trained_policy':True,'fresh_replay':True,
                      'proof_actions':len(receipt['actions']),'verified_counterexample':True,'strong_Std_baseline':True,
                      'scope':'Published regression example, not a new held-out benchmark.'}))
if __name__=='__main__':check()
