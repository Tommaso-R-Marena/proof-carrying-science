"""Genuine TCP/HTTP integration for v0.6; browser transport tested separately."""
import json
import subprocess
import sys
import time
from pathlib import Path
import httpx
from studio.verify_relational import verify_with_policy,POLICY_SCHEMA

ROOT=Path(__file__).resolve().parents[1]
BASE='http://127.0.0.1:8765'

def main():
    proc=subprocess.Popen([sys.executable,'-m','uvicorn','studio.server:app',
            '--host','127.0.0.1','--port','8765'],cwd=ROOT,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
    try:
        with httpx.Client(trust_env=False,timeout=12) as client:
            for _ in range(80):
                if proc.poll() is not None:raise RuntimeError('server exited early: '+proc.stderr.read().decode()[-2000:])
                try:
                    r=client.get(BASE+'/api/status')
                    if r.status_code==200:break
                except httpx.RequestError:pass
                time.sleep(.1)
            else:raise RuntimeError('server did not start')
            assert r.json()['version']=='0.6.0'
            assert r.json()['exact_relational_dual_checker_available'] is True
            raw=(ROOT/'samples/demo_trained_iris_mlp.onnx').read_bytes()
            prof=json.loads((ROOT/'validation/v06_iris_profile.json').read_text())
            claim=prof['properties'][0]
            pol={'enable_relational_certificate':True,'relational_input_box':prof['reviewer_box'],
                 'relational_coefficients':claim['output_coefficients'],
                 'relational_upper_limit':claim['upper_limit']}
            resp=client.post(BASE+'/api/analyze',content=raw,
                headers={'X-PCS-Filename':'demo_trained_iris_mlp.onnx','X-PCS-Policy':json.dumps(pol)})
            assert resp.status_code==200,resp.text[:500]
            report=resp.json()
            assert report['details']['relational_proof']['status']=='PROVED_CONDITIONALLY'
            cert=report['details']['relational_proof']['certificate']
            expected={'schema':POLICY_SCHEMA,'input_box':prof['reviewer_box'],
                      'output_coefficients':claim['output_coefficients'],
                      'upper_limit':claim['upper_limit']}
            assert verify_with_policy(raw,cert,expected)[0]
            print('PASS actual local HTTP trained-model upload → exact certificate → standalone reviewer check')
            raw=(ROOT/'samples/demo_activation_identity.onnx').read_bytes()
            pol={'enable_relational_certificate':True,'enable_activation_case_cover':True,
                 'relational_coefficients':['1'],'relational_upper_limit':'0'}
            resp=client.post(BASE+'/api/analyze',content=raw,
                headers={'X-PCS-Filename':'demo_activation_identity.onnx','X-PCS-Policy':json.dumps(pol)})
            assert resp.status_code==200,resp.text[:500]
            assert resp.json()['details']['activation_proof']['status']=='PROVED_CONDITIONALLY'
            print('PASS actual local HTTP activation-case proof')
            # Real HTTP, binary double-upload, independent acceptance of both certificates.
            from studio.verify_update import verify_composition
            from studio.model_update import compare
            from urllib.parse import quote
            old=(ROOT/'samples/demo_trained_iris_mlp.onnx').read_bytes()
            new=(ROOT/'samples/demo_trained_iris_updated.onnx').read_bytes()
            policy={'input_box':prof['reviewer_box'],'output_coefficients':['-1','1','0'],
                    'baseline_upper_limit':'-1/2','drift_upper_limit':'1/8',
                    'required_new_upper_limit':'-3/8'}
            body=len(old).to_bytes(4,'little')+old+new
            updated=client.post(BASE+'/api/compare-update',content=body,
                    headers={'X-PCS-Update-Policy':quote(json.dumps(policy))})
            assert updated.status_code==200,updated.text[:600]
            evidence=updated.json()
            assert evidence['status']=='PROVED_CONDITIONALLY',str(evidence)[:600]
            ok,out=verify_composition(old,new,evidence['baseline']['certificate'],
                    evidence['baseline_reviewer_policy'],evidence['update']['certificate'],
                    evidence['update_reviewer_policy'],required_updated_upper_limit='-3/8')
            assert ok,str(out)
            assert out['derived_new_model_upper_bound']=='-3/8'
            print('PASS actual HTTP two-model upload → baseline + drift → independent composition')
            rejected=client.post(BASE+'/api/compare-update',content=body,
                    headers={'X-PCS-Update-Policy':quote(json.dumps(policy)),
                             'Origin':'https://unauthorized.example'})
            assert rejected.status_code==403
            invalid=client.post(BASE+'/api/compare-update',content=b'broken',
                    headers={'X-PCS-Update-Policy':quote(json.dumps(policy))})
            assert invalid.status_code==400
            print('PASS actual HTTP malformed two-model envelope and origin rejection')
            assert client.get(BASE+'/api/iris-demo-profile').status_code==200
            assert client.post(BASE+'/api/analyze',content=raw,headers={'Host':'malicious.example'}).status_code==403
            assert client.post(BASE+'/api/analyze',content=raw,headers={'Origin':'https://malicious.example'}).status_code==403
            print('PASS fixed demo source and Host/Origin checks')
    finally:
        proc.terminate()
        try:proc.communicate(timeout=4)
        except subprocess.TimeoutExpired:proc.kill();proc.communicate()

if __name__=='__main__':main()
