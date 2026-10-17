"""Frozen retrospective computational experiments on real Delft measurements."""
from pathlib import Path
from fractions import Fraction as Q
import argparse
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import resource
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from pcs import calibration_kernel_v1 as receiver
from pcs.experimental.calibration_proposer_v1 import propose
from pcs.canonical_json import canonicalize_jcs_bytes as encode

EXAMPLE=ROOT/'examples/experimental_calibration_v1'
PROTOCOL=ROOT/'research/experimental-calibration-v1/PROTOCOL.json'


def groups():
    raw=(EXAMPLE/'yacht_hydrodynamics.data').read_bytes()
    provenance=json.loads((EXAMPLE/'provenance.json').read_bytes())
    assert receiver.sha(raw)==provenance['data_sha256']==json.loads(PROTOCOL.read_bytes())['data_sha256']
    assert receiver.sha((EXAMPLE/'UPSTREAM_LICENSE.txt').read_bytes())==provenance['license_sha256']
    result=OrderedDict();count=0
    for source_row,line in enumerate(raw.decode('ascii').splitlines(),1):
        if not line.strip():continue
        columns=line.split();assert len(columns)==7
        values=list(map(Q,columns));key=tuple(values[:5])
        result.setdefault(key,[]).append((values[5],values[6],source_row));count+=1
    assert count==308 and len(result)==22
    for rows in result.values():
        rows.sort();assert len(rows)==14 and len({r[0] for r in rows})==14
        assert [r[0] for r in rows]==[Q(i,40) for i in range(5,19)]
    return result


def inputs(rows):
    data=('x,y\n'+''.join(f'{40*x},{y}\n' for x,y,_ in rows)).encode()
    models=[]
    for degree in [1,2,3]:
        models.append({'degree':degree,'fit_rows':list(range(0,14,2)),
                       'queries':[str(40*rows[i][0]) for i in range(1,14,2)]+['24']})
        models.append({'degree':degree,'fit_rows':list(range(14)),'queries':[]})
    contract=encode({'format':receiver.FORMAT,'data_sha256':receiver.sha(data),'models':models})
    return data,contract,propose(data,contract)


def metrics(rows,certificate):
    models=json.loads(certificate)['models'];result=[]
    for index,degree in enumerate([1,2,3]):
        b=list(map(Q,models[2*index]['coefficients']))
        residuals=[y-sum(c*(40*x)**j for j,c in enumerate(b)) for x,y,_ in rows[1::2]]
        # Different algorithm: QR/SVD on a floating Vandermonde, no certificate authority.
        import numpy as np
        train=rows[::2];a=np.array([[float(40*x)**j for j in range(degree+1)] for x,_,_ in train])
        baseline=np.linalg.lstsq(a,np.array([float(y) for _,y,_ in train]),rcond=None)[0]
        error=float(np.max(np.abs(baseline-np.array(list(map(float,b))))))
        assert np.allclose(baseline,list(map(float,b)),atol=1e-9,rtol=1e-9)
        q=models[2*index]['queries'][-1];weights=list(map(Q,q['weights']))
        mm=q['minimax'];mmweights=list(map(Q,mm['weights']))
        mm_residuals=[]
        for observation,witness in zip(rows[1::2],models[2*index]['queries'][:-1]):
            estimate=sum(Q(w)*y for w,(_,y,_) in zip(witness['minimax']['weights'],train))
            mm_residuals.append(observation[1]-estimate)
        # Actual worst-case perturbation experiment, not only evaluation of a formula.
        training_y=[y for _,y,_ in train];perturbations=[]
        for epsilon in [Q(0),Q(1,1000),Q(1,100)]:
            changed=[y+(epsilon if w>=0 else -epsilon) for y,w in zip(training_y,weights)]
            shift=sum(w*(z-y) for w,z,y in zip(weights,changed,training_y))
            assert shift==epsilon*Q(q['gain'])
            perturbed_fit=np.linalg.lstsq(a,np.array(list(map(float,changed))),rcond=None)[0]
            refit_shift=sum((24**j)*(v-float(c)) for j,(v,c) in enumerate(zip(perturbed_fit,b)))
            assert abs(refit_shift-float(shift))<=1e-8
            mmchanged=[y+(epsilon if w>=0 else -epsilon) for y,w in zip(training_y,mmweights)]
            mmshift=sum(w*(z-y) for w,z,y in zip(mmweights,mmchanged,training_y))
            assert mmshift==epsilon*Q(mm['gain']) and Q(mm['gain'])<=Q(q['gain'])
            perturbations.append({'epsilon':str(epsilon),'exact_ls_shift':str(shift),
                'exact_minimax_shift':str(mmshift),'measured_numpy_ls_refit_shift':refit_shift})
        result.append({'degree':degree,'heldout_sse':str(sum(r*r for r in residuals)),
            'heldout_max_abs_error':str(max(map(abs,residuals))),
            'full_data_globally_minimal_sse':models[2*index+1]['sse'],
            'heldout_gains':[q['gain'] for q in models[2*index]['queries'][:-1]],
            'extrapolation_gain':q['gain'],'attained_extrapolation_shift_at_epsilon_0.01':str(shift),
            'minimax_heldout_sse':str(sum(r*r for r in mm_residuals)),
            'minimax_heldout_max_abs_error':str(max(map(abs,mm_residuals))),
            'minimax_heldout_gains':[q['minimax']['gain'] for q in models[2*index]['queries'][:-1]],
            'minimax_extrapolation_gain':mm['gain'],
            'attained_minimax_extrapolation_shift_at_epsilon_0.01':str(mmshift),
            'measured_numpy_refit_extrapolation_shift':refit_shift,
            'perturbation_experiments':perturbations,
            'uniform_error_exclusions_derived_from_certified_loss':[
                {'epsilon':str(e),'training_excluded':Q(models[2*index]['sse'])>7*e*e,
                 'full_data_excluded':Q(models[2*index+1]['sse'])>14*e*e}
                for e in [Q(0),Q(1,1000),Q(1,100)]],
            'numpy_max_coefficient_abs_error':error})
    return result


def run(output,*,pilot=False,workers=2):
    output.mkdir(parents=True,exist_ok=False)
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    dirty=bool(subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip())
    frozen={n:receiver.sha(b) for n,b in receiver.sources().items()}
    def write(path,value):path.write_bytes(encode(value))
    write(output/'EXECUTION_PROTOCOL.json',{'source_head':head,'source_tree_dirty':dirty,'pilot':pilot,
        'protocol_sha256':receiver.sha(PROTOCOL.read_bytes()),
        'minimax_addendum_sha256':receiver.sha((PROTOCOL.parent/'MINIMAX_ADDENDUM.json').read_bytes()),'source_sha256':frozen,
        'all_estimators_addendum_sha256':receiver.sha((PROTOCOL.parent/'ALL_ESTIMATORS_ADDENDUM.json').read_bytes()),
        'process_replay_addendum_sha256':receiver.sha((PROTOCOL.parent/'PROCESS_REPLAY_ADDENDUM.json').read_bytes()),
        'proposer_sha256':receiver.sha((ROOT/'pcs/experimental/calibration_proposer_v1.py').read_bytes()),
        'runner_sha256':receiver.sha(Path(__file__).read_bytes()),'frozen_before_execution':True,
        'isolated_receiving_workers':workers})
    start=time.monotonic();results=[];numpy_version=None
    cases=list(enumerate(groups().items()))
    if pilot:cases=cases[:1]
    def receive(item):
        k,(hull,rows)=item
        case=output/f'hull-{k:02}';case.mkdir()
        data,contract,certificate=inputs(rows)
        for name,raw in [('data.csv',data),('contract.json',contract),('certificate.json',certificate)]:
            (case/name).write_bytes(raw)
        command=[sys.executable,'-m','pcs.cli','calibration-kernel-v1','--data',str(case/'data.csv'),
                 '--contract',str(case/'contract.json'),'--certificate',str(case/'certificate.json'),
                 '--output',str(case/'receiving')]
        p=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,timeout=360)
        (case/'receiving.log').write_text(p.stdout+p.stderr)
        report=json.loads((case/'receiving/report.json').read_bytes())
        if p.returncode or not report['accepted']:
            raise RuntimeError(f'kernel receiver rejected hull {k}; inspect {case}')
        record={'hull':list(map(str,hull)),'source_rows':[r[2] for r in rows],
                'training_source_rows':[r[2] for r in rows[::2]],
                'heldout_source_rows':[r[2] for r in rows[1::2]],
                'models':metrics(rows,certificate),'kernel_theorems':len(report['kernel']['kernel_theorems']),
                'report_sha256':receiver.sha((case/'receiving/report.json').read_bytes())}
        write(case/'METRICS.json',record)
        print(json.dumps({'hull':k,'accepted':True,'kernel_theorems':record['kernel_theorems']}),flush=True)
        return record
    with ThreadPoolExecutor(max_workers=workers) as pool:results=list(pool.map(receive,cases))
    assert frozen=={n:receiver.sha(b) for n,b in receiver.sources().items()}
    import numpy as np
    summary={'format':'pcs-experimental-calibration-result-v1','passed':True,'pilot':pilot,
        'source_head':head,'source_tree_dirty':dirty,'hulls':len(results),
        'isolated_receiving_workers':workers,
        'training_measurements':7*len(results),'heldout_measurements':7*len(results),
        'fit_certificates':6*len(results),'sharp_query_certificates':24*len(results),
        'pooled_heldout_sse':{str(d):str(sum(Q(r['models'][d-1]['heldout_sse']) for r in results)) for d in [1,2,3]},
        'minimax_pooled_heldout_sse':{str(d):str(sum(Q(r['models'][d-1]['minimax_heldout_sse']) for r in results)) for d in [1,2,3]},
        'quadratic_beats_linear_hulls':sum(Q(r['models'][1]['heldout_sse'])<Q(r['models'][0]['heldout_sse']) for r in results),
        'cubic_beats_quadratic_hulls':sum(Q(r['models'][2]['heldout_sse'])<Q(r['models'][1]['heldout_sse']) for r in results),
        'receivers':results,'numpy_version':np.__version__,'wall_seconds':round(time.monotonic()-start,6),
        'child_peak_rss_kib':resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
        'scientific_acceptance':False,'external_domain_review':'NOT_OBTAINED','new_physical_measurements':0,
        'physical_model_validity':'OPEN','measurement_error_bound':'ASSUMED_SCENARIO_ONLY','spend':0}
    write(output/'SUMMARY.json',summary)
    write(output/'SHA256.json',{'files':{str(p.relative_to(output)):receiver.sha(p.read_bytes())
        for p in sorted(output.rglob('*')) if p.is_file()}})
    print(json.dumps({k:summary[k] for k in ['passed','hulls','fit_certificates','sharp_query_certificates','pooled_heldout_sse','wall_seconds']}))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--pilot',action='store_true');p.add_argument('--workers',type=int,choices=[1,2],default=2)
    a=p.parse_args();run(a.output,pilot=a.pilot,workers=a.workers)
