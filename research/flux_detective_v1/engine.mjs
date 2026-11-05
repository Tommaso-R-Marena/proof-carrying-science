// Exact arithmetic for a synthetic, discrete transport puzzle. No Lean runs here.
const gcd = (a, b) => { a = a < 0n ? -a : a; while (b) [a, b] = [b, a % b]; return a; };
export class Q {
  constructor(n, d = 1n) {
    if (typeof n !== 'bigint' || typeof d !== 'bigint' || d === 0n) throw Error('BigInt rational required');
    if (d < 0n) { n = -n; d = -d; }
    const g = gcd(n, d); this.n = n / g; this.d = d / g; Object.freeze(this);
  }
  static parse(s) {
    if (typeof s !== 'string' || s.length > 96 || !/^(0|-?[1-9][0-9]*)(\/[1-9][0-9]*)?$/.test(s)) throw Error('Canonical rational required');
    const [n, d = '1'] = s.split('/'); const q = new Q(BigInt(n), BigInt(d));
    if (q.toString() !== s) throw Error('Canonical rational required'); return q;
  }
  add(b) { return new Q(this.n * b.d + b.n * this.d, this.d * b.d); }
  sub(b) { return new Q(this.n * b.d - b.n * this.d, this.d * b.d); }
  mul(b) { return new Q(this.n * b.n, this.d * b.d); }
  div(b) { return new Q(this.n * b.d, this.d * b.n); }
  cmp(b) { const t = this.n * b.d - b.n * this.d; return t < 0n ? -1 : t > 0n ? 1 : 0; }
  toString() { return this.d === 1n ? String(this.n) : `${this.n}/${this.d}`; }
}
const zero = new Q(0n), one = new Q(1n), q = Q.parse;
const sum = xs => xs.reduce((a, b) => a.add(b), zero);
export function parseSeed(s) {
  if (typeof s !== 'string' || !/^(0|[1-9][0-9]{0,9})$/.test(s) || BigInt(s) > 4294967295n) throw Error('Seed must be an integer from 0 to 4294967295');
  return Number(s);
}
function rng(seed) {
  // Specified 32-bit LCG. Zero is a valid seed; no Math.random or clock dependency.
  let x = seed;
  return n => { x = (Math.imul(1664525, x) + 1013904223) >>> 0; return x % n; };
}
export function step(contract, state, factor = one) {
  const v = contract.cells.map(c => q(c.volume));
  const amounts = state.map((x, i) => x.mul(v[i]));
  for (const e of contract.edges) {
    const i = contract.cells.findIndex(c => c.id === e.left), j = contract.cells.findIndex(c => c.id === e.right);
    const f = q(contract.time_step).mul(q(e.conductance)).mul(state[i].sub(state[j])).mul(factor);
    amounts[i] = amounts[i].sub(f); amounts[j] = amounts[j].add(f);
  }
  return amounts.map((x, i) => x.div(v[i]));
}
export function inspect(contract, rows) {
  const v = contract.cells.map(c => q(c.volume)), initial = contract.cells.map(c => q(c.initial_concentration));
  const lo = initial.reduce((a, b) => a.cmp(b) < 0 ? a : b), hi = initial.reduce((a, b) => a.cmp(b) > 0 ? a : b);
  const amount = row => sum(row.map((x, i) => x.mul(v[i])));
  const energy = row => sum(row.map((x, i) => x.mul(x).mul(v[i])));
  let fault = null;
  rows[0].forEach((x, i) => { if (!fault && x.cmp(initial[i])) fault = {kind: 'initial', step: 0, cell: i, observed: String(x), expected: String(initial[i]), residual: String(x.sub(initial[i]))}; });
  for (let k = 0; k < rows.length - 1; k++) {
    const expected = step(contract, rows[k]);
    rows[k + 1].forEach((x, i) => {
      if (!fault && x.cmp(expected[i])) fault = {kind: 'recurrence', step: k, cell: i, observed: String(x), expected: String(expected[i]), residual: String(x.sub(expected[i]))};
    });
  }
  return {mass: rows.every(row => amount(row).cmp(amount(initial)) === 0),
    bounds: rows.every(row => row.every(x => x.cmp(lo) >= 0 && x.cmp(hi) <= 0)),
    energy: rows.slice(1).every((row, k) => energy(row).cmp(energy(rows[k])) <= 0),
    energies: rows.map(row => String(energy(row))), amount: String(amount(initial)), fault};
}
export const LEVEL_COUNT = 6;
export function puzzle(seed, level) {
  parseSeed(String(seed));
  if (!Number.isInteger(level) || level < 0 || level >= LEVEL_COUNT) throw Error('Level outside campaign');
  const next = rng((seed ^ Math.imul(level + 1, 2654435761)) >>> 0);
  const width = 2 + level % 4, steps = 1 + Math.floor(level / 2);
  const cells = Array.from({length: width}, (_, i) => ({id: `C${i}`, volume: String(1 + next(3)), initial_concentration: i === 0 ? '1' : '0'}));
  const edges = Array.from({length: width - 1}, (_, i) => ({left: `C${i}`, right: `C${i+1}`, conductance: '1/8'}));
  const contract = {format: 'pcs-finite-volume-transport-contract-v3',
    question: 'Check an exact synthetic puzzle trajectory against its declared discrete diffusion model.',
    cells, edges, time_step: '1/4', steps,
    units: {volume: 'm^3', concentration: 'mol/m^3', conductance: 'm^3/s', time: 's'},
    data_path: 'trajectory.csv', data_origin: 'synthetic_numerical_computation_not_empirical', license: 'CC0-1.0',
    assumptions: [{id: 'A_CLOSED', statement: 'Only the declared symmetric internal conductances act; no source or boundary flux.'},
      {id: 'A_DISCRETE', statement: 'This explicit discrete rational update is the model. No empirical or continuum validity is asserted.'}]};
  const prefix = [cells.map(c => q(c.initial_concentration))];
  for (let k = 1; k < steps; k++) prefix.push(step(contract, prefix.at(-1)));
  const factors = [one, new Q(2n), new Q(3n)];
  // Fisher-Yates shuffle avoids a fixed winning position.
  for (let i = factors.length - 1; i > 0; i--) { const j = next(i + 1); [factors[i], factors[j]] = [factors[j], factors[i]]; }
  const candidates = factors.map(f => {
    const rows = [...prefix.map(row => [...row]), step(contract, prefix.at(-1), f)];
    return {rows, analysis: inspect(contract, rows)};
  });
  return {seed, level, contract, candidates};
}
export function exportCase(p, choice) {
  if (!Number.isInteger(choice) || choice < 0 || choice > 2) throw Error('Choose a trajectory');
  const rows = p.candidates[choice].rows;
  const csv = [`time_s,${p.contract.cells.map(c => c.id).join(',')}`,
    ...rows.map((row, k) => [String(q(p.contract.time_step).mul(new Q(BigInt(k)))), ...row.map(String)].join(','))].join('\n') + '\n';
  // No browser-supplied verdict is exported. The receiving checker decides again.
  return {format: 'pcs-flux-detective-export-v1', seed: p.seed, level: p.level, choice, contract: p.contract, trajectory: csv};
}
