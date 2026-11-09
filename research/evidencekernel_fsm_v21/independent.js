'use strict';
// Independent exact BigInt reference for registered finite-state allocation policies.
// It does not authenticate the physical experiment or external pin chronology.
const crypto=require('node:crypto');
const {readStrict}=require('../evidencekernel_selective_v17/strict_json');
function insist(v,m){if(!v)throw Error(m);}
function canonical(v){
 if(Array.isArray(v))return '['+v.map(canonical).join(',')+']';
 if(v!==null&&typeof v==='object')return '{'+Object.keys(v).sort().map(k=>JSON.stringify(k)+':'+canonical(v[k])).join(',')+'}';
 return JSON.stringify(v);
}
function digest(v){return crypto.createHash('sha256').update(canonical(v)).digest('hex');}
function gcd(a,b){a=a<0n?-a:a;b=b<0n?-b:b;while(b!==0n){[a,b]=[b,a%b];}return a;}
function F(a,b=1n){a=BigInt(a);b=BigInt(b);insist(b!==0n,'zero denominator');
 if(b<0n){a=-a;b=-b;}let g=gcd(a,b);return [a/g,b/g];}
const ZERO=F(0),ONE=F(1),NEG=F(-1);
const add=(a,b)=>F(a[0]*b[1]+b[0]*a[1],a[1]*b[1]);
const mul=(a,b)=>F(a[0]*b[0],a[1]*b[1]);
const div=(a,b)=>F(a[0]*b[1],a[1]*b[0]);
const cmp=(a,b)=>a[0]*b[1]-b[0]*a[1];
const max=(a,b)=>cmp(a,b)>=0n?a:b;
const str=a=>a[1]===1n?String(a[0]):String(a[0])+'/'+String(a[1]);
function fraction(s,maxLength=30){
 insist(typeof s==='string'&&s.length<=maxLength&&/^-?(0|[1-9]\d*)(?:\/[1-9]\d*)?$/.test(s),'bad rational');
 let q=s.split('/'),v=F(q[0],q[1]||'1');insist(str(v)===s,'noncanonical rational');return v;
}
function exact(o,fields){insist(o&&typeof o==='object'&&!Array.isArray(o)&&
 Object.keys(o).sort().join('|')===fields.slice().sort().join('|'),'unexpected object fields');}
function assignments(n,k){
 let out=[];function recurse(start,prefix){if(prefix.length===k){out.push(prefix);return;}
  for(let i=start;i<=n-(k-prefix.length);i++)recurse(i+1,prefix.concat(i));}
 recurse(0,[]);return out;
}
const fields=['format','n','k','baseline_covariate','max_attempts','initial_state',
 'candidate_law','candidate_weights_by_state','reject_next_state',
 'accept_if_score_le_by_state','selection_rule','null_ate_upper',
 'max_interval_misses','confidence_alpha','tie_rule'];
function design(p){
 exact(p,fields);
 insist(p.format==='pcs-evidencekernel-finite-state-v21'&&
 p.candidate_law==='registered_finite_state_outcome_blind'&&
 p.selection_rule==='first_state_acceptable_else_last'&&
 p.tie_rule==='conditional_lex_right_cdf_given_selected_and_stop','unsupported finite state policy');
 const n=p.n,k=p.k,H=p.max_attempts;
 insist(Number.isSafeInteger(n)&&n>=2&&n<=8&&Number.isSafeInteger(k)&&k>=1&&k<n&&
 Number.isSafeInteger(H)&&H>=1&&H<=64,'invalid trial size or horizon');
 const x=p.baseline_covariate;
 insist(Array.isArray(x)&&x.length===n&&x.every(v=>Number.isSafeInteger(v)&&v>=-16&&v<=16),'invalid baseline');
 const K=p.max_interval_misses;
 insist(Number.isSafeInteger(K)&&K>=0&&K<=n,'bad interval budget');
 const alpha=fraction(p.confidence_alpha),nullATE=fraction(p.null_ate_upper);
 insist(cmp(alpha,ZERO)>0n&&cmp(alpha,ONE)<0n&&cmp(nullATE,NEG)>=0n&&cmp(nullATE,ONE)<=0n,'invalid alpha/null');
 const space=assignments(n,k),N=space.length;
 insist(N*4**n<=5000000,'potential outcome budget exceeded');
 const rows=p.candidate_weights_by_state,trans=p.reject_next_state,limits=p.accept_if_score_le_by_state;
 const S=Array.isArray(rows)?rows.length:-1;
 insist(S>=1&&S<=8&&Array.isArray(trans)&&trans.length===S&&
 Array.isArray(limits)&&limits.length===S,'invalid states');
 const init=p.initial_state;
 insist(Number.isSafeInteger(init)&&init>=0&&init<S,'bad initial state');
 let probs=[];
 for(let s=0;s<S;s++){
  let row=rows[s],next=trans[s],th=limits[s];
  insist(Array.isArray(row)&&row.length===N&&
   row.every(q=>Number.isSafeInteger(q)&&q>=0&&q<=10000),'invalid weights');
  let sum=row.reduce((a,b)=>a+b,0);insist(sum>0,'empty state weights');
  insist(Array.isArray(next)&&next.length===N&&
   next.every(v=>Number.isSafeInteger(v)&&v>=0&&v<S),'invalid transitions');
  insist(Number.isSafeInteger(th)&&th>=0&&th<=10000,'invalid cutoff');
  probs.push(row.map(q=>F(q,sum)));
 }
 let sx=x.reduce((a,b)=>a+b,0);
 let scores=space.map(z=>Math.abs(n*z.reduce((a,i)=>a+x[i],0)-k*sx));
 let acc=limits.map(th=>scores.map(score=>score<=th));
 let alive=new Map([[init,ONE]]),mass=Array.from({length:N},()=>ZERO);
 for(let t=1;t<=H;t++){
  let follow=new Map();
  for(let [s,prob] of alive)for(let i=0;i<N;i++){
   let q=probs[s][i];if(q[0]===0n)continue;
   let v=mul(prob,q);
   if(t===H||acc[s][i])mass[i]=add(mass[i],v);
   else {let ns=trans[s][i];follow.set(ns,add(follow.get(ns)||ZERO,v));}
  }
  alive=follow;
 }
 insist(cmp(mass.reduce(add,ZERO),ONE)===0n,'selection law fails normalization');
 insist(mass.every(v=>v[0].toString(2).length+v[1].toString(2).length<65536),'big design');
 return {n,k,H,N,S,initial:init,space,probs,trans,acc,mass,alpha,nullATE,K};
}
function attemptCommit(pin,attempts){
 return digest({domain:'pcs-evidencekernel-v21-adaptive-attempts',protocol_sha256:pin,attempts});
}
function validate(p,e,d,pin,attemptPin){
 insist(/^[a-f0-9]{64}$/.test(pin)&&/^[a-f0-9]{64}$/.test(attemptPin),'external pins required');
 insist(digest(p)===pin,'registration hash mismatch');
 exact(e,['attempts','selected_assignment','observed_intervals']);
 const a=e.attempts,z=e.selected_assignment,labels=e.observed_intervals;
 insist(Array.isArray(a)&&a.length>0&&a.length<=d.H,'invalid attempt count');
 insist(Array.isArray(labels)&&labels.length===d.n&&
  labels.every(v=>v==='0'||v==='1'||v==='01'),'invalid intervals');
 const ids=[],states=[];let state=d.initial;
 for(let j=0;j<a.length;j++){
  let idx=d.space.findIndex(x=>JSON.stringify(x)===JSON.stringify(a[j]));
  insist(idx>=0,'unknown candidate allocation');
  insist(d.probs[state][idx][0]>0n,'candidate impossible under policy');
  states.push(state);ids.push(idx);
  if(j<a.length-1){insist(!d.acc[state][idx],'early acceptance omitted');state=d.trans[state][idx];}
  else insist(a.length===d.H||d.acc[state][idx],'premature stop');
 }
 insist(Array.isArray(z)&&JSON.stringify(z)===JSON.stringify(a.at(-1)),'selected mismatch');
 insist(attemptCommit(pin,a)===attemptPin,'attempt history commitment mismatch');
 return {ids,states};
}
function conditionalCDF(d,ids){
 let t=ids.length,z=ids.at(-1),memo=new Map();
 function suffix(j,s){
  const key=j+'|'+s;if(memo.has(key))return memo.get(key);
  let answer=ZERO;
  if(j===t)answer=(t===d.H||d.acc[s][z])?d.probs[s][z]:ZERO;
  else for(let i=0;i<d.N;i++)if(!d.acc[s][i]&&d.probs[s][i][0]>0n)
    answer=add(answer,mul(d.probs[s][i],suffix(j+1,d.trans[s][i])));
  memo.set(key,answer);return answer;
 }
 let total=suffix(1,d.initial);
 insist(total[0]>0n,'impossible terminal event');
 let smaller=ZERO,prefix=ONE,state=d.initial;
 for(let j=1;j<t;j++){
  let i=ids[j-1];
  insist(!d.acc[state][i]&&d.probs[state][i][0]>0n,'invalid rejected prefix');
  for(let c=0;c<i;c++)if(!d.acc[state][c]&&d.probs[state][c][0]>0n)
   smaller=add(smaller,mul(prefix,mul(d.probs[state][c],suffix(j+1,d.trans[state][c]))));
  prefix=mul(prefix,d.probs[state][i]);
  state=d.trans[state][i];
 }
 insist(t===d.H||d.acc[state][z],'invalid terminal acceptance');
 let point=mul(prefix,d.probs[state][z]);
 let u=div(add(smaller,point),total);
 insist(cmp(u,ZERO)>0n&&cmp(u,ONE)<=0n,'invalid conditional transcript right CDF');
 return [u,total,point];
}
function stat(world,z,n,k){
 let treated=0,control=0;for(let i=0;i<n;i++){
  if(z.includes(i))treated+=world[i][1];else control+=world[i][0];}
 return (n-k)*treated-k*control;
}
function audit(p,e,pin,attemptPin){
 const d=design(p),{ids,states}=validate(p,e,d,pin,attemptPin);
 const [u,ev,point]=conditionalCDF(d,ids),z=d.space[ids.at(-1)];
 const best=new Map();let compatible=0;
 for(let q=0;q<4**d.n;q++){
  let v=q,w=Array(d.n);
  for(let i=d.n-1;i>=0;i--){let digit=v%4;v=Math.floor(v/4);w[i]=[(digit>>1)&1,digit&1];}
  let misses=0,ate=0;
  for(let i=0;i<d.n;i++){
   ate+=w[i][1]-w[i][0];
   if(e.observed_intervals[i]!=='01'&&e.observed_intervals[i]!==String(w[i][z.includes(i)?1:0]))misses++;
  }
  if(misses>d.K)continue;
  compatible++;
  let scores=d.space.map(alt=>stat(w,alt,d.n,d.k)),obs=scores[ids.at(-1)];
  let gt=ZERO,eq=ZERO;
  for(let i=0;i<d.N;i++){
   if(scores[i]>obs)gt=add(gt,d.mass[i]);else if(scores[i]===obs)eq=add(eq,d.mass[i]);
  }
  const candidate=add(gt,mul(u,eq));
  if(!best.has(ate)||cmp(candidate,best.get(ate))>0n)best.set(ate,candidate);
 }
 insist(compatible>0,'no compatible world');
 let curve=[],peak=NEG;
 for(let h=-d.n;h<=d.n;h++){
  peak=max(peak,best.get(h)||NEG);
  curve.push({ate_upper:str(F(h,d.n)),null_feasible:cmp(peak,ZERO)>=0n,
    max_p:cmp(peak,ZERO)>=0n?str(peak):null});
 }
 curve.at(-1).null_feasible=true;curve.at(-1).max_p='1';
 const relevant=curve.filter(v=>cmp(fraction(v.ate_upper),d.nullATE)<=0n).at(-1);
 const lower=curve.find(v=>v.null_feasible&&cmp(fraction(v.max_p,20000),d.alpha)>0n);
 return {status:relevant.null_feasible?'CONDITIONALLY_VERIFIED':'INCONSISTENT_NULL',
  conditional_p:relevant.max_p,conditional_lower_ate:lower?lower.ate_upper:null,
  confidence_alpha:str(d.alpha),compatible_worlds:compatible,
  design_selected_probability:str(d.mass[ids.at(-1)]),stop_time:ids.length,
  state_history:states,conditional_rank:str(u),
  conditional_terminal_event_mass:str(ev),observed_transcript_mass:str(point),
  null_curve:curve,protocol_sha256:pin,attempts_sha256:attemptPin,
  warning:'Research-only conditional inference: genuine physical randomization, outcome blindness, temporal registration, complete custody and calibration remain external premises.'};
}
if(require.main===module){
 try{
  insist(process.argv.length===6,'usage: node independent.js protocol.json evidence.json protocol_pin attempts_pin');
  console.log(JSON.stringify(audit(readStrict(process.argv[2]),readStrict(process.argv[3]),process.argv[4],process.argv[5]),null,2));
 }catch(e){console.error('REJECTED: '+e.message);process.exit(2);}
}
module.exports={design,attemptCommit,validate,conditionalCDF,audit,digest};
