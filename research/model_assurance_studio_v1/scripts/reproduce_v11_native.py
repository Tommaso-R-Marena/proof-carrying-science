"""Retain independent C CPU measurements on the published Iris data.

No held-out claim: v0.9 operating regions were chosen using this dataset.
No ONNX Runtime/Lean/OS-sandbox authority inferred from these observations.
"""
from __future__ import annotations
import json
from pathlib import Path
from fractions import Fraction
from studio.native_fp32_crosscheck_v11 import compare
from studio.ieee754 import round_bits

ROOT=Path(__file__).resolve().parents[1]

def run():
    from sklearn.datasets import load_iris
    profile=json.loads((ROOT/'validation/v06_iris_profile.json').read_text())
    points=[]
    for row in load_iris().data:
        standardized=[(float(v)-mu)/sd for v,mu,sd in zip(row,
            profile['standard_scaler_mean'],profile['standard_scaler_scale'])]
        points.append([f'{round_bits(Fraction.from_float(v)):08x}' for v in standardized])
    raw=(ROOT/'samples/demo_trained_iris_updated.onnx').read_bytes()
    report=compare(raw,points)
    return dict(report,dataset='Iris (all 150 entries; used in envelope construction)',
                model_input_scaling='v06 saved StandardScaler mean and scale',
                total_input_vectors=len(points))


def main(argv=None):
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument('--output',help='save observed report for reproducibility')
    a=p.parse_args(argv)
    try:r=run()
    except Exception as exc:r={'status':'NOT_RUN','reason':type(exc).__name__+': '+str(exc)[:100]}
    data=json.dumps(r,sort_keys=True,indent=2)+'\n'
    if a.output:Path(a.output).write_text(data)
    print(data,end='')
    return 0 if r.get('status')=='AGREE_ON_TESTED_POINTS' and r.get('checked_points')==150 else 2

if __name__=='__main__':raise SystemExit(main())
