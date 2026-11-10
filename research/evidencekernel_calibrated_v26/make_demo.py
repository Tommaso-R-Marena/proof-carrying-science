"""Produce fully synthetic preregistration-style calibration and v25 evidence."""
from __future__ import annotations
from pathlib import Path
import json
from random import Random
from . import kernel as v26

ROOT=Path(__file__).parent
PREV=ROOT.parent/'evidencekernel_propensity_v25'

def generate():
    rng=Random(26011)
    probs=[(3,5),(2,5),(1,2)]
    sample_sizes=[512,512,512]
    streams=[[int(rng.randrange(b)<a) for _ in range(m)]
             for (a,b),m in zip(probs,sample_sizes)]
    contract={'format':v26.FORMAT,'state_count':3,'minimum_sample_sizes':sample_sizes,
              'maximum_sample_sizes':sample_sizes,'sample_size_policy':'fixed_per_state',
              'beta_spend_by_state':['1/300']*3,'grid_denominator':1000,
              'sampling_model':v26.SAMPLING,'require_nontrivial_ceiling':True}
    records={'assignment_bits_by_state':streams,'stage':'prestudy'}
    cpin=v26.digest(contract)
    rpin=v26.calibration_evidence_pin(cpin,records)
    cal=v26.calibrate(contract,records,contract_pin=cpin,records_pin=rpin)
    p=json.loads((PREV/'example_protocol.json').read_text())
    p['propensity_upper_by_state']=cal['propensity_ceiling_by_state']
    e=json.loads((PREV/'example_evidence.json').read_text())
    pp=v26.digest(p);ep=v26.v25.evidence_digest(pp,e)
    report=v26.audit(contract,records,p,e,
             calibration_contract_pin=cpin,calibration_records_pin=rpin,
             study_protocol_pin=pp,study_records_pin=ep)
    files={'calibration_contract.json':contract,'calibration_records.json':records,
           'study_protocol.json':p,'study_records.json':e,'example_report.json':report}
    for name,value in files.items():
        (ROOT/name).write_text(json.dumps(value,sort_keys=True,indent=2)+'\n')
    for name,value in [('calibration_contract_pin.txt',cpin),('calibration_records_pin.txt',rpin),
                       ('study_protocol_pin.txt',pp),('study_records_pin.txt',ep)]:
        (ROOT/name).write_text(value+'\n')
    return report

if __name__=='__main__':
    j=generate()
    print(json.dumps({'caps':j['calibration']['propensity_ceiling_by_state'],
     'beta':j['derived_propensity_calibration_failure_budget'],
     'error':j['joint_failure_bound_if_all_physical_assumptions_hold'],
     'lower':j['study_v25']['anytime_lower_ate'],'status':j['status']},indent=2))
