"""Offline Chromium event and rendering smoke test using actual API results.

Browser TCP navigation is blocked in this environment. Real backend TestClient
responses are passed to the browser as a mocked fetch transport. Browser event
wiring, file blobs, report panels and JS errors are exercised; live browser HTTP
transport is NOT tested.
"""
from pathlib import Path
from playwright.sync_api import sync_playwright
from fastapi.testclient import TestClient
from studio.server import app
import json,base64
ROOT=Path(__file__).resolve().parents[1]

def main():
    cli=TestClient(app)
    dense=(ROOT/'samples/demo_dense_neural_violation.onnx').read_bytes()
    agent=(ROOT/'samples/demo_agent_attack_blocked.agenttrace.json').read_bytes()
    policy={'check_output_bounds':True,'search_scalar_witness':True,'enable_reference_replay':True,
            'input_min':-1,'input_max':1,'output_min':0,'output_max':1}
    neural=cli.post('/api/analyze',content=dense,headers={'x-pcs-filename':'demo_dense_neural_violation.onnx','x-pcs-policy':__import__('urllib.parse',fromlist=['quote']).quote(json.dumps(policy))})
    assert neural.status_code==200
    guarded=cli.post('/api/guarded-demo',content=agent)
    assert guarded.status_code==200
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox','--disable-dev-shm-usage'])
        page=browser.new_page(viewport={'width':1440,'height':900},device_scale_factor=1)
        errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        html=(ROOT/'studio/index.html').read_text().replace('<script src="/app.js" defer></script>','')
        page.set_content(html,wait_until='load')
        page.evaluate('''(data)=>{const from64=s=>Uint8Array.from(atob(s),x=>x.charCodeAt(0));
          window.fetch=async(url,opts={})=>{
            let p=String(url);
            if(p.includes('demo_dense_neural_violation.onnx'))return new Response(from64(data.dense),{status:200});
            if(p.includes('demo_agent_attack_blocked.agenttrace.json'))return new Response(from64(data.agent),{status:200});
            if(p==='/api/analyze')return new Response(JSON.stringify(data.neural),{status:200,headers:{'content-type':'application/json'}});
            if(p==='/api/guarded-demo')return new Response(JSON.stringify(data.guarded),{status:200,headers:{'content-type':'application/json'}});
            if(p==='/api/status')return new Response(JSON.stringify({ok:true,version:'0.4.0'}),{status:200});
            throw Error('Unexpected UI request '+p);
          };
        }''',{'dense':base64.b64encode(dense).decode(),'agent':base64.b64encode(agent).decode(),
               'neural':neural.json(),'guarded':guarded.json()})
        page.add_script_tag(content=(ROOT/'studio/app.js').read_text())
        page.locator('#dense-demo').click()
        page.get_by_text('Neural-network box assurance (experimental)').wait_for(timeout=20000)
        assert page.get_by_text('Dense neural-network policy violation reproduced by NumPy float32').count()==1
        page.screenshot(path='/mnt/data/PCS_Model_Assurance_Studio_v0_4_Neural_Preview.png',full_page=True)
        page.locator('#guarded-live').click()
        page.get_by_text('Actual pre-dispatch guard — synthetic backend').wait_for(timeout=20000)
        assert page.get_by_text('denied before any effect',exact=False).count()>0
        page.screenshot(path='/mnt/data/PCS_Model_Assurance_Studio_v0_4_Guard_Preview.png',full_page=True)
        assert not errors, errors
        browser.close()
        print('PASS Chromium clicks, file blobs and actual backend response rendering; HTTP transport stubbed. Zero JS exceptions.')
if __name__=='__main__':main()
