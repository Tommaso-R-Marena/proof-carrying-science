"""Optional actual-browser check of the passive two-profile comparison page."""
import argparse,json
from pathlib import Path


def main():
    p=argparse.ArgumentParser();p.add_argument('index',type=Path);p.add_argument('output',type=Path);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    from playwright.sync_api import sync_playwright
    requests=[];dialogs=[];rows=[]
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True)
        try:
            for width,label in ((1280,'desktop'),(390,'mobile')):
                page=browser.new_page(viewport=dict(width=width,height=900))
                page.on('request',lambda r:requests.append(r.url) if r.url.startswith(('http:','https:')) else None)
                page.on('dialog',lambda d:(dialogs.append(d.message),d.dismiss()))
                page.goto(a.index.resolve().as_uri())
                assert page.title()=='PCS · Action Format Experiment'
                assert not page.evaluate('document.documentElement.scrollWidth > innerWidth + 1')
                assert page.locator('script,img,iframe,form').count()==0
                for mode in ('raw','trie'):
                    link=page.locator(f'a[href="{mode}/report.html"]');assert link.count()==1
                    link.focus()
                    with page.expect_navigation(wait_until='load'):page.keyboard.press('Enter')
                    assert page.title()=='PCS · Local Agent Lab' and page.locator('.case').count()==16
                    page.go_back(wait_until='load');assert page.title()=='PCS · Action Format Experiment'
                page.screenshot(path=str(a.output/(label+'.png')),full_page=True)
                rows.append(dict(width=width,no_horizontal_overflow=True,keyboard_profile_navigation=True,active_content=False));page.close()
        finally:browser.close()
    assert not requests and not dialogs
    result=dict(findings=rows,external_requests=requests,dialogs=dialogs,scope='Browser smoke, not a human study or complete accessibility certification')
    (a.output/'checks.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))


if __name__=='__main__':main()
