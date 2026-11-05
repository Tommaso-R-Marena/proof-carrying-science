"""Chromium visual regression using genuine backend output, mocked HTTP transport."""
import json,base64
from pathlib import Path
from playwright.sync_api import sync_playwright
from studio.model_update import compare
from studio.fp32_lift_v07 import lift_update
ROOT=Path(__file__).resolve().parents[1]
names=['demo_trained_iris_mlp.onnx','demo_trained_iris_updated.onnx']
files={n:(ROOT/'samples'/n).read_bytes() for n in names}
p=json.loads((ROOT/'validation/v06_iris_profile.json').read_text())
real=compare(files[names[0]],files[names[1]],{'input_box':p['reviewer_box'],'output_coefficients':['-1','1','0'],
                  'baseline_upper_limit':'-1/2','drift_upper_limit':'1/8','required_new_upper_limit':'-3/8'})
assert real['status']=='PROVED_CONDITIONALLY'
fp32=lift_update(files[names[0]],files[names[1]],real['baseline']['certificate'],real['baseline_reviewer_policy'],
                 real['update']['certificate'],real['update_reviewer_policy'],'-37/100')
assert fp32['status']=='PROVED_CONDITIONALLY'
response={'exact_real':real,'binary32_lift':fp32,'lean_kernel_verification':'NOT_ESTABLISHED','runtime_equivalence':'NOT_ESTABLISHED'}
mock='''
const files = FILES;const report=REPORT;const profile=PROFILE;
window.fetch=async (url,opts={})=>{
 if(url==='/api/status')return {ok:true,json:async()=>({ok:true,version:'0.7.0',onnx_checker_version:null})};
 if(url==='/api/iris-demo-profile')return {ok:true,json:async()=>profile};
 if(url==='/api/compare-update-fp32')return {ok:true,json:async()=>report};
 if(url.startsWith('/api/sample/')){
  const n=url.split('/').pop(),s=files[n];
  if(!s)return {ok:false,status:404};
  return {ok:true,blob:async()=>new Blob([Uint8Array.from(atob(s),c=>c.charCodeAt(0))])};
 }
 return {ok:false,status:404,json:async()=>({detail:'No mock'})};
};
'''.replace('FILES',json.dumps({n:base64.b64encode(b).decode() for n,b in files.items()})).replace('REPORT',json.dumps(response)).replace('PROFILE',json.dumps(p))

def main():
    html=(ROOT/'studio/index.html').read_text().replace('<script src="/app.js" defer></script>','')
    js=(ROOT/'studio/app.js').read_text()
    with sync_playwright() as pl:
        browser=pl.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox','--disable-dev-shm-usage'])
        page=browser.new_page(viewport={'width':1540,'height':970},device_scale_factor=1)
        errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        page.set_content(html,wait_until='load');page.add_script_tag(content=mock);page.add_script_tag(content=js)
        page.click('#fp32-update-demo')
        page.get_by_text('Model update and rounding budget: CONDITIONAL PROOF').wait_for(timeout=15000)
        text=page.locator('#fp32-results').inner_text()
        assert 'Download FP32 proof-gated update evidence' in text
        assert '-37/100' in text
        assert 'NOT_ESTABLISHED' in text
        page.screenshot(path='/mnt/data/PCS_Model_Assurance_Studio_v0_7_FP32_Update_Preview.png',full_page=True)
        page.click('#fp32-update-selected')
        page.get_by_text('Model update and rounding budget: CONDITIONAL PROOF').wait_for(timeout=15000)
        assert not errors,errors
        print('PASS Chromium FP32 update demo and selected pair; JS errors:',errors)
        browser.close()

if __name__=='__main__':main()
