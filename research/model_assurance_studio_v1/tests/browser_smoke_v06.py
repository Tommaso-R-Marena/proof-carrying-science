"""Chromium UI regression with genuine v0.6 assessment JSON, mocked HTTP transport.

Browser-to-live-server navigation is NOT established by this test.
"""
import base64
import json
from pathlib import Path
from playwright.sync_api import sync_playwright
from studio.engine import analyze
from studio.model_update import compare
ROOT=Path(__file__).resolve().parents[1]
iris=json.loads((ROOT/'validation/v06_iris_profile.json').read_text())
inputs={name:(ROOT/'samples'/name).read_bytes() for name in
        ['demo_relational_margin.onnx','demo_activation_identity.onnx','demo_trained_iris_mlp.onnx','demo_trained_iris_updated.onnx']}
policies={
 'demo_relational_margin.onnx':{'enable_relational_certificate':True,'relational_coefficients':['-1','1'],
                                 'relational_upper_limit':'-1/4'},
 'demo_activation_identity.onnx':{'enable_relational_certificate':True,'enable_activation_case_cover':True,
                                  'relational_coefficients':['1'],'relational_upper_limit':'0'},
 'demo_trained_iris_mlp.onnx':{'enable_relational_certificate':True,'relational_coefficients':iris['properties'][0]['output_coefficients'],
                               'relational_upper_limit':iris['properties'][0]['upper_limit'],
                               'relational_input_box':iris['reviewer_box']},
}
reports={name:analyze(name,raw,policies[name]) for name,raw in inputs.items() if name in policies}
update_report=compare(inputs['demo_trained_iris_mlp.onnx'],inputs['demo_trained_iris_updated.onnx'],
  {'input_box':iris['reviewer_box'],'output_coefficients':['-1','1','0'],
   'baseline_upper_limit':'-1/2','drift_upper_limit':'1/8','required_new_upper_limit':'-3/8'})
assert all('relational_proof' in x['details'] for x in reports.values())
mock='''
const files=MODEL_BYTES, reports=REPORTS, iris=PROFILE, update=UPDATE_REPORT;
window.fetch=async (url, opts={})=>{
  if(url==='/api/status')return {ok:true,json:async()=>({ok:true,version:'0.6.0',onnx_checker_version:null})};
  if(url==='/api/iris-demo-profile')return {ok:true,json:async()=>iris};
  if(url==='/api/compare-update')return {ok:true,json:async()=>update};
  if(url.startsWith('/api/sample/')){
    const name=url.split('/').pop();const b64=files[name];
    if(!b64)return {ok:false,status:404};
    const arr=Uint8Array.from(atob(b64),c=>c.charCodeAt(0));
    return {ok:true,blob:async()=>new Blob([arr])};
  }
  if(url==='/api/analyze'){
    const name=decodeURIComponent(opts.headers['X-PCS-Filename']);
    if(!reports[name])return {ok:false,status:404,json:async()=>({detail:'missing fixture'})};
    return {ok:true,json:async()=>reports[name]};
  }
  return {ok:false,status:404,json:async()=>({detail:'missing fixture'})};
}
'''.replace('MODEL_BYTES',json.dumps({k:base64.b64encode(v).decode() for k,v in inputs.items()})).replace('REPORTS',json.dumps(reports)).replace('PROFILE',json.dumps(iris)).replace('UPDATE_REPORT',json.dumps(update_report))

def main():
    html=(ROOT/'studio/index.html').read_text().replace('<script src="/app.js" defer></script>','')
    js=(ROOT/'studio/app.js').read_text()
    with sync_playwright() as pl:
        br=pl.chromium.launch(headless=True,executable_path='/usr/bin/chromium',
                              args=['--no-sandbox','--disable-dev-shm-usage'])
        page=br.new_page(viewport={'width':1530,'height':920},device_scale_factor=1)
        errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        page.set_content(html,wait_until='load');page.add_script_tag(content=mock);page.add_script_tag(content=js)
        page.click('#relational-demo');page.get_by_text('Independent neural invariant certificate: VERIFIED').wait_for(timeout=12000)
        assert page.get_by_text('Download exact rational proof').count()==1
        page.screenshot(path='/mnt/data/PCS_Model_Assurance_Studio_v0_6_Relational_Preview.png',full_page=True)
        print('PASS relational')
        page.click('#activation-demo');page.get_by_text('Exhaustive activation-case proof: VERIFIED').wait_for(timeout=12000)
        assert '2 complete activation cases verified' in page.locator('#reports').inner_text()
        page.screenshot(path='/mnt/data/PCS_Model_Assurance_Studio_v0_6_Activation_Preview.png',full_page=True)
        print('PASS activation')
        page.click('#iris-demo');page.get_by_text('Independent neural invariant certificate: VERIFIED').wait_for(timeout=12000)
        assert page.locator('#per-feature-box').input_value().startswith('[[')
        assert 'nonzero_multipliers' in page.locator('#reports').inner_text()
        page.screenshot(path='/mnt/data/PCS_Model_Assurance_Studio_v0_6_Iris_Preview.png',full_page=True)
        print('PASS trained iris')
        page.click('#update-demo');page.get_by_text('Proof-gated model update: CONDITIONAL ACCEPTANCE').wait_for(timeout=12000)
        assert '-3/8' in page.locator('#update-results').inner_text()
        page.screenshot(path='/mnt/data/PCS_Model_Assurance_Studio_v0_6_Update_Preview.png',full_page=True)
        print('PASS proof-gated model-update UI')
        print('errors',errors)
        assert not errors,errors
        br.close()
if __name__=='__main__':main()
