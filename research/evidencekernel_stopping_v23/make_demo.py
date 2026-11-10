from pathlib import Path
import json
try:
    from .kernel import digest, commitment, audit
except ImportError:
    from kernel import digest, commitment, audit

def make(path):
    path=Path(path);path.mkdir(parents=True,exist_ok=True)
    p={
      'format':'pcs-evidencekernel-stopping-v23', 'registered_units':4,
      'states':2, 'initial_state':0, 'min_enrollment':2,
      'allocation_weights_by_state':[[3,1],[1,3]],
      'next_state_by_state_action_report':[
          [[0,1],[0,1]], [[0,1],[0,1]]],
      'stop_after_by_state_action_report':[
          [[False,False],[False,True]],[[False,True],[False,True]]],
      'potential_schedule_model':'fixed_binary_potential_truth_and_report_schedule',
      'statistic':'stopped_binary_mean_difference_integer',
      'inference_rule':'exact_stopped_path_weak_null_maximization',
      'null_ate_upper':'0', 'confidence_alpha':'1/20', 'max_interval_misses':0
    }
    e={'assignments':[0,1,1], 'reports':[0,0,1], 'true_intervals':['0','1','1']}
    pin=digest(p);epin=commitment(pin,e)
    (path/'example_protocol.json').write_text(json.dumps(p,indent=2,sort_keys=True)+'\n')
    (path/'example_evidence.json').write_text(json.dumps(e,indent=2,sort_keys=True)+'\n')
    (path/'example_protocol_pin.txt').write_text(pin+'\n')
    (path/'example_evidence_pin.txt').write_text(epin+'\n')
    print(json.dumps(audit(p,e,protocol_pin=pin,evidence_pin=epin),indent=2))
if __name__=='__main__':make(Path(__file__).parent)
