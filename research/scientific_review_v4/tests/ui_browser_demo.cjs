/* Actual Firefox automation. Requires an authored fixture generated immediately
 * before this run; no historical browser evidence is consumed. */
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const crypto = require('node:crypto');
const assert = require('node:assert/strict');
const {firefox} = require(process.env.PCS_PLAYWRIGHT_MODULE || '/workspace/.onboarding/tools/browser/node_modules/playwright');

async function main() {
  const demo = path.resolve(process.argv[2]);
  const output = path.resolve(process.argv[3]);
  fs.mkdirSync(output, {recursive:true});
  const manifest = JSON.parse(fs.readFileSync(path.join(demo, 'demo-manifest.json')));
  assert.equal(manifest.fresh_lean_status, 'KERNEL_CHECKED_ABSTRACT_PARTIAL_SEMANTICS');
  const requests = [], errors = [], externalRequests = [];
  const server = http.createServer((request, response) => {
    requests.push(request.url);
    const name = request.url === '/' ? 'review.html' : request.url.slice(1);
    if (name !== 'review.html' && name !== manifest.download_path && !/^parent\/intake\/objects\/[a-f0-9]{64}$/.test(name)) {
      response.writeHead(404); response.end(); return;
    }
    const file = path.join(demo, name);
    if (!fs.existsSync(file)) {response.writeHead(404); response.end(); return;}
    const raw = fs.readFileSync(file), source = name !== 'review.html';
    response.writeHead(200, {'Content-Type':source ? 'application/octet-stream' : 'text/html; charset=utf-8',
      'Content-Length':raw.length, 'X-Content-Type-Options':'nosniff', 'Cache-Control':'no-store',
      ...(source ? {'Content-Disposition':'attachment; filename="captured-source.bin"'} : {})});
    response.end(raw);
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const origin = `http://127.0.0.1:${server.address().port}`;
  let browser;
  const result = {schema:'pcs-scientific-review-actual-browser-v4',
    started_at_utc:new Date().toISOString(), authored_walkthrough:true, human_usability_study:false,
    heldout_data_read:false, fresh_lean_status:manifest.fresh_lean_status,
    check_statuses:manifest.check_statuses, review_sha256:manifest.review_sha256,
    renderer_sha256:crypto.createHash('sha256').update(fs.readFileSync(path.join(__dirname, '..', 'review.py'))).digest('hex'),
    fixture_generator_sha256:crypto.createHash('sha256').update(fs.readFileSync(path.join(__dirname, 'ui_demo_fixture.py'))).digest('hex'),
    browser_harness_sha256:crypto.createHash('sha256').update(fs.readFileSync(__filename)).digest('hex'), checks:{}};
  try {
    browser = await firefox.launch({headless:true, executablePath:process.env.PCS_FIREFOX || '/workspace/.onboarding/cache/ms-playwright/firefox-1555/firefox/firefox'});
    const context = await browser.newContext({acceptDownloads:true, viewport:{width:1440,height:1040}});
    await context.route('**/*', route => {
      if (!route.request().url().startsWith(origin + '/')) {externalRequests.push(route.request().url()); return route.abort();}
      return route.continue();
    });
    const page = await context.newPage();
    page.on('pageerror', error => errors.push(String(error)));
    await page.goto(origin + '/', {waitUntil:'networkidle'});
    assert.equal(await page.locator('script').count(), 0);
    assert.equal(await page.locator('img,iframe,object,link').count(), 0);
    assert.equal(await page.evaluate(() => window.PCS_INJECTED), undefined);
    result.checks.injection_is_inert = true;
    assert(await page.locator('body').textContent().then(t => t.includes('<script>window.PCS_INJECTED=true</script>')));
    const categories = await page.locator('[data-evidence-class]').evaluateAll(elements => elements.map(e => e.dataset.evidenceClass));
    assert.deepEqual(categories, ['proof','computation','source','refuted','unknown']);
    for (const category of categories) assert((await page.locator(`[data-evidence-class="${category}"] .check`).count()) > 0);
    result.checks.five_evidence_classes = categories;
    assert(await page.locator('header').innerText().then(t => t.includes('No scientific conclusions are certified')));
    const headings = await page.locator('h2').allTextContents();
    assert.equal(headings[0], 'Contradictions and open questions');
    result.checks.questions_first = true;
    await page.keyboard.press('Tab');
    assert.equal(await page.evaluate(() => document.activeElement.className), 'skip');
    await page.keyboard.press('Enter');
    assert(page.url().endsWith('#questions'));
    result.checks.keyboard_skip_link = true;
    const source = page.locator('.claim .source-detail').first();
    const sourceSummary = source.locator('summary');
    let sourceTabs = 0;
    while (!(await sourceSummary.evaluate(element => element === document.activeElement)) && sourceTabs < 80) {
      await page.keyboard.press('Tab');
      sourceTabs++;
    }
    assert(await sourceSummary.evaluate(element => element === document.activeElement), 'Source disclosure must be reachable by Tab.');
    await page.keyboard.press('Enter');
    assert(await source.getAttribute('open') !== null);
    assert(await source.locator('.source-quote').isVisible());
    result.checks.keyboard_source_disclosure = {reachable_by_tab:true, tab_presses:sourceTabs, enter_opens:true};
    const link = source.locator('a.source-download');
    const href = await link.getAttribute('href');
    assert.equal(href, manifest.download_path);
    await page.keyboard.press('Tab');
    assert(await link.evaluate(element => element === document.activeElement), 'Original download follows its disclosure in keyboard order.');
    const downloading = page.waitForEvent('download');
    await page.keyboard.press('Enter');
    const download = await downloading;
    assert.equal(await download.failure(), null);
    const downloaded = fs.readFileSync(await download.path());
    const sha = crypto.createHash('sha256').update(downloaded).digest('hex');
    assert.equal(sha, manifest.download_sha256);
    result.checks.original_download = {sha256:sha, bytes:downloaded.length, keyboard_activated:true, href};
    await page.evaluate(() => window.scrollTo(0,0));
    await page.screenshot({path:path.join(output, 'ui-desktop.png'), fullPage:false});
    await page.locator('[data-evidence-class="proof"]').scrollIntoViewIfNeeded();
    await page.screenshot({path:path.join(output, 'ui-evidence-classes.png'), fullPage:false});
    result.checks.viewports = [];
    await page.locator('details').evaluateAll(elements => elements.forEach(element => element.open = true));
    for (const width of [390, 768, 1440]) {
      await page.setViewportSize({width,height:1040});
      await page.evaluate(() => window.scrollTo(0,0));
      const dimensions = await page.evaluate(() => ({viewport:innerWidth, body:document.body.scrollWidth, document:document.documentElement.scrollWidth}));
      assert(dimensions.body <= width && dimensions.document <= width, JSON.stringify(dimensions));
      result.checks.viewports.push({...dimensions, all_disclosures_open:true, horizontal_overflow:false});
      if (width === 390) await page.screenshot({path:path.join(output, 'ui-mobile.png'), fullPage:false});
    }
    assert.deepEqual(externalRequests, []);
    assert.deepEqual(errors, []);
    result.checks.external_network_requests = externalRequests;
    result.checks.page_errors = errors;
    result.checks.script_free = true;
    result.requests = requests;
    result.browser = {name:'Firefox', version:browser.version(), headless:true};
    result.status = 'PASSED';
  } finally {
    if (browser) await browser.close();
    await new Promise(resolve => server.close(resolve));
  }
  result.finished_at_utc = new Date().toISOString();
  fs.writeFileSync(path.join(output, 'ui-browser-results.json'), JSON.stringify(result, null, 2) + '\n');
  console.log(JSON.stringify(result, null, 2));
}
main().catch(error => {console.error(error); process.exitCode=1;});
