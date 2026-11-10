"""Generate offline synthetic fixture; all pins are DEMO ONLY, not timestamp evidence."""
import json
from pathlib import Path
from research.evidencekernel_anytime_calibration_v27 import kernel as k
from research.evidencekernel_propensity_v25 import kernel as v25
from research.evidencekernel_calibrated_v26 import kernel as v26

def put(path,data): path.write_text(json.dumps(data,sort_keys=True,indent=2)+'\n')

def main():
    here=Path(__file__).parent
    old=Path('research/evidencekernel_calibrated_v26')
    c0=v25.read(old/'calibration_contract.json')
    r0=v25.read(old/'calibration_records.json')
    p0=v25.read(old/'study_protocol.json')
    e0=v25.read(old/'study_records.json')
    c={'format':k.FORMAT,'sampling_model':k.SAMPLING,
       'state_count':c0['state_count'],
       'minimum_sample_sizes':[16]*c0['state_count'],
       'maximum_sample_sizes':[512]*c0['state_count'],
       'beta_spend_by_state':c0['beta_spend_by_state'],
       'grid_denominator':c0['grid_denominator'],
       'e_mixture_ratios':['1/2','3/4','7/8','15/16','31/32','63/64','127/128','255/256'],
       'drift_mixture_ratios':['1/2','3/4','7/8'],
       'drift_alarm_spend_by_state':['1/300']*c0['state_count'],
       'require_nontrivial_ceiling':True}
    cp=k.digest(c);rp=k.record_pin(cp,r0)
    cal=k.calibrate(c,r0,contract_pin=cp,records_pin=rp)
    p0['propensity_upper_by_state']=cal['propensity_ceiling_by_state']
    pp=k.digest(p0);ep=v25.evidence_digest(pp,e0)
    report=k.audit(c,r0,p0,e0,contract_pin=cp,records_pin=rp,
                   study_pin=pp,evidence_pin=ep)
    put(here/'example_contract.json',c)
    put(here/'example_records.json',r0)
    put(here/'example_study_protocol.json',p0)
    put(here/'example_study_records.json',e0)
    put(here/'example_report.json',report)
    for path,pin in [('example_contract_pin.txt',cp),('example_records_pin.txt',rp),
                     ('example_study_pin.txt',pp),('example_evidence_pin.txt',ep)]:
        (here/path).write_text(pin+'\n')
    print('ceilings',cal['propensity_ceiling_by_state'],'ATE',report['study_v25']['anytime_lower_ate'],'alarm',report['drift_monitor']['alarm'])
if __name__=='__main__': main()
