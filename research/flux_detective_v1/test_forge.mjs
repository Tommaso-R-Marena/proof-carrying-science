import test from 'node:test';
import assert from 'node:assert/strict';
import {Q,puzzle,exportCase} from './engine.mjs';
import {pairRegion,regionFor,forgeCase,sliderAmount} from './forge.mjs';
const q=Q.parse;
test('exact energy interval includes both orientations and equality',()=>{
  for(const [x,y,low,high] of [['1','0','0','1'],['0','1','-1','0'],['1/2','1/2','0','0']]) {
    const r=pairRegion(q('1'),q('1'),q(x),q(y),q('0'),q('1'));
    assert.equal(String(r.low),low);assert.equal(String(r.high),high);
  }
});
test('invalid pair, volume, bounds and rational encodings are rejected',()=>{
  for(const [left,right] of [[0,0],[-1,1],[0,2],[0,'1'],[0,NaN]]) assert.throws(()=>regionFor(puzzle(0,0),left,right));
  for(const [v,w,x,y,lo,hi] of [['0','1','1','0','0','1'],['1','-1','1','0','0','1'],['1','1','2','0','0','1'],['1','1','1','0','1','0']]) assert.throws(()=>pairRegion(...[v,w,x,y,lo,hi].map(q)));
  for(const s of ['-0','01','2/4','1/0','1e3']) assert.throws(()=>forgeCase(puzzle(0,0),0,1,s));
});
test('all endpoints and midpoints preserve stronger summaries and any nonzero transfer fails the model',()=>{
  for(let level=0;level<6;level++) {
    const p=puzzle(20261021,level), before=JSON.stringify(exportCase(p,0));
    for(let i=0;i<p.contract.cells.length;i++) for(let j=0;j<p.contract.cells.length;j++) if(i!==j) {
      const r=regionFor(p,i,j);
      for(const tick of [0,50,100]) {
        const f=forgeCase(p,i,j,sliderAmount(r,tick));
        assert.ok(f.summary.inside && f.summary.stronger);
        assert.equal(f.summary.exact_model,f.amount==='0');
        assert.equal(f.summary.invariant_impostor,f.amount!=='0');
      }
    }
    assert.equal(JSON.stringify(exportCase(p,0)),before);
  }
});
test('manual transfers expose failed conditions; restoring zero reconstructs the model',()=>{
  const p=puzzle(0,0), bad=forgeCase(p,0,1,'1000');
  assert.ok(bad.analysis.mass);assert.ok(!bad.analysis.bounds && !bad.summary.inside && !bad.summary.stronger);
  assert.ok(bad.analysis.fault);assert.ok(forgeCase(p,0,1,'0').summary.exact_model);
  // Intermediate energy arithmetic does not feed a 96-character input parser.
  assert.ok(forgeCase(p,0,1,'1'.repeat(90)).analysis.fault);
});
test('slider uses exact rational interpolation and strict integer ticks',()=>{
  const r={low:q('-1/3'),high:q('2/3')};assert.equal(sliderAmount(r,25),'-1/12');
  for(const tick of [-1,101,0.5,'0',NaN]) assert.throws(()=>sliderAmount(r,tick));
});
test('workshop export stays compatible with the unchanged data-only envelope',()=>{
  const f=forgeCase(puzzle(0,0),0,1,'1/64');
  assert.deepEqual(Object.keys(f.bundle).sort(),['choice','contract','format','level','seed','trajectory']);
  assert.equal(f.bundle.format,'pcs-flux-detective-export-v1');
  assert.equal(f.bundle.trajectory.split('\n').length,f.p.contract.steps+3);
});
