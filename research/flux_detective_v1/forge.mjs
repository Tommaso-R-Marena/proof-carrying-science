// Construct data, never a proof verdict. The receiver checks exported bytes again.
import {Q, step, inspect, exportCase} from './engine.mjs';
const q = Q.parse, zero = q('0'), two = q('2');
const min = (...xs) => xs.reduce((a,b) => a.cmp(b) < 0 ? a : b);
const max = (...xs) => xs.reduce((a,b) => a.cmp(b) > 0 ? a : b);
export function pairRegion(v, w, x, y, lo, hi) {
  if (v.cmp(zero) <= 0 || w.cmp(zero) <= 0 || lo.cmp(hi) > 0 || [x,y].some(z => z.cmp(lo)<0 || z.cmp(hi)>0)) throw Error('Positive volumes and in-bounds baseline required');
  const root = two.mul(v).mul(w).mul(x.sub(y)).div(v.add(w));
  const low = max(min(zero,root), v.mul(x.sub(hi)), w.mul(lo.sub(y)));
  const high = min(max(zero,root), v.mul(x.sub(lo)), w.mul(hi.sub(y)));
  return {root, low, high};
}
export function baseline(p) {
  const rows = [p.contract.cells.map(c => q(c.initial_concentration))];
  for (let k=0; k<p.contract.steps; k++) rows.push(step(p.contract, rows.at(-1)));
  return rows;
}
export function regionFor(p, left, right) {
  const n=p.contract.cells.length;
  if (![left,right].every(i => Number.isInteger(i) && i>=0 && i<n) || left===right) throw Error('Choose two different declared cells');
  const rows=baseline(p), initial=rows[0], row=rows.at(-1);
  const v=q(p.contract.cells[left].volume), w=q(p.contract.cells[right].volume);
  const lo=min(...initial), hi=max(...initial), x=row[left], y=row[right];
  return {...pairRegion(v,w,x,y,lo,hi), rows, v,w,x,y,lo,hi};
}
export function forgeCase(p, left, right, amount) {
  const t=q(amount), region=regionFor(p,left,right), rows=region.rows.map(row=>[...row]);
  rows.at(-1)[left]=region.x.sub(t.div(region.v));
  rows.at(-1)[right]=region.y.add(t.div(region.w));
  const analysis=inspect(p.contract,rows);
  const energy = row => row.reduce((a,x,i)=>a.add(x.mul(x).mul(q(p.contract.cells[i].volume))),zero);
  const energyDelta=energy(rows.at(-1)).sub(energy(region.rows.at(-1)));
  const inside=region.low.cmp(t)<=0 && t.cmp(region.high)<=0;
  const stronger=analysis.mass && analysis.bounds && analysis.energy && energyDelta.cmp(zero)<=0;
  return {p, left, right, amount, rows, region, analysis,
    summary:{amount, low:String(region.low), high:String(region.high), energy_root:String(region.root),
      inside, stronger, energy_delta:String(energyDelta), exact_model:analysis.fault===null,
      invariant_impostor:stronger && analysis.fault!==null},
    bundle:exportCase({...p,candidates:[{rows}]},0)};
}
export function sliderAmount(region, tick) {
  if (!Number.isInteger(tick) || tick<0 || tick>100) throw Error('Slider tick outside 0..100');
  return String(region.low.add(region.high.sub(region.low).mul(new Q(BigInt(tick),100n))));
}
