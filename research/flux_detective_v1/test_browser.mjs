import {test, before, after} from 'node:test';
import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {readFile, mkdir} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import {join} from 'node:path';
import {chromium} from 'playwright';
import {puzzle, exportCase} from './engine.mjs';
const root = fileURLToPath(new URL('.', import.meta.url));
let server, browser, base;
before(async () => {
  const allowed = {'/':'text/html', '/index.html':'text/html', '/style.css':'text/css', '/engine.mjs':'text/javascript', '/app.mjs':'text/javascript', '/README.md':'text/plain'};
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
