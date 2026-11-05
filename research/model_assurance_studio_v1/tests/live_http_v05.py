"""Genuine local socket and Uvicorn transport smoke.

Does not invoke Chromium (blocked from localhost by this test environment).
Test must be run when port 8765 is unused.
"""
import json
import subprocess
import sys
import time
from pathlib import Path
import httpx

ROOT=Path(__file__).resolve().parents[1]
BASE='http://127.0.0.1:8765'

def main():
    proc=subprocess.Popen([sys.executable,'-m','uvicorn','studio.server:app','--host','127.0.0.1','--port','8765'],cwd=ROOT,
                          stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    try:
        with httpx.Client(trust_env=False,timeout=15) as client:
            for i in range(75):
                if proc.poll() is not None:raise RuntimeError('server exited early')
                try:
                    st=client.get(BASE+'/api/status')
                    if st.status_code==200:break
                except httpx.RequestError:pass
                time.sleep(.1)
            else:raise RuntimeError('server not ready')
            assert st.json()['version']=='0.5.0'
            assert client.get(BASE).status_code==200
            assert client.get(BASE+'/app.js').status_code==200
            raw=(ROOT/'samples/demo_hidden_spike.onnx').read_bytes()
            policy={'check_output_bounds':True,'search_scalar_witness':True,'enable_reference_replay':True,
                    'enable_milp_challenger':True,'output_min':0,'output_max':0.5}
            r=client.post(BASE+'/api/analyze',content=raw,headers={'x-pcs-filename':'demo_hidden_spike.onnx',
                                'x-pcs-policy':json.dumps(policy)})
            assert r.status_code==200,r.text[:300]
            assert r.json()['details']['milp_replay']['status']=='VIOLATION_REPRODUCED'
            print('PASS live HTTP file intake + solver-guided numerical replay')
            r=client.post(BASE+'/api/attack-campaign')
            assert r.status_code==200 and r.json()['unexpected_authorizations']==0
            print('PASS live HTTP synthetic challenge, 64 adversarial proposals')
            assert client.post(BASE+'/api/analyze',content=raw,headers={'Host':'evil.example'}).status_code==403
            assert client.post(BASE+'/api/analyze',content=raw,headers={'Origin':'https://malicious.example'}).status_code==403
            print('PASS live HTTP Host / Origin restrictions')
    finally:
        proc.terminate()
        try:proc.communicate(timeout=4)
        except subprocess.TimeoutExpired:proc.kill();proc.communicate()

if __name__=='__main__':main()
