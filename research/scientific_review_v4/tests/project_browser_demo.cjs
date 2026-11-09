/* Authored browser walkthrough of an actual, complete development-project
 * package. Never performs scientific checking or claims human usability. */
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const crypto = require('node:crypto');
const assert = require('node:assert/strict');
const {firefox} = require(process.env.PCS_PLAYWRIGHT_MODULE || '/workspace/.onboarding/tools/browser/node_modules/playwright');
const sha = bytes => crypto.createHash('sha256').update(bytes).digest('hex');

async function main() {
  const packet = path.resolve(process.argv[2]);
  const output = path.resolve(process.argv[3]);
  fs.mkdirSync(output, {recursive:true});
  const read = name => fs.readFileSync(path.join(packet, name));
  const meaning = JSON.parse(read('interpretation.json'));
  const checks = JSON.parse(read('checks.json'));
  const inventory = JSON.parse(read('parent/intake/inventory.json'));
  const first = meaning.claims[0];
  assert(first && /^[0-9a-f]{64}$/.test(first.source.sha256));
  const result = {
    schema:'pcs-real-project-browser-walkthrough-v4',
    project:'fiedler2016-development', started_at_utc:new Date().toISOString(),
    authored_walkthrough:true, human_usability_study:false, scientific_validation:false,
    heldout_data_read:false, review_sha256:sha(read('review.html')),
    manifest_sha256:sha(read('manifest.json')),
    renderer_sha256:sha(fs.readFileSync(path.join(__dirname, '..', 'review.py'))),
    browser_harness_sha256:sha(fs.readFileSync(__filename)),
    inputs:{artifacts:inventory.artifacts.length, claims:meaning.claims.length,
      checks:checks.length, check_statuses:[...new Set(checks.map(c => c.status))].sort()},
    checks:{}, defects:[]
  };
  const requests = [], external = [], errors = [];
  const server = http.createServer((request,response) => {
    requests.push(request.url);
    const name = request.url === '/' ? 'review.html' : request.url.slice(1);
    if (name !== 'review.html' && !/^parent\/intake\/objects\/[a-f0-9]{64}$/.test(name)) {
      response.writeHead(404);response.end();return;
    }
    const target = path.join(packet,name);
    if (!fs.existsSync(target)) {response.writeHead(404);response.end();return;}
    const bytes = fs.readFileSync(target), download = name !== 'review.html';
    response.writeHead(200, {'Content-Type':download?'application/octet-stream':'text/html; charset=utf-8',
      'Content-Length':bytes.length,'X-Content-Type-Options':'nosniff','Cache-Control':'no-store',
      ...(download?{'Content-Disposition':'attachment; filename="original-project-source.bin"'}:{})});
    response.end(bytes);
  });
  await new Promise(resolve => server.listen(0,'127.0.0.1',resolve));
  const origin = `http://127.0.0.1:${server.address().port}`;
  let browser;
  try {
    browser = await firefox.launch({headless:true,executablePath:process.env.PCS_FIREFOX || '/workspace/.onboarding/cache/ms-playwright/firefox-1555/firefox/firefox'});
    result.browser = {name:'Firefox',version:browser.version(),headless:true};
    const context = await browser.newContext({acceptDownloads:true,viewport:{width:1440,height:1040}});
    await context.route('**/*',route => {
      if (!route.request().url().startsWith(origin+'/')) {external.push(route.request().url());return route.abort();}
      return route.continue();
    });
    const page = await context.newPage();
    page.on('pageerror',e => errors.push(String(e)));
    await page.goto(origin+'/',{waitUntil:'networkidle'});
    assert.equal(await page.locator('script').count(),0);
    assert.equal(await page.locator('img,iframe,object,link').count(),0);
    assert.equal(await page.locator('.claim').count(),meaning.claims.length);
    assert((await page.locator('header').innerText()).includes('No scientific conclusions are certified'));
    assert((await page.locator('header').innerText()).includes(`${inventory.artifacts.length} captured files`));
    assert((await page.locator('header').innerText()).includes(`${checks.length} check records`));
    result.checks.actual_inventory_and_statement_counts = true;
    const categories = await page.locator('[data-evidence-class]').evaluateAll(els=>els.map(el=>el.dataset.evidenceClass));
    assert.deepEqual(categories,['proof','computation','source','refuted','unknown']);
    const counts = {};
    for (const category of categories) counts[category] = await page.locator(`[data-evidence-class="${category}"] .check`).count();
    for (const category of ['proof','computation','source','unknown']) assert(counts[category]>0,`${category} should contain actual development results`);
    assert.equal(Object.values(counts).reduce((a,b)=>a+b,0),checks.length);
    result.checks.evidence_classes = counts;
    result.checks.scope_separation_visible = true;
    const proofText = await page.locator('[data-evidence-class="proof"]').innerText();
    assert(proofText.includes('finite exact integer residuals'));
    const body = await page.locator('body').innerText();
    assert(body.includes('source_assumption'));
    assert(body.includes('pERK'));
    assert(body.includes('scientific') && body.includes('open'));
    result.checks.actual_assumptions_biological_relation_and_abstract_proof_displayed = true;
    assert.equal((await page.locator('h2').allTextContents())[0],'Contradictions and open questions');
    await page.keyboard.press('Tab');
    assert.equal(await page.evaluate(()=>document.activeElement.className),'skip');
    await page.keyboard.press('Enter');
    assert(page.url().endsWith('#questions'));
    result.checks.keyboard_skip_link = true;
    const source = page.locator('.claim .source-detail').first();
    const summary = source.locator('summary');
    let tabs = 0;
    while (!(await summary.evaluate(el=>el===document.activeElement)) && tabs<2000) {await page.keyboard.press('Tab');tabs++;}
    assert(await summary.evaluate(el=>el===document.activeElement));
    await page.keyboard.press('Enter');
    assert(await source.getAttribute('open')!==null);
    assert(await source.locator('.source-quote').isVisible());
    result.checks.keyboard_source_disclosure = {tab_presses:tabs,enter_opens:true};
    if (tabs>40) result.defects.push({kind:'usability_cost',severity:'observation',detail:`The first statement source requires ${tabs} Tab presses from the questions skip target; no direct statement/source skip shortcut was found.`});
    const link = source.locator('a.source-download');
    const href = await link.getAttribute('href');
    assert.equal(href,`parent/intake/objects/${first.source.sha256}`);
    await page.keyboard.press('Tab');
    assert(await link.evaluate(el=>el===document.activeElement));
    const waiting = page.waitForEvent('download');
    await page.keyboard.press('Enter');
    const download = await waiting;
    assert.equal(await download.failure(),null);
    const bytes = fs.readFileSync(await download.path());
    assert.equal(sha(bytes),first.source.sha256);
    assert.deepEqual(bytes,read(href));
    result.checks.original_download = {href,bytes:bytes.length,sha256:sha(bytes),keyboard_activated:true,exact_captured_bytes:true};
    await page.evaluate(()=>window.scrollTo(0,0));
    await page.screenshot({path:path.join(output,'project-ui-desktop.png'),fullPage:false});
    await page.locator('[data-evidence-class="computation"]').scrollIntoViewIfNeeded();
    await page.screenshot({path:path.join(output,'project-ui-evidence.png'),fullPage:false});
    await page.locator('details').evaluateAll(els=>els.forEach(el=>el.open=true));
    result.checks.viewports=[];
    for (const width of [390,768,1440]) {
      await page.setViewportSize({width,height:1040});
      await page.evaluate(()=>window.scrollTo(0,0));
      const dimensions=await page.evaluate(()=>({viewport:innerWidth,body:document.body.scrollWidth,document:document.documentElement.scrollWidth}));
      assert(dimensions.body<=width && dimensions.document<=width,JSON.stringify(dimensions));
      result.checks.viewports.push({...dimensions,all_disclosures_open:true,horizontal_overflow:false});
      if(width===390) await page.screenshot({path:path.join(output,'project-ui-mobile.png'),fullPage:false});
    }
    assert.deepEqual(external,[]);assert.deepEqual(errors,[]);
    result.checks.external_requests=external;result.checks.page_errors=errors;
    result.checks.script_free=true;result.status='PASSED';
  } catch(error) {
    result.status='FAILED';result.defects.push({error:String(error),stack:error.stack});
    process.exitCode=1;
  } finally {
    if(browser) await browser.close();
    await new Promise(resolve=>server.close(resolve));
    result.requests=requests;result.finished_at_utc=new Date().toISOString();
    fs.writeFileSync(path.join(output,'project-ui-results.json'),JSON.stringify(result,null,2)+'\n');
  }
  console.log(JSON.stringify(result,null,2));
}
main().catch(error=>{console.error(error);process.exitCode=1;});
