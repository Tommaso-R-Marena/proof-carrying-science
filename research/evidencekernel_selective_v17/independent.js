'use strict';
/* Independent exact JavaScript/BigInt implementation of v17.
   Computational redundancy, not an external randomness or evidence custodian. */
const fs = require('node:fs');
const crypto = require('node:crypto');
const {readStrict} = require('./strict_json');
function insist(v, msg){if(!v)throw Error(msg);}
function exactKeys(o,ks,c){insist(o!==null&&typeof o==='object'&&!Array.isArray(o)&&
  Object.keys(o).sort().join('|')===ks.slice().sort().join('|'),c+': invalid keys');}
function canonical(v){
  if(Array.isArray(v))return '['+v.map(canonical).join(',')+']';
  if(v!==null&&typeof v==='object')return '{'+Object.keys(v).sort().map(k=>JSON.stringify(k)+':'+canonical(v[k])).join(',')+'}';
  return JSON.stringify(v);
}
function digest(v){return crypto.createHash('sha256').update(canonical(v)).digest('hex');}
function abs(a){return a<0n?-a:a;}
function gcd(a,b){a=abs(a);b=abs(b);while(b!==0n){let r=a%b;a=b;b=r;}return a;}
function frac(a,b){insist(b>0n,'bad rational denominator');let g=gcd(a,b);return b/g===1n?String(a/g):String(a/g)+'/'+String(b/g);}
function parseFrac(s){
  insist(typeof s==='string'&&s.length<=30&&/^-?(0|[1-9]\d*)(?:\/[1-9]\d*)?$/.test(s),'noncanonical rational');
  let v=s.split('/');let a=BigInt(v[0]),b=BigInt(v.length===2?v[1]:1);
  insist(frac(a,b)===s,'noncanonical rational');return [a,b];
}
function comp(a,b){return a[0]*b[1]-b[0]*a[1];}
function chooseAssignments(n,k){const result=[];function go(start,z){if(z.length===k){result.push(z.slice());return;}
  for(let i=start;i<=n-(k-z.length);i++)go(i+1,[...z,i]);}
 go(0,[]);return result;}
function falling(n,k){if(k>n)return 0n;let x=1n;for(let i=0;i<k;i++)x*=BigInt(n-i);return x;}
function design(p){
  exactKeys(p,['format','n','k','baseline_covariate','candidate_draws','candidate_law',
               'selection_rule','null_ate_upper','max_interval_misses','confidence_alpha','randomizer_support','randomizer_rule'],'protocol');
  insist(p.format==='pcs-evidencekernel-balanced-selection-v17','wrong format');
  const n=p.n,k=p.k,b=p.candidate_draws;
  insist(Number.isSafeInteger(n)&&n>=2&&n<=8&&Number.isSafeInteger(k)&&k>0&&k<n,'trial size unsupported');
  insist(Number.isSafeInteger(b)&&b>0&&b<=4096,'draw count unsupported');
  insist(p.candidate_law==='iid_with_replacement'||p.candidate_law==='ordered_without_replacement','invalid candidate law');
  insist(p.selection_rule==='minimum_absolute_baseline_imbalance_first_tie','invalid selection');
  insist(Array.isArray(p.baseline_covariate)&&p.baseline_covariate.length===n&&
         p.baseline_covariate.every(x=>Number.isSafeInteger(x)&&x>=-16&&x<=16),'invalid covariates');
  const h=parseFrac(p.null_ate_upper),alpha=parseFrac(p.confidence_alpha);
  insist(comp(h,[-1n,1n])>=0n&&comp(h,[1n,1n])<=0n,'invalid null');
  insist(comp(alpha,[0n,1n])>0n&&comp(alpha,[1n,1n])<0n,'invalid confidence alpha');
  insist(Number.isSafeInteger(p.max_interval_misses)&&p.max_interval_misses>=0&&p.max_interval_misses<=n,
         'invalid miss budget');
  insist(p.randomizer_rule==='independent_right_endpoint_uniform','unsupported randomized-tie rule');
  insist(Number.isSafeInteger(p.randomizer_support)&&p.randomizer_support>=2&&p.randomizer_support<=256,'invalid randomizer support');
  const A=chooseAssignments(n,k),N=A.length;
  insist(p.candidate_law==='iid_with_replacement'||b<=N,'without-replacement impossible');
  const bits=BigInt(Math.floor(Math.log2(N))+1)*BigInt(p.candidate_law==='iid_with_replacement'?b:Math.min(N,b));
  insist(bits<=32768n,'design integer cap exceeded');
  const sumx=p.baseline_covariate.reduce((a,b)=>a+b,0);
  const scores=A.map(z=>Math.abs(n*z.reduce((a,i)=>a+p.baseline_covariate[i],0)-k*sumx));
  const groups=new Map();scores.forEach((score,i)=>{if(!groups.has(score))groups.set(score,[]);groups.get(score).push(i);});
  const mass=A.map(()=>0n), F=t=>p.candidate_law==='iid_with_replacement'?BigInt(t)**BigInt(b):falling(t,b);
  let above=0;
  for(const score of [...groups.keys()].sort((a,b)=>b-a)){
    const indices=groups.get(score),m=indices.length;
    const wins=F(above+m)-F(above);
    insist(wins>=0n&&wins%BigInt(m)===0n,'invalid selection symmetry');
    for(const i of indices)mass[i]=wins/BigInt(m);
    above+=m;
  }
  const denom=F(N);insist(mass.reduce((a,b)=>a+b,0n)===denom,'probability mass mismatch');
  return {A,scores,mass,denom,n,k,b,h,alpha};
}
function validate(p,e,pin,d){
  insist(typeof pin==='string'&&/^[0-9a-f]{64}$/.test(pin),'external pin required');
  insist(digest(p)===pin,'protocol does not match externally pinned SHA-256');
  exactKeys(e,['attempts','selected_assignment','observed_intervals'],'evidence');
  const z=e.selected_assignment;
  insist(Array.isArray(z)&&z.length===d.k&&z.every(Number.isSafeInteger),'invalid assignment');
  insist(Array.isArray(e.observed_intervals)&&e.observed_intervals.length===d.n&&
         e.observed_intervals.every(x=>x==='0'||x==='1'||x==='01'),'invalid intervals');
  insist(Array.isArray(e.attempts)&&e.attempts.length===d.b,'missing/extra attempts');
  const indices=e.attempts.map(x=>{
    insist(Array.isArray(x)&&x.length===d.k&&x.every(Number.isSafeInteger),'invalid attempt');
    const i=d.A.findIndex(a=>JSON.stringify(a)===JSON.stringify(x));
    insist(i>=0,'invalid candidate allocation');return i;
  });
  if(p.candidate_law==='ordered_without_replacement')insist(new Set(indices).size===indices.length,'duplicate distinct assignment');
  let win=indices[0];for(const i of indices){if(d.scores[i]<d.scores[win])win=i;}
  insist(JSON.stringify(d.A[win])===JSON.stringify(z),'selected assignment violates preregistered rule');
  insist(d.mass[win]>0n,'impossible selected assignment');return win;
}
function stat(world,z,n,k){let t=0,c=0;const set=new Set(z);
  for(let i=0;i<n;i++){if(set.has(i))t+=world[i][1];else c+=world[i][0];}
  return (n-k)*t-k*c;
}
function audit(p,e,pin,externalUniformIndex=null){
  const d=design(p),win=validate(p,e,pin,d);
  const M=p.randomizer_support;
  if(externalUniformIndex!==null)insist(Number.isSafeInteger(externalUniformIndex)&&externalUniformIndex>=1&&externalUniformIndex<=M,'invalid independent uniform index');
  insist(4**d.n*d.A.length<=5000000,'latent-world capacity exceeded');
  const z=d.A[win],labels=e.observed_intervals;
  const byAte=new Map(), witnesses=new Map(), randomizedByAte=new Map();let compatible=0;
  for(let idx=0;idx<4**d.n;idx++){
    let v=idx;const world=Array(d.n);
    for(let i=d.n-1;i>=0;i--){const x=v%4;v=Math.floor(v/4);world[i]=[(x>>1)&1,x&1];}
    let misses=0,ate=0;const zs=new Set(z);
    for(let i=0;i<d.n;i++){
      ate+=world[i][1]-world[i][0];const observed=world[i][zs.has(i)?1:0];
      if(labels[i]!=='01'&&labels[i]!==String(observed))misses++;
    }
    if(misses>p.max_interval_misses)continue;
    compatible++;
    const threshold=stat(world,z,d.n,d.k);
    let gt=0n,eq=0n;
    for(let i=0;i<d.A.length;i++)if(d.mass[i]>0n){const v=stat(world,d.A[i],d.n,d.k);
      if(v>threshold)gt+=d.mass[i];else if(v===threshold)eq+=d.mass[i];}
    const hits=gt+eq;
    if(externalUniformIndex!==null){const value=BigInt(M)*gt+BigInt(externalUniformIndex)*eq;
      if(!randomizedByAte.has(ate)||value>randomizedByAte.get(ate))randomizedByAte.set(ate,value);}
    if(!byAte.has(ate)||hits>byAte.get(ate)){byAte.set(ate,hits);witnesses.set(ate,world.map(x=>x.join('')));}
  }
  insist(compatible>0,'no compatible potential outcome model');
  let prefix=-1n;const curve=[];
  for(let j=-d.n;j<=d.n;j++){
    if(byAte.has(j)&&byAte.get(j)>prefix)prefix=byAte.get(j);
    curve.push({ate_upper:frac(BigInt(j),BigInt(d.n)),max_p:prefix<0n?null:frac(prefix,d.denom),null_feasible:prefix>=0n});
  }
  const selected=curve.filter(c=>comp(parseFrac(c.ate_upper),d.h)<=0n).at(-1);
  const first=curve.find(c=>c.null_feasible&&comp(parseFrac(c.max_p),d.alpha)>0n);
  let randomizedCurve=null, randomizedReport=null, randomizedLower=null, randomizedStatus=null;
  if(externalUniformIndex!==null){
    randomizedCurve=[];let peak=-1n;
    for(let j=-d.n;j<=d.n;j++){
      if(randomizedByAte.has(j)&&randomizedByAte.get(j)>peak)peak=randomizedByAte.get(j);
      randomizedCurve.push({ate_upper:frac(BigInt(j),BigInt(d.n)),
        max_p:peak<0n?null:frac(peak,BigInt(M)*d.denom),null_feasible:peak>=0n});
    }
    const selectedIdx=curve.findLastIndex(c=>comp(parseFrac(c.ate_upper),d.h)<=0n);
    randomizedReport=randomizedCurve[selectedIdx].max_p;
    const candidate=randomizedCurve.find(c=>c.null_feasible&&comp(parseFrac(c.max_p),d.alpha)>0n);
    randomizedLower=candidate?candidate.ate_upper:null;
    randomizedStatus=candidate?'NONEMPTY':'EMPTY_SET';
  }
  let witness=null;
  if(selected.null_feasible){let best=-1n;
    for(const t of [...byAte.keys()].sort((a,b)=>a-b)){
      if(BigInt(t)*d.h[1]>d.h[0]*BigInt(d.n))continue;
      if(byAte.get(t)>best){best=byAte.get(t);witness=witnesses.get(t);}
    }
  }
  return {status:selected.null_feasible?'CONDITIONALLY_VERIFIED':'INCONSISTENT_NULL',
          conditional_robust_p:selected.max_p,null_feasible:selected.null_feasible,
          compatible_worlds:compatible,design_denominator:String(d.denom),
          selected_assignment_mass:String(d.mass[win]),maximizing_world:witness,
          confidence_alpha:frac(...d.alpha),conditional_lower_ate:first?first.ate_upper:null,
          confidence_set_status:first?'NONEMPTY':'EMPTY_SET',null_curve:curve,
          randomized_conditional_p:randomizedReport,randomized_conditional_lower_ate:randomizedLower,
          randomized_confidence_set_status:randomizedStatus,randomized_null_curve:randomizedCurve,
          external_uniform_index:externalUniformIndex,randomizer_support:M,protocol_sha256:pin,
          warning:'Conditional result only: candidate draw law, chronology, baseline blindness, interval coverage and complete attempts are external assumptions. Randomized p-values additionally require an independently uniform tie randomizer, not chosen or reset by the researcher.'};
}
if(require.main===module){try{
 insist(process.argv.length===5||process.argv.length===6,'usage: node independent.js protocol.json evidence.json PIN [external_uniform_index]');
 const u=process.argv.length===6?Number(process.argv[5]):null;
 const report=audit(readStrict(process.argv[2]),readStrict(process.argv[3]),process.argv[4],u);
 console.log(JSON.stringify(report,null,2));
}catch(e){console.error('REJECTED:',e.message);process.exit(2);}}
module.exports={design,audit,digest};
