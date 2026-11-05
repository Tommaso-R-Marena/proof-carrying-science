"""Run the v0.7 binary32 drag/drop presentation in Chromium with a mocked
transport carrying a *genuine backend calculation*; not a live HTTP browser test.
"""
from pathlib import Path
from playwright.sync_api import sync_playwright
import base64
import json
from studio.fp32_assurance import issue,POLICY_SCHEMA,digest

ROOT=Path(__file__).resolve().parents[1]
name='demo_dense_neural_violation.onnx';raw=(ROOT/'samples'/name).read_bytes()
policy=dict(schema=POLICY_SCHEMA,model_sha256=digest(raw),input_box=[['-1','1'],['-1','1']],output_coefficients=['1','0'],upper_limit='5/4')
assessment=issue(raw,policy)
assert assessment['status']=='PROVED_CONDITIONALLY'
real_response={'assessment':assessment,'suggested_reviewer_policy':policy,
               'independent_reviewer_acceptance':'NOT_ESTABLISHED'}
js_mock='''
const raw = Uint8Array.from(atob(MODEL),c=>c.charCodeAt(0));
const real = RESULT;
window.fetch=async (url, opts={})=>{
 if(url==='/api/status') return {ok:true,json:async()=>({ok:true,version:'0.7.0',onnx_checker_version:null})};
 if(url==='/api/sample/demo_dense_neural_violation.onnx') return {ok:true,blob:async()=>new Blob([raw])};
 if(url==='/api/fp32-assure')return {ok:true,json:async()=>real};
 return {ok:false,status:404,json:async()=>({detail:'mocked route not available'})};
};
'''.replace('MODEL',json.dumps(base64.b64encode(raw).decode())).replace('RESULT',json.dumps(real_response))

def main():
    html=(ROOT/'studio/index.html').read_text().replace('<script src="/app.js" defer></script>','')
    js=(ROOT/'studio/app.js').read_text()
    with sync_playwright() as pl:
        browser=pl.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox','--disable-dev-shm-usage'])
        page=browser.new_page(viewport={'width':1550,'height':980},device_scale_factor=1)
        errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        page.set_content(html,wait_until='load')
        page.add_script_tag(content=js_mock);page.add_script_tag(content=js)
        page.click('#fp32-demo')
        page.get_by_text('Sequential binary32 property: CONDITIONAL PROOF').wait_for(timeout=12000)
        assert page.locator('#fp32-results').get_by_text('Download float32 analysis and suggested policy').count()==1
        assert '5/4' in page.locator('#fp32-results').inner_text()
        assert 'NOT_ESTABLISHED' in page.locator('#fp32-results').inner_text()
        page.screenshot(path='/mnt/data/PCS_Model_Assurance_Studio_v0_7_FP32_Preview.png',full_page=True)
        page.click('#fp32-selected')
        page.get_by_text('Sequential binary32 property: CONDITIONAL PROOF').wait_for(timeout=12000)
        assert not errors,errors
        print('PASS browser float32 demo and selected-file controls; page exceptions:',errors)
        browser.close()

if __name__=='__main__':main()
