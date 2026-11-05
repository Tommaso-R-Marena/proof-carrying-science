"""Real local TCP upload for the binary32 endpoint; Chromium smoke separately."""
import json
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import quote
import httpx
from studio.fp32_assurance import verify

ROOT=Path(__file__).resolve().parents[1]
URL='http://127.0.0.1:8765'

def main():
    proc=subprocess.Popen([sys.executable,'-m','uvicorn','studio.server:app',
        '--host','127.0.0.1','--port','8765'],cwd=ROOT,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
    try:
        with httpx.Client(trust_env=False,timeout=12) as client:
            for _ in range(80):
                if proc.poll() is not None:raise RuntimeError('server exited early '+proc.stderr.read().decode()[-400:])
                try:
                    res=client.get(URL+'/api/status')
                    if res.status_code==200:break
                except httpx.RequestError:pass
                time.sleep(.1)
            else:raise RuntimeError('server failed to start')
            assert res.json()['fp32_exact_rounding_intervals_available'] is True
            model=(ROOT/'samples/demo_dense_neural_violation.onnx').read_bytes()
            claim={'input_box':[['-1','1'],['-1','1']],'input_min':'-1','input_max':'1',
                   'output_coefficients':['1','0'],'upper_limit':'5/4'}
            headers={'X-PCS-Fp32-Claim':quote(json.dumps(claim))}
            res=client.post(URL+'/api/fp32-assure',content=model,headers=headers)
            assert res.status_code==200,res.text
            response=res.json()
            assert response['assessment']['status']=='PROVED_CONDITIONALLY'
            assert response['independent_reviewer_acceptance']=='NOT_ESTABLISHED'
            assert verify(model,response['suggested_reviewer_policy'],response['assessment'])[0]
            print('PASS actual TCP/HTTP binary32 upload -> conditional proof -> independent replay')
            denied=client.post(URL+'/api/fp32-assure',content=model,
                               headers={**headers,'Origin':'https://bad.example'})
            assert denied.status_code==403
            bad=client.post(URL+'/api/fp32-assure',content=b'garbage',headers=headers)
            assert bad.status_code==400
            print('PASS actual HTTP origin rejection and malformed model rejection')
    finally:
        proc.terminate()
        try:proc.communicate(timeout=4)
        except subprocess.TimeoutExpired:proc.kill();proc.communicate()

if __name__=='__main__':main()
