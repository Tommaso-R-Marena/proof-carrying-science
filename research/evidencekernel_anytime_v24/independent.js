'use strict';
/* Independently implemented BigInt exact verifier for v24 predictable propensity
 * confidence sequence. No inference code is shared with the Python verifier. */
const crypto=require('node:crypto');
const {readStrict}=require('./strict_json');
function need(ok,msg){if(!ok)throw Error(msg);}
function keys(o,expected,label){need(o!==null && typeof o==='object' && !Array.isArray(o)&&
 Object.keys(o).sort().join('|')===expected.slice().sort().join('|'),label+': keys');}
function enc(o){if(Array.isArray(o))return '['+o.map(enc).join(',')+']';
 if(o!==null&&typeof o==='object')return '{'+Object.keys(o).sort().map(k=>JSON.stringify(k)+':'+enc(o[k])).join(',')+'}';
 return JSON.stringify(o);}
function digest(o){return crypto.createHash('sha256').update(enc(o)).digest('hex');}
function abs(n){return n<0n?-n:n;}
function gcd(a,b){a=abs(a);b=abs(b);while(b!==0n){let t=a%b;a=b;b=t;}return a;}
function F(a,b=1n){need(b!==0n,'zero denominator');if(b<0n){a=-a;b=-b;}const g=gcd(a,b);return [a/g,b/g];}
const Z=F(0n),O=F(1n),N=F(-1n);
function add(a,b){return F(a[0]*b[1]+b[0]*a[1],a[1]*b[1]);}
function neg(a){return [-a[0],a[1]];}
function sub(a,b){return add(a,neg(b));}
function mul(a,b){return F(a[0]*b[0],a[1]*b[1]);}
function div(a,b){need(b[0]!==0n,'division by zero');return F(a[0]*b[1],a[1]*b[0]);}
function cmp(a,b){const d=a[0]*b[1]-b[0]*a[1];return d<0n?-1:d>0n?1:0;}
function out(a){return a[1]===1n?String(a[0]):String(a[0])+'/'+String(a[1]);}
function rat(s){need(typeof s==='string'&&s.length>0&&s.length<=48&&/^-?(?:0|[1-9]\d*)(?:\/[1-9]\d*)?$/.test(s),'rational syntax');
 const [a,b='1']=s.split('/'),v=F(BigInt(a),BigInt(b));need(out(v)===s,'noncanonical rational');return v;}
function nat(v,lo,hi,label){need(Number.isInteger(v)&&v>=lo&&v<=hi,label);return v;}
function taylor(c,terms){let part=O,total=O;
 for(let k=1;k<=terms;k++){part=div(mul(part,c),F(BigInt(k)));total=add(total,part);}return total;}
const FORMAT='pcs-evidencekernel-predictable-anytime-v24';
const RESULT='pcs-evidencekernel-predictable-anytime-audit-v24';
function design(p){
 keys(p,['format','registered_units','states','initial_state',
  'allocation_weights_by_state','next_state_by_state_action_report',
  'stop_after_by_state_action_report','min_enrollment','confidence_alpha',
  'calibration_failure_bound','null_ate_upper','max_interval_misses',
  'tuning','estimand','assignment_model','interval_model','stopping_rule'],'registration');
 need(p.format===FORMAT&&p.estimand==='fixed_registered_cohort_binary_ate'&&
 p.assignment_model==='predictable_bernoulli_fresh_randomness'&&
 p.interval_model==='binary_labels_with_max_misses'&&
 p.stopping_rule==='registered_feedback_fsm','unsupported protocol');
 const n=nat(p.registered_units,2,100000,'n'),S=nat(p.states,1,16,'states');
 const init=nat(p.initial_state,0,S-1,'initial');
 const min=nat(p.min_enrollment,2,n,'min_enrollment');
 const K=nat(p.max_interval_misses,0,n,'max_interval_misses');
 const alpha=rat(p.confidence_alpha),delta=rat(p.calibration_failure_bound),h=rat(p.null_ate_upper);
 need(cmp(alpha,Z)>0&&cmp(alpha,O)<0&&cmp(delta,Z)>=0&&
 cmp(add(delta,alpha),O)<=0&&cmp(h,N)>=0&&cmp(h,O)<=0,'alpha,delta,null');
 const wt=p.allocation_weights_by_state,tr=p.next_state_by_state_action_report,st=p.stop_after_by_state_action_report;
 need([wt,tr,st].every(a=>Array.isArray(a)&&a.length===S),'state table lengths');
 const probabilities=[];
 for(let s=0;s<S;s++){
  const w=wt[s];need(Array.isArray(w)&&w.length===2&&
   w.every(x=>Number.isInteger(x)&&x>=1&&x<=1000),'strictly positive weights');
  probabilities.push(F(BigInt(w[1]),BigInt(w[0]+w[1])));
  for(let a=0;a<2;a++){
   need(Array.isArray(tr[s])&&tr[s].length===2&&Array.isArray(st[s])&&st[s].length===2,
    'state row');
   need(Array.isArray(tr[s][a])&&tr[s][a].length===2&&
    tr[s][a].every(x=>Number.isInteger(x)&&x>=0&&x<S),'transition');
   need(Array.isArray(st[s][a])&&st[s][a].length===2&&
    st[s][a].every(x=>typeof x==='boolean'),'stop flags');
  }
 }
 need(Array.isArray(p.tuning)&&p.tuning.length>=1&&p.tuning.length<=16,'tuning count');
 let spent=Z;const tuning=[];
 for(const entry of p.tuning){
  keys(entry,['lambda','alpha_spend','log_upper','taylor_terms'],'tuning');
  const lambda=rat(entry.lambda),a=rat(entry.alpha_spend),c=rat(entry.log_upper);
  const terms=nat(entry.taylor_terms,1,32,'taylor_terms');
  need(cmp(lambda,Z)>0&&cmp(lambda,O)<=0&&cmp(a,Z)>0&&cmp(a,alpha)<=0&&
   cmp(c,Z)>=0&&cmp(c,F(20n))<=0,'tuning rationals');
  const proof=taylor(c,terms);
  need(cmp(mul(proof,a),O)>=0,'failed exponential lower-bound certificate');
  spent=add(spent,a);
  tuning.push({lambda,a,c,terms,proof});
 }
 need(cmp(spent,alpha)<=0,'overspent alpha');
 return {n,S,init,min,K,alpha,delta,h,probabilities,tr,st,tuning};
}
function audit(p,e,protocolPin,evidencePin){
 need(typeof protocolPin==='string'&&/^[0-9a-f]{64}$/.test(protocolPin)&&
  typeof evidencePin==='string'&&/^[0-9a-f]{64}$/.test(evidencePin),'missing external hash pins');
 need(digest(p)===protocolPin,'registration digest');
 need(digest({domain:'pcs-evidencekernel-v24-observed-prefix',protocol_sha256:protocolPin,evidence:e})===evidencePin,'evidence digest');
 const d=design(p);
 keys(e,['assignments','reports','true_intervals'],'observations');
 need(Array.isArray(e.assignments)&&Array.isArray(e.reports)&&Array.isArray(e.true_intervals),'arrays required');
 const t=e.assignments.length;
 need(t>=d.min&&t<=d.n&&e.reports.length===t&&e.true_intervals.length===t,'truncated observed prefix');
 need(e.assignments.concat(e.reports).every(x=>x===0||x===1),'invalid action/report bits');
 need(e.true_intervals.every(x=>x==='0'||x==='1'||x==='01'),'binary intervals required');
 let state=d.init,HT=Z,W2=Z;
 const penalty=[],trace=[],visits=Array(d.S).fill(0);
 for(let i=0;i<t;i++){
  const a=e.assignments[i],r=e.reports[i],lab=e.true_intervals[i],pp=d.probabilities[state];
  visits[state]++;
  trace.push(out(pp));
  const lower=lab==='1'?1:0,upper=lab==='0'?0:1;
  const treated=div(F(BigInt(lower)),pp);
  const control=div(F(BigInt(upper)),sub(O,pp));
  HT=add(HT,a===1?treated:neg(control));
  penalty.push(a===1?treated:div(F(BigInt(1-upper)),sub(O,pp)));
  const width=add(div(O,pp),div(O,sub(O,pp)));
  W2=add(W2,mul(width,width));
  const end=i+1===d.n||(i+1>=d.min && d.st[state][a][r]);
  need(end===(i===t-1),'invalid terminal history or hidden early stop');
  state=d.tr[state][a][r];
 }
 penalty.sort((a,b)=>-cmp(a,b));
 let correction=Z;
 for(let i=0;i<Math.min(d.K,penalty.length);i++)correction=add(correction,penalty[i]);
 const results=[];let best=null;
 for(const entry of d.tuning){
  const lambda=entry.lambda,c=entry.c;
  const boundary=add(div(c,lambda),div(mul(lambda,W2),F(8n)));
  const ate=div(sub(sub(sub(HT,correction),boundary),F(BigInt(d.n-t))),F(BigInt(d.n)));
  results.push({lambda:out(lambda),alpha_spend:out(entry.a),log_upper:out(c),
   taylor_terms:entry.terms,exact_exp_lower:out(entry.proof),
   martingale_boundary:out(boundary),ate_lower_bound:out(ate)});
  if(best===null||cmp(ate,best)>0)best=ate;
 }
 return {format:RESULT,status:cmp(best,d.h)>0?'CONDITIONALLY_REJECTED':'INSUFFICIENT_EVIDENCE',
  registered_units:d.n,enrolled_units:t,null_ate_upper:out(d.h),anytime_lower_ate:out(best),
  interval_based_lower_ht:out(HT),worst_case_interval_miss_penalty:out(correction),
  sum_predictable_width_squared:out(W2),conditional_confidence_alpha:out(d.alpha),
  asserted_joint_calibration_failure_bound:out(d.delta),
  unconditional_miscoverage_bound_if_calibration_valid:out(add(d.alpha,d.delta)),
  propensity_trace_sha256:digest(trace),state_visit_counts:visits,tuning_results:results,
  protocol_sha256:protocolPin,evidence_sha256:evidencePin,
  warning:'Research-only conditional confidence sequence. Real assignment propensities, freshness of randomization, fixed cohort/potential outcomes, chronology, measurement calibration, custody, and no interference remain unverified. Reported calibration delta is a premise, not measured evidence.'};
}
module.exports={audit,design,digest,F,out,rat,add,sub,mul,div,cmp,taylor};
if(require.main===module){
 try{need(process.argv.length===6,'usage: node independent.js protocol.json evidence.json PROTOCOL_PIN EVIDENCE_PIN');
 console.log(JSON.stringify(audit(readStrict(process.argv[2]),readStrict(process.argv[3]),
 process.argv[4],process.argv[5]),null,2));}
 catch(err){console.error('REJECTED:',err.message);process.exit(2);}
}
