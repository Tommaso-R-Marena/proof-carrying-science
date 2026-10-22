import {test, before, after} from 'node:test';
import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {readFile, mkdir} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import {join} from 'node:path';
import {createHash} from 'node:crypto';
import {spawn} from 'node:child_process';
import {chromium} from 'playwright';
import {puzzle, exportCase} from './engine.mjs';
import {forgeCase,regionFor,sliderAmount} from './forge.mjs';
const root = fileURLToPath(new URL('.', import.meta.url));
let server, browser, base;
before(async () => {
  const allowed = {'/':'text/html', '/index.html':'text/html', '/style.css':'text/css', '/engine.mjs':'text/javascript', '/forge.mjs':'text/javascript', '/app.mjs':'text/javascript', '/inspector.mjs':'text/javascript', '/inspector-ui.mjs':'text/javascript', '/inspector-worker.mjs':'text/javascript', '/README.md':'text/plain'};
  server = createServer(async (req, res) => {
    if (!Object.hasOwn(allowed, req.url)) { res.writeHead(404).end(); return; }
    try { res.writeHead(200, {'Content-Type':allowed[req.url]}); res.end(await readFile(join(root, req.url === '/' ? 'index.html' : req.url.slice(1)))); }
    catch { res.writeHead(500).end(); }
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  base = `http://127.0.0.1:${server.address().port}`;
  browser = await chromium.launch({headless:true, ...(process.env.PCS_CHROMIUM ? {executablePath:process.env.PCS_CHROMIUM} : {})});
});
after(async () => { await browser?.close(); await new Promise(resolve => server?.close(resolve)); });
async function capture(page, name) {
  if (!process.env.PCS_FLUX_SCREENSHOTS) return;
  await mkdir(process.env.PCS_FLUX_SCREENSHOTS, {recursive:true});
  await page.screenshot({path:join(process.env.PCS_FLUX_SCREENSHOTS, name), fullPage:true});
}
test('desktop plays all six cases; mistakes, hints, stars and final state work', async () => {
  const page = await browser.newPage({viewport:{width:1440, height:1000}}), errors = [];
  page.on('pageerror', e => errors.push(e.message));
  await page.goto(base); await page.locator('.candidate').last().waitFor();
  await capture(page, 'desktop-initial.png');
  for (let level = 0; level < 6; level++) {
    const p = puzzle(20261021, level), good = p.candidates.findIndex(c => !c.analysis.fault), wrong = (good+1)%3;
    assert.equal(await page.locator('#progress').textContent(), `Case ${level+1} of 6`);
    if (level === 0) {
      await page.locator('.choose').nth(wrong).click(); assert.ok(await page.locator('.choose').nth(wrong).isDisabled());
      await page.locator('#hint').click(); assert.equal(await page.locator('.residual').count(), 3);
      assert.match(await page.locator('#feedback').textContent(), /observed/);
      await capture(page, 'desktop-residuals.png');
    }
    await page.locator('.choose').nth(good).focus(); await page.keyboard.press('Enter');
    assert.equal(await page.locator('.candidate.correct').count(), 1);
    if (level < 5) await page.locator('#next').click();
  }
  assert.equal(await page.locator('#score').textContent(), '16 / 18 stars');
  assert.match(await page.locator('#feedback').textContent(), /Campaign complete/);
  assert.ok(await page.locator('#next').isHidden()); assert.ok(await page.locator('#hint').isDisabled());
  assert.deepEqual(errors, []); await page.close();
});
test('download contains exactly the visible export and no verdict', async () => {
  const page = await browser.newPage(); await page.goto(base+'/#seed=0');
  const download = page.waitForEvent('download'); await page.locator('.download').first().click();
  const file = await download; const stream = await file.createReadStream(); let text = '';
  for await (const chunk of stream) text += chunk;
  assert.deepEqual(JSON.parse(text), exportCase(puzzle(0, 0), 0));
  assert.equal(file.suggestedFilename(), 'flux-0-level-1-trace-1.json'); await page.close();
});
test('mobile layout, invalid seeds, maximum seed and campaign reset', async () => {
  const page = await browser.newPage({viewport:{width:390, height:844}}), errors = [];
  page.on('pageerror', e => errors.push(e.message));
  await page.goto(base+'/#seed=4294967295'); await page.locator('.candidate').last().waitFor();
  assert.equal(await page.locator('#seed').inputValue(), '4294967295');
  assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
  await capture(page, 'mobile-initial.png');
  await page.locator('#seed').fill('-1'); await page.locator('#seed-form button').click();
  assert.match(await page.locator('#error').textContent(), /Seed must/);
  await page.locator('#seed').fill('0'); await page.locator('#seed-form button').click();
  assert.equal(await page.locator('#progress').textContent(), 'Case 1 of 6');
  assert.equal(await page.locator('#score').textContent(), '0 / 18 stars');
  assert.equal(await page.locator('#error').textContent(), ''); assert.equal(new URL(page.url()).hash, '#seed=0');
  assert.deepEqual(errors, []); await page.close();
});
test('workshop builds and downloads a counterexample without changing the puzzle score', async()=>{
  const page=await browser.newPage();await page.goto(base);await page.locator('#forge-half').click();
  assert.match(await page.locator('#forge-status').textContent(),/Impostor constructed/);
  const p=puzzle(20261021,0), amount=sliderAmount(regionFor(p,0,1),50);
  assert.equal(await page.locator('#forge-amount').inputValue(),amount);
  const download=page.waitForEvent('download');await page.locator('#forge-export').click();
  const file=await download, stream=await file.createReadStream();let raw='';for await(const chunk of stream) raw+=chunk;
  assert.deepEqual(JSON.parse(raw),forgeCase(p,0,1,amount).bundle);
  assert.equal(await page.locator('#score').textContent(),'0 / 18 stars');
  await page.locator('#forge-reset').click();assert.match(await page.locator('#forge-status').textContent(),/Exact model restored/);
  await page.close();
});
test('mobile workshop fails closed on bad input and handles zero-width intervals', async()=>{
  const page=await browser.newPage({viewport:{width:390,height:844}}), errors=[];
  page.on('pageerror',e=>errors.push(e.message));await page.goto(base);
  await page.locator('#forge-right').selectOption('0');assert.ok(await page.locator('#forge-export').isDisabled());
  assert.match(await page.locator('#forge-error').textContent(),/different/);
  await page.locator('#forge-right').selectOption('1');
  await page.locator('#forge-amount').fill('2/4');await page.locator('#forge-form button').click();
  assert.ok(await page.locator('#forge-export').isDisabled());assert.match(await page.locator('#forge-error').textContent(),/Canonical/);
  await page.locator('#forge-reset').click();
  await page.locator('#forge-amount').fill('1000');await page.locator('#forge-form button').click();
  assert.match(await page.locator('#forge-details').textContent(),/Bounds FAIL/);
  for(let level=0;level<3;level++) {
    const p=puzzle(20261021,level);await page.locator('.choose').nth(p.candidates.findIndex(c=>!c.analysis.fault)).click();await page.locator('#next').click();
  }
  await page.locator('#forge-left').selectOption('3');await page.locator('#forge-right').selectOption('4');
  assert.ok(await page.locator('#forge-slider').isDisabled());assert.match(await page.locator('#forge-details').textContent(),/Only zero/);
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  await capture(page,'mobile-zero-width-workshop.png');
  await page.locator('#forge-left').selectOption('0');await page.locator('#forge-right').selectOption('1');await page.locator('#forge-half').click();
  assert.match(await page.locator('#forge-status').textContent(),/Impostor constructed/);
  await capture(page,'mobile-workshop.png');assert.deepEqual(errors,[]);await page.close();
});
test('one-click workshop inspection keeps browser and Lean verdicts separate and captures exact bytes',async()=>{
  const page=await browser.newPage();await page.goto(base);await page.locator('#forge-half').click();await page.locator('#forge-inspect').click();
  await page.waitForFunction(()=>document.getElementById('inspect-status').textContent.includes('exact model mismatch'));
  assert.match(await page.locator('#inspect-status').textContent(),/Lean has not run/);
  assert.match(await page.locator('#inspect-result').textContent(),/Mass PASS/);assert.equal(await page.locator('#inspect-result meter').count(),2);
  const p=puzzle(20261021,0),r=regionFor(p,0,1),raw=JSON.stringify(forgeCase(p,0,1,sliderAmount(r,50)).bundle,null,2)+'\n';
  assert.match(await page.locator('#inspect-digest').textContent(),new RegExp(createHash('sha256').update(raw).digest('hex')));
  const pending=page.waitForEvent('download');await page.locator('#inspect-download').click();const file=await pending,stream=await file.createReadStream();let captured='';for await(const part of stream)captured+=part;
  assert.equal(captured,raw);assert.equal(file.suggestedFilename(),'inspected-case.json');
  await page.locator('#inspect-copy').click();await page.waitForFunction(()=>/copied|Clipboard unavailable/.test(document.getElementById('inspect-copy-status').textContent));
  await capture(page,'desktop-case-inspector.png');await page.close();
});
test('file import, malformed UTF-8 and oversized files clear prior usable results',async()=>{
  const page=await browser.newPage({viewport:{width:390,height:844}});await page.goto(base);
  const p=puzzle(0,0),b=exportCase(p,p.candidates.findIndex(c=>!c.analysis.fault));b.contract.question='<img src=x onerror=alert(1)>';
  await page.locator('#inspect-file').setInputFiles({name:'untrusted-name.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(b))});
  await page.waitForFunction(()=>document.getElementById('inspect-status').textContent.includes('matches the declared model'));
  assert.ok(await page.locator('#inspect-download').isEnabled());assert.equal(await page.locator('#inspect-result img').count(),0);
  for(const buffer of [Buffer.from('{"x":1,"x":2}'),Buffer.from([255]),Buffer.alloc(256*1024+1,32)]){
    await page.locator('#inspect-file').setInputFiles({name:'bad.json',mimeType:'application/json',buffer});
    await page.waitForFunction(()=>document.getElementById('inspect-error').textContent.length>0);
    assert.ok(await page.locator('#inspect-download').isDisabled());assert.equal(await page.locator('#inspect-result').textContent(),'');
  }
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await page.close();
});
test('a superseded delayed worker cannot replace the newest captured input',async()=>{
  const page=await browser.newPage();let seen=0,firstResolve;const firstRequested=new Promise(resolve=>{firstResolve=resolve;});
  await page.route('**/inspector-worker.mjs',async route=>{
    if(++seen!==1){await route.continue();return;}
    firstResolve();await route.fulfill({contentType:'text/javascript',body:"import {inspectCase} from './inspector.mjs';self.onmessage=e=>setTimeout(()=>self.postMessage({id:e.data.id,result:inspectCase(e.data.raw)}),600);"});
  });
  await page.goto(base);const p=puzzle(0,0),good=JSON.stringify(exportCase(p,p.candidates.findIndex(c=>!c.analysis.fault))),bad=JSON.stringify(forgeCase(p,0,1,'1/64').bundle);
  await page.locator('#inspect-file').setInputFiles({name:'first.json',mimeType:'application/json',buffer:Buffer.from(good)});await firstRequested;
  await page.locator('#inspect-file').setInputFiles({name:'second.json',mimeType:'application/json',buffer:Buffer.from(bad)});
  await page.waitForFunction(()=>document.getElementById('inspect-status').textContent.includes('exact model mismatch'));
  await page.waitForTimeout(800);assert.match(await page.locator('#inspect-digest').textContent(),new RegExp(createHash('sha256').update(bad).digest('hex')));assert.match(await page.locator('#inspect-status').textContent(),/mismatch/);await page.close();
});
test('unresponsive browser analysis refuses without an affirmative verdict',async()=>{
  const page=await browser.newPage();await page.route('**/inspector-worker.mjs',route=>route.fulfill({contentType:'text/javascript',body:'self.onmessage=()=>{};'}));
  await page.goto(base);const p=puzzle(0,0),b=exportCase(p,0);
  await page.locator('#inspect-file').setInputFiles({name:'case.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(b))});
  await page.waitForFunction(()=>document.getElementById('inspect-error').textContent.includes('budget expired'),{},{timeout:8000});
  assert.ok(await page.locator('#inspect-download').isDisabled());assert.match(await page.locator('#inspect-status').textContent(),/Lean has not run/);await page.close();
});
test('standard-library launcher serves a working worker under its actual CSP',async()=>{
  const child=spawn(process.env.PCS_LAB_PYTHON??'python3',['-S','-m','research.trace_lab_v1','serve','--port','0','--json'],{cwd:fileURLToPath(new URL('../../',import.meta.url)),stdio:['ignore','pipe','pipe']});
  try{
    const metadata=await new Promise((resolve,reject)=>{let raw='';const timer=setTimeout(()=>reject(Error('Launcher did not start')),10000);child.once('error',reject);child.stdout.on('data',data=>{raw+=data;if(raw.includes('\n')){clearTimeout(timer);resolve(JSON.parse(raw.split('\n')[0]));}});});
    assert.equal(metadata.kernel_checked,false);const page=await browser.newPage();await page.goto(metadata.url);await page.locator('#forge-inspect').click();
    await page.waitForFunction(()=>document.getElementById('inspect-status').textContent.includes('matches the declared model'));
    assert.match(await page.locator('#inspect-status').textContent(),/Lean has not run/);await page.close();
  }finally{child.kill('SIGTERM');await new Promise(resolve=>child.once('exit',resolve));}
});
