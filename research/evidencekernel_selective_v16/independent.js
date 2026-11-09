'use strict';
/* Independent JS rational/counting verifier for v16, no Python imports.
   Computational redundancy, not a second independent real-world custodian. */
const fs=require('node:fs');
const crypto=require('node:crypto');
const {readStrict}=require('./strict_json');
function fail(message){throw Error(message);}
function check(ok,message){if(!ok)fail(message);}
function exactKeys(obj,keys){check(obj!==null&&typeof obj==='object'&&!Array.isArray(obj)&&
 Object.keys(obj).sort().join('|')===keys.slice().sort().join('|'),'invalid object keys');}
function canonical(value){
 if(Array.isArray(value))return '['+value.map(canonical).join(',')+']';
 if(value&&typeof value==='object')return '{'+Object.keys(value).sort().map(k=>JSON.stringify(k)+':'+canonical(value[k])).join(',')+'}';
 return JSON.stringify(value);
}
function hash(x){return crypto.createHash('sha256').update(canonical(x)).digest('hex');}
function gcd(a,b){a=Math.abs(a);b=Math.abs(b);while(b!==0){let c=a%b;a=b;b=c;}return a;}
function rational(a,b){const g=gcd(a,b);return b/g===1?String(a/g):`${a/g}/${b/g}`;}
function parseFraction(s){
 check(typeof s==='string'&&s.length<31&&/^-?(0|[1-9]\d*)(?:\/[1-9]\d*)?$/.test(s),'invalid rational');
 let [a,b=1]=s.split('/').map(Number);check(Number.isSafeInteger(a)&&Number.isSafeInteger(b)&&b>0,'invalid rational range');
 check(rational(a,b)===s,'noncanonical rational');return [a,b];
}
function assignments(n,k){
 const out=[];function go(next,chosen){if(chosen.length===k){out.push(chosen.slice());return;}
 for(let i=next;i<=n-(k-chosen.length);i++)go(i+1,[...chosen,i]);}go(0,[]);return out;
}
function design(p){
 exactKeys(p,['format','n','k','baseline_covariate','candidate_draws','candidate_law','selection_rule','null_ate_upper','max_interval_misses']);
 check(p.format==='pcs-evidencekernel-outcome-blind-selection-v16','wrong format');
 const n=p.n,k=p.k,b=p.candidate_draws;
 check(Number.isInteger(n)&&n>=2&&n<=7&&Number.isInteger(k)&&k>0&&k<n,'size rejected');
 check(Number.isInteger(b)&&b>=1&&b<=3,'candidate count rejected');
 check(p.candidate_law==='iid_with_replacement'||p.candidate_law==='ordered_without_replacement','unknown design');
 check(p.selection_rule==='minimum_absolute_baseline_imbalance_first_tie','selection policy mismatch');
 check(Array.isArray(p.baseline_covariate)&&p.baseline_covariate.length===n&&
 p.baseline_covariate.every(x=>Number.isInteger(x)&&x>=-16&&x<=16),'invalid covariate');
 const [hnum,hden]=parseFraction(p.null_ate_upper);
 check(Math.abs(hnum)<=hden,'invalid null bound');
 check(Number.isInteger(p.max_interval_misses)&&p.max_interval_misses>=0&&p.max_interval_misses<=n,'bad misses');
 const A=assignments(n,k),N=A.length;
 check(p.candidate_law!=='ordered_without_replacement'||b<=N,'too few allocations');
 const total=p.candidate_law==='iid_with_replacement'?N**b:Array.from({length:b},(_,i)=>N-i).reduce((x,y)=>x*y,1);
 check(total<=20000,'resource cap');
 const sumx=p.baseline_covariate.reduce((a,b)=>a+b,0);
 const scores=A.map(z=>Math.abs(n*z.reduce((a,i)=>a+p.baseline_covariate[i],0)-k*sumx));
 const mass=Array(N).fill(0);const draw=[];
 function walk(){if(draw.length===b){let best=draw[0];for(const i of draw){if(scores[i]<scores[best])best=i;}mass[best]++;return;}
  for(let i=0;i<N;i++){
   if(p.candidate_law==='ordered_without_replacement'&&draw.includes(i))continue;
   draw.push(i);walk();draw.pop();
  }}walk();
 check(mass.reduce((a,b)=>a+b,0)===total,'mass conservation failure');
 return {A,scores,mass,total,n,k,b,hnum,hden};
}
function selectedIndex(d,attempts,p){
 check(Array.isArray(attempts)&&attempts.length===d.b,'incomplete attempt roster');
 const ii=attempts.map(z=>{check(Array.isArray(z)&&z.length===d.k&&z.every(Number.isInteger), 'invalid attempts');
 const i=d.A.findIndex(a=>JSON.stringify(a)===JSON.stringify(z));check(i>=0,'allocation not in universe');return i;});
 if(p.candidate_law==='ordered_without_replacement')check(new Set(ii).size===ii.length,'duplicate without-replacement attempt');
 let win=ii[0];for(const i of ii){if(d.scores[i]<d.scores[win])win=i;}return win;
}
function stat(world,z,n,k){let treated=0,controls=0;
 for(let i=0;i<n;i++){if(z.includes(i))treated+=world[i][1];else controls+=world[i][0];}
 return (n-k)*treated-k*controls;
}
function audit(p,e,pin){
 check(typeof pin==='string'&&/^[0-9a-f]{64}$/.test(pin),'external pin required');
 check(hash(p)===pin,'protocol not externally pinned');
 const d=design(p);
 exactKeys(e,['attempts','selected_assignment','observed_intervals']);
 check(Array.isArray(e.selected_assignment)&&e.selected_assignment.every(Number.isInteger),'bad observed assignment');
 const chosen=selectedIndex(d,e.attempts,p);
 check(JSON.stringify(e.selected_assignment)===JSON.stringify(d.A[chosen]),'selected candidate mismatch');
 check(d.mass[chosen]>0,'impossible observed assignment');
 check(Array.isArray(e.observed_intervals)&&e.observed_intervals.length===d.n&&
 e.observed_intervals.every(x=>['0','1','01'].includes(x)),'bad binary labels');
 const cap=4**d.n*d.A.length;check(cap<=2000000,'world search exceeds cap');
 let best=-1,worlds=0,witness=null;
 for(let t=0;t<4**d.n;t++){
  let x=t;const world=[];let miss=0,ate=0;
  for(let i=d.n-1;i>=0;i--){let v=x%4;x=Math.floor(x/4);world[i]=[v>>1,v&1];}
  for(let i=0;i<d.n;i++){
    ate+=world[i][1]-world[i][0];
    const observed=world[i][e.selected_assignment.includes(i)?1:0];
    if(e.observed_intervals[i]!=='01'&&e.observed_intervals[i]!==String(observed))miss++;
  }
  if(miss>p.max_interval_misses||ate*d.hden>d.hnum*d.n)continue;
  worlds++;
  const threshold=stat(world,d.A[chosen],d.n,d.k);
  let hits=0;
  for(let i=0;i<d.A.length;i++)if(d.mass[i]&&stat(world,d.A[i],d.n,d.k)>=threshold)hits+=d.mass[i];
  if(hits>best){best=hits;witness=world.map(x=>x.join(''));}
 }
 if(best<0)return {status:'INCONSISTENT_NULL',conditional_robust_p:null,compatible_worlds:0,
   design_denominator:d.total,protocol_sha256:pin};
 return {status:'CONDITIONALLY_VERIFIED',conditional_robust_p:rational(best,d.total),tail_mass:best,
  design_denominator:d.total,compatible_worlds:worlds,maximizing_world:witness,protocol_sha256:pin,
  warning:'Randomness, chronology, baseline blindness, interval calibration and complete attempt custody are unverified external premises.'};
}
if(require.main===module){
 try{check(process.argv.length===5,'usage: node independent.js protocol.json evidence.json PIN');
 console.log(JSON.stringify(audit(readStrict(process.argv[2]),readStrict(process.argv[3]),process.argv[4]),null,2));}
 catch(e){console.error('REJECTED:',e.message);process.exit(2);}
}
module.exports={audit,design,hash};
