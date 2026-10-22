import test from 'node:test';
import assert from 'node:assert/strict';
import {puzzle,exportCase} from './engine.mjs';
import {forgeCase} from './forge.mjs';
import {wireRat,strictJSON,inspectCase,MAX_INPUT_BYTES} from './inspector.mjs';
const good=()=>{const p=puzzle(20261021,0);return exportCase(p,p.candidates.findIndex(c=>!c.analysis.fault));};
test('legacy exact decimal and rational aliases normalize without binary floats',()=>{
  for(const [raw,expected] of [['-0','0'],['01.00e0','1'],['25e-2','1/4'],['-02/4','-1/2'],['0.000000000000000001','1/1000000000000000000']])assert.equal(String(wireRat(raw)),expected);
  for(const raw of ['.5',' 1','1/01','1/0','1e1000','NaN','١',true])assert.throws(()=>wireRat(raw));
});
test('strict structural JSON rejects duplicate keys, ambiguity and resource attacks',()=>{
  for(const raw of ['{"x":1,"x":2}','{"x":1,"\\u0078":2}','{"x":{"a":1,"a":2}}','[1,]','{} true','{"x":1e0}','{"x":9007199254740993}','{"x":"\\ud800"}','\ufeff{}','['.repeat(20)+']'.repeat(20),' '.repeat(MAX_INPUT_BYTES+1)])assert.throws(()=>strictJSON(raw));
  const parsed=strictJSON('{"__proto__":{"polluted":true},"x":1}');assert.equal(Object.getPrototypeOf(parsed),null);assert.equal({}.polluted,undefined);
});
test('model support is an explicit browser diagnostic, never a kernel verdict',()=>{
  const r=inspectCase(JSON.stringify(good()));assert.equal(r.status,'BROWSER_MODEL_MATCH');
  assert.equal(r.kernel_checked,false);assert.equal(r.pcs_authority,false);assert.equal(r.empirical_validation,false);
});
test('a constructed invariant-preserving forgery reports its exact mismatch',()=>{
  const f=forgeCase(puzzle(20261021,0),0,1,'31/64'),r=inspectCase(JSON.stringify(f.bundle));
  assert.equal(r.status,'BROWSER_MODEL_MISMATCH');assert.deepEqual(r.fault,f.analysis.fault);
  assert.ok(r.summaries.mass&&r.summaries.bounds&&r.summaries.historical_energy);
});
test('extra authority fields, invalid paths, dimensions and CFL violations refuse',()=>{
  const mutations=[b=>{b.kernel_checked=true;},b=>{b.contract.data_path='pcs-transport-v3/data.csv';},b=>{b.contract.data_path='../data.csv';},b=>{b.contract.steps=true;},b=>{b.contract.time_step='1000';},b=>{b.contract.cells[1].id=b.contract.cells[0].id;},b=>{b.contract.edges.push({...b.contract.edges[0]});},b=>{b.contract.units.time='minutes';}];
  for(const mutate of mutations){const b=good();mutate(b);assert.throws(()=>inspectCase(JSON.stringify(b)));}
});
test('wire aliases, CRLF and negative zero preserve the imported model meaning',()=>{
  const b=good();b.contract.cells[0].volume='03.0';b.contract.cells[1].volume='1e0';b.contract.cells[1].initial_concentration='-0';b.contract.time_step='25e-2';b.trajectory=b.trajectory.replaceAll('\n','\r\n');
  assert.equal(inspectCase(JSON.stringify(b)).status,'BROWSER_MODEL_MATCH');
});
test('time, initial and recurrence faults are distinguished and exact',()=>{
  for(const kind of ['time','initial','recurrence']){const b=good(),lines=b.trajectory.trimEnd().split('\n'),k=kind==='initial'?1:lines.length-1,row=lines[k].split(',');row[kind==='time'?0:1]='100';lines[k]=row.join(',');b.trajectory=lines.join('\n')+'\n';assert.equal(inspectCase(JSON.stringify(b)).fault.kind,kind);}
});
test('quoted CSV is an explicit browser refusal, not a changed authority parser',()=>{
  const b=good();b.trajectory=b.trajectory.replace('time_s','"time_s"');assert.throws(()=>inspectCase(JSON.stringify(b)),/Quoted CSV/);
});
