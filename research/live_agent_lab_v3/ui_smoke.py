"""Optional real-browser smoke check for the generated passive report.

Requires Playwright + its Chromium headless shell; not a proof/a11y certification.
No model or verifier is mocked. Screenshots and findings go to a fresh directory.
"""
import argparse
import json
from pathlib import Path


def main():
    p=argparse.ArgumentParser();p.add_argument("report",type=Path);p.add_argument("output",type=Path)
    args=p.parse_args();args.output.mkdir(parents=True,exist_ok=False)
    from playwright.sync_api import sync_playwright
    requests=[];dialogs=[];findings=[]
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True)
        try:
            for width,label in ((1280,"desktop"),(390,"mobile")):
                page=browser.new_page(viewport=dict(width=width,height=900))
                page.on("request",lambda req:requests.append(req.url) if req.url.startswith(("http:","https:")) else None)
                page.on("dialog",lambda dialog:(dialogs.append(dialog.message),dialog.dismiss()))
                page.goto(args.report.resolve().as_uri())
                assert page.title()=="PCS · Local Agent Lab"
                assert page.locator("h1").count()==1 and page.locator(".case").count()>0
                assert not page.evaluate("document.documentElement.scrollWidth > innerWidth + 1")
                assert page.locator("script,img,iframe,form").count()==0
                assert page.evaluate("typeof window.pcsInjected")=="undefined"
                detail=page.locator(".case details").first
                detail.locator("summary").focus();page.keyboard.press("Enter")
                assert detail.get_attribute("open") is not None
                nav=page.locator("details.case-nav");nav.locator("summary").focus();page.keyboard.press("Enter")
                assert nav.get_attribute("open") is not None and nav.locator("a").count()==page.locator(".case").count()
                page.screenshot(path=str(args.output/(label+".png")),full_page=True)
                findings.append(dict(viewport=width,horizontal_overflow=False,keyboard_disclosure=True,
                                     workflow_navigation=True,active_content=False,visible_cases=page.locator(".case").count()))
                page.close()
        finally:browser.close()
    assert not requests and not dialogs
    result=dict(format="pcs-lab-browser-smoke-v1",findings=findings,external_requests=requests,dialogs=dialogs,
                scope="Local browser smoke; not comprehensive accessibility or human usability validation")
    (args.output/"checks.json").write_text(json.dumps(result,indent=2)+"\n");print(json.dumps(result))


if __name__=="__main__":main()
