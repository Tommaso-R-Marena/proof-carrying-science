import test from 'node:test';
import assert from 'node:assert/strict';
import {Q, parseSeed, puzzle, exportCase, LEVEL_COUNT} from './engine.mjs';

test('canonical rationals normalize signs and zero exactly', () => {
  assert.equal(String(new Q(-6n, -8n)), '3/4'); assert.equal(String(new Q(0n, -7n)), '0');
  for (const s of ['0', '1', '-1', '7/8', '-17/29', '9007199254740993']) assert.equal(String(Q.parse(s)), s);
});
test('ambiguous and noncanonical rational spellings fail closed', () => {
  for (const s of ['', '-0', '01', '+1', '1/01', '2/4', '1/1', '0/7', '1/0', '1/-2', ' 1', '1\n', '١', '1/2/3', '1.0', '1e2', 1, '1'.repeat(97)]) assert.throws(() => Q.parse(s));
  assert.throws(() => new Q(1n, 0n)); assert.throws(() => new Q(1)); assert.throws(() => Q.parse('1').div(Q.parse('0')));
});
test('bounded signed arithmetic satisfies cross-multiplication identities', () => {
  for (let a = -12n; a <= 12n; a++) for (let b = 1n; b <= 8n; b++) for (let c = -12n; c <= 12n; c++) for (let d = 1n; d <= 8n; d++) {
    const x = new Q(a, b), y = new Q(c, d), z = x.add(y), m = x.mul(y);
    assert.equal(z.n * b * d, (a*d + c*b) * z.d);
    assert.equal(m.n * b * d, a*c*m.d);
    assert.equal(String(z.sub(y)), String(x));
    if (c) assert.equal(String(m.div(y)), String(x));
  }
});
test('rational values are immutable', () => { const x = Q.parse('1/2'); assert.throws(() => { x.n = 9n; }); });
test('seeds include zero and unsigned maximum; ambiguous forms refused', () => {
  assert.equal(parseSeed('0'), 0); assert.equal(parseSeed('4294967295'), 4294967295);
  for (const s of ['-1', '01', '1.0', '4294967296', '1e3', '', ' 1', 'NaN', 1]) assert.throws(() => parseSeed(s));
});
test('every campaign has exactly one valid choice and three passing invariant summaries', () => {
  const winners = new Set();
  for (const seed of [0, 1, 42, 20261021, 4294967295]) for (let level = 0; level < LEVEL_COUNT; level++) {
    const p = puzzle(seed, level), good = p.candidates.map((c, i) => c.analysis.fault ? -1 : i).filter(i => i >= 0);
    assert.equal(good.length, 1); winners.add(good[0]);
    for (const c of p.candidates) { assert.ok(c.analysis.mass && c.analysis.bounds && c.analysis.energy); assert.notEqual(c.analysis.energies[0], c.analysis.energies.at(-1)); }
  }
  assert.equal(winners.size, 3);
});
test('exports reproduce exactly, contain no verdict and terminate the CSV', () => {
  const p = puzzle(0, 5), a = exportCase(p, 2), b = exportCase(puzzle(0, 5), 2);
  assert.deepEqual(a, b); assert.equal(a.trajectory.split('\n').length, p.contract.steps + 3);
  assert.deepEqual(Object.keys(a).sort(), ['choice', 'contract', 'format', 'level', 'seed', 'trajectory']);
  assert.ok(a.trajectory.endsWith('\n')); assert.match(a.trajectory, /^time_s,C0,C1,C2\n/);
});
test('campaign and choice bounds are strict', () => {
  for (const k of [-1, 6, 1.5, NaN, '0']) assert.throws(() => puzzle(1, k));
  for (const i of [-1, 3, 0.5, undefined, '0']) assert.throws(() => exportCase(puzzle(1, 0), i));
});
