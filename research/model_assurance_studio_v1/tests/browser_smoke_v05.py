"""Browser interaction smoke using REAL analyzer outputs and stubbed browser transport.

Chromium in this environment is prohibited from local HTTP navigation. This tests
DOM/UI flow and rendering, but NOT browser-to-server transport (tested separately).
"""
from __future__ import annotations
import base64
import json
from pathlib import Path
from playwright.sync_api import sync_playwright
from studio.engine import analyze

ROOT=Path(__file__).resolve().parents[1]
BLOB=(ROOT/'samples/demo_partition_abs.onnx').read_bytes()
DENSE=(ROOT/'samples/demo_dense_neural_violation.onnx').read_bytes()
HIDDEN=(ROOT/'samples/demo_hidden_spike.onnx').read_bytes()
POLICY_PARTITION={'check_output_bounds':True,'enable_partition_proof':True,'max_partition_leaves':16,
                  'input_min':-1,'input_max':1,'output_min':0,'output_max':1,'search_scalar_witness':False}
POLICY_MILP={'check_output_bounds':True,'search_scalar_witness':True,'enable_reference_replay':True,
             'enable_milp_challenger':True,'enable_torch_crosscheck':True,'milp_timeout_seconds':6,
             'input_min':-1,'input_max':1,'output_min':0,'output_max':.5}
POLICY_DENSE={'check_output_bounds':True,'enable_reference_replay':True,'enable_torch_crosscheck':True,
              'search_scalar_witness':True,'input_min':-1,'input_max':1,'output_min':0,'output_max':1}
reports={'demo_partition_abs.onnx':analyze('demo_partition_abs.onnx',BLOB,POLICY_PARTITION),
         'demo_dense_neural_violation.onnx':analyze('demo_dense_neural_violation.onnx',DENSE,POLICY_DENSE),
         'demo_hidden_spike.onnx':analyze('demo_hidden_spike.onnx',HIDDEN,POLICY_MILP)}
files={'demo_partition_abs.onnx':base64.b64encode(BLOB).decode(),
       'demo_dense_neural_violation.onnx':base64.b64encode(DENSE).decode(),
       'demo_hidden_spike.onnx':base64.b64encode(HIDDEN).decode()}

from studio.adversarial_campaign import run_campaign
campaign=run_campaign()
mock='''
const fileData=MOCK_FILES;
const reports=MOCK_REPORTS;
const campaign=MOCK_CAMPAIGN;
window.fetch=async (url,opts={})=>{
 const name=String(url).split('/').pop();
 if(String(url).startsWith('/api/sample/')){
   const b64=fileData[name];if(!b64)return {ok:false,status:404,json:async()=>({detail:'not found'})};
   const raw=atob(b64);const bytes=Uint8Array.from(raw,c=>c.charCodeAt(0));
   return {ok:true,status:200,blob:async()=>new Blob([bytes])};
 }
 if(url==='/api/attack-campaign')return {ok:true,status:200,json:async()=>campaign};
 if(url==='/api/status')return {ok:true,json:async()=>({ok:true,version:'0.5.0',onnx_checker_version:null})};
 if(url==='/api/analyze'){
   const filename=decodeURIComponent(opts.headers['X-PCS-Filename']);
   if(!reports[filename])return {ok:false,status:400,json:async()=>({detail:'unknown fixture'})};
   return {ok:true,status:200,json:async()=>reports[filename]};
 }
 return {ok:false,status:404,json:async()=>({detail:'not mocked'})};
};
'''.replace('MOCK_FILES',json.dumps(files)).replace('MOCK_REPORTS',json.dumps(reports)).replace('MOCK_CAMPAIGN',json.dumps(campaign))

def main():
    html=(ROOT/'studio/index.html').read_text().replace('<script src="/app.js" defer></script>','')
    js=(ROOT/'studio/app.js').read_text()
    with sync_playwright() as playwright:
        browser=playwright.chromium.launch(headless=True,executable_path='/usr/bin/chromium',
                                          args=['--no-sandbox','--disable-dev-shm-usage'])
        page=browser.new_page(viewport={'width':1440,'height':990},device_scale_factor=1)
        errors=[]
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.set_content(html,wait_until='load')
        page.add_script_tag(content=mock)
        page.add_script_tag(content=js)
        page.click('#partition-demo')
        page.get_by_text('Conditional real bound: finite-cover certificate').wait_for(timeout=15000)
        assert '2 exact input regions checked' in page.locator('#reports').inner_text()
        page.screenshot(path='/mnt/data/PCS_Model_Assurance_Studio_v0_5_Proof_Preview.png',full_page=True)
        print('PASS: partition proof UI, download affordance, actual analysis body (mock transport)')
        page.locator('#torch').check()
        page.click('#dense-demo')
        page.get_by_text('Independent PyTorch CPU reference').wait_for(timeout=15000)
        assert 'VIOLATION_REPRODUCED' in page.locator('#reports').inner_text()
        page.screenshot(path='/mnt/data/PCS_Model_Assurance_Studio_v0_5_Differential_Preview.png',full_page=True)
        print('PASS: second runtime panel, actual analysis body (mock transport)')
        page.click('#milp-demo')
        page.get_by_text('MILP challenge: interior counterexample search').wait_for(timeout=15000)
        assert '1.199960708618164' in page.locator('#reports').inner_text()
        page.screenshot(path='/mnt/data/PCS_Model_Assurance_Studio_v0_5_Hidden_Failure_Preview.png',full_page=True)
        print('PASS: solver-guided hidden failure panel, real analysis (mock transport)')
        page.click('#attack-demo')
        page.get_by_text('Host-side synthetic metamorphic challenge').wait_for(timeout=15000)
        assert '64/64' in page.locator('#guarded-results').inner_text()
        print('PASS: guard campaign button 64/64 (mock transport)')
        print('PAGE_ERRORS',errors)
        assert not errors
        browser.close()

if __name__=='__main__':main()
