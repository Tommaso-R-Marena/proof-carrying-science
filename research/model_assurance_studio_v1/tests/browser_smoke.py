"""Offline Chromium DOM smoke test using actual engine-produced receipts.

This execution environment blocks Chromium HTTP navigation. The test loads the
actual HTML/JS via Playwright in about:blank and injects *real analysis reports*
into the UI state. It covers rendering and JS errors, not browser-to-server HTTP.
HTTP API is independently covered with TestClient integration tests.
"""
from pathlib import Path
from playwright.sync_api import sync_playwright
from studio.engine import analyze

ROOT=Path(__file__).resolve().parents[1]

def main():
    model=(ROOT/'samples/demo_relu_violation.onnx').read_bytes()
    model_report=analyze('demo_relu_violation.onnx',model,{
        'check_output_bounds':True,'output_min':0,'output_max':.5,'enable_reference_replay':True})
    attack=(ROOT/'samples/demo_agent_attack_blocked.agenttrace.json').read_bytes()
    agent_report=analyze('demo_agent_attack_blocked.agenttrace.json',attack)
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox','--disable-dev-shm-usage'])
        page=browser.new_page(viewport={'width':1440,'height':1000},device_scale_factor=1)
        errors=[]
        page.on('pageerror',lambda exc: errors.append(str(exc)))
        html=(ROOT/'studio/index.html').read_text().replace('<script src="/app.js" defer></script>','')
        page.set_content(html,wait_until='load')
        page.add_script_tag(content=(ROOT/'studio/app.js').read_text())
        page.evaluate('(reports)=>{state.reports=reports;renderReports();}',[model_report])
        assert page.get_by_text('Float32 numerical violation reproduced (scoped)').count()==1
        assert page.get_by_text('Output policy violated in NumPy float32 scalar replay').count()==1
        page.screenshot(path='/mnt/data/PCS_Model_Assurance_Studio_v0_3_Preview.png',full_page=True)
        page.evaluate('(reports)=>{state.reports=reports;renderReports();}',[agent_report])
        assert page.get_by_text('Tool-use agent policy evaluation (synthetic)').count()==1
        assert page.get_by_text('Policy evaluation of proposed tool actions').count()==1
        page.screenshot(path='/mnt/data/PCS_Model_Assurance_Studio_v0_3_Agent_Gate_Preview.png',full_page=True)
        assert not errors,'JavaScript errors: '+repr(errors)
        print('PASS: Chromium rendered actual ONNX and agent-gate assessments; no JS exceptions. HTTP transport not exercised.')
        browser.close()
if __name__=='__main__':main()
