'use strict';
/* Independent BigInt verifier of exact potential-report-aware response-adaptive
 * causal inference. No Python or production PCS dependency. Research only. */
const crypto=require('node:crypto');
const {readStrict}=require('./strict_json');
function insist(c,m){if(!c)throw Error(m);}
function exact(o,keys){insist(o!==null&&typeof o==='object'&&!Array.isArray(o)&&
  Object.keys(o).sort().join('|')===keys.slice().sort().join('|'),'unexpected/missing keys');}
function canonical(v){if(Array.isArray(v))return '['+v.map(canonical).join(',')+']';
 if(v!==null&&typeof v==='object')return '{'+Object.keys(v).sort().map(k=>JSON.stringify(k)+':'+canonical(v[k])).join(',')+'}';
 return JSON.stringify(v);}
function digest(v){return crypto.createHash('sha256').update(canonical(v)).digest('hex');}
function abs(a){return a<0n?-a:a;}
function gcd(a,b){a=abs(a);b=abs(b);while(b){let t=a%b;a=b;b=t;}return a;}
function f(a,b=1n){insist(b!==0n,'zero denominator');if(b<0n){a=-a;b=-b;}
 const g=gcd(a,b);return [a/g,b/g];}
function add(x,y){return f(x[0]*y[1]+y[0]*x[1],x[1]*y[1]);}
function mul(x,y){return f(x[0]*y[0],x[1]*y[1]);}
function cmp(x,y){return x[0]*y[1]-y[0]*x[1];}
function str(x){return x[1]===1n?String(x[0]):String(x[0])+'/'+String(x[1]);}
const ZERO=f(0n),ONE=f(1n);
function parse(s){insist(typeof s==='string'&&s.length<=32&&/^-?(0|[1-9]\d*)(?:\/[1-9]\d*)?$/.test(s),'noncanonical rational');
 const p=s.split('/'),r=f(BigInt(p[0]),BigInt(p[1]??'1'));
 insist(str(r)===s,'noncanonical rational');return r;}
function design(p){
 exact(p,['format','n','states','initial_state','allocation_weights_by_state',
 'next_state_by_state_action_report','observation_model','null_ate_upper',
 'confidence_alpha','max_interval_misses','statistic','inference_rule']);
 insist(p.format==='pcs-evidencekernel-feedback-v22'&&p.observation_model==='unrestricted_deterministic_binary_potential_reports'&&
 p.statistic==='sample_mean_difference_integer'&&p.inference_rule==='exact_robust_potential_report_randomization','unsupported policy');
 const n=p.n,S=p.states,init=p.initial_state,K=p.max_interval_misses;
 insist(Number.isInteger(n)&&n>=2&&n<=5,'invalid n');
 insist(Number.isInteger(S)&&S>=1&&S<=6,'invalid states');
 insist(Number.isInteger(init)&&init>=0&&init<S,'invalid initial state');
 insist(Number.isInteger(K)&&K>=0&&K<=n,'invalid miss budget');
 const alpha=parse(p.confidence_alpha),nullATE=parse(p.null_ate_upper);
 insist(cmp(alpha,ZERO)>0n&&cmp(alpha,ONE)<0n&&cmp(nullATE,f(-1n))>=0n&&cmp(nullATE,ONE)<=0n,'invalid alpha/null');
 const weights=p.allocation_weights_by_state,trans=p.next_state_by_state_action_report;
 insist(Array.isArray(weights)&&weights.length===S&&Array.isArray(trans)&&trans.length===S,'state rows');
 const w=[];
 for(let s=0;s<S;s++){
  let row=weights[s],r=trans[s];
  insist(Array.isArray(row)&&row.length===2&&row.every(x=>Number.isInteger(x)&&x>=0&&x<=10000)&&row[0]+row[1]>0,'invalid treatment weights');
  insist(Array.isArray(r)&&r.length===2&&r.every(a=>Array.isArray(a)&&a.length===2&&a.every(t=>Number.isInteger(t)&&t>=0&&t<S)),'invalid transitions');
  w.push([f(BigInt(row[0]),BigInt(row[0]+row[1])),f(BigInt(row[1]),BigInt(row[0]+row[1]))]);
 }
 return {n,S,init,K,alpha,nullATE,w,trans};
}
function evidenceCommitment(pin,e){return digest({domain:'pcs-evidencekernel-v22-outcome-feedback-evidence',protocol_sha256:pin,evidence:e});}
function validate(p,e,d,protocolPin,evidencePin){
 insist(typeof protocolPin==='string'&&/^[a-f0-9]{64}$/.test(protocolPin)&&
        typeof evidencePin==='string'&&/^[a-f0-9]{64}$/.test(evidencePin),'missing external pins');
 insist(digest(p)===protocolPin,'protocol pin mismatch');
 insist(evidenceCommitment(protocolPin,e)===evidencePin,'evidence pin mismatch');
 exact(e,['assignments','reports','true_intervals']);const {n}=d;
 const a=e.assignments,r=e.reports,labels=e.true_intervals;
 insist(Array.isArray(a)&&a.length===n&&a.every(v=>Number.isInteger(v)&&(v===0||v===1)),'invalid allocations');
 insist(Array.isArray(r)&&r.length===n&&r.every(v=>Number.isInteger(v)&&(v===0||v===1)),'invalid reports');
 insist(Array.isArray(labels)&&labels.length===n&&labels.every(v=>v==='0'||v==='1'||v==='01'),'invalid truth intervals');
 let s=d.init,prob=ONE,states=[];
 for(let i=0;i<n;i++){states.push(s);insist(d.w[s][a[i]][0]>0n,'impossible assignment');
  prob=mul(prob,d.w[s][a[i]]);s=d.trans[s][a[i]][r[i]];}
 return {a,r,labels,states,prob};
}
function law(d,reportWorld){let output=new Map();
 function rec(i,s,actions,prob){if(i===d.n){output.set(actions,prob);return;}
  for(let a=0;a<=1;a++){let q=d.w[s][a];if(q[0]!==0n)
   rec(i+1,d.trans[s][a][reportWorld[i][a]],actions+String(a),mul(prob,q));}}
 rec(0,d.init,'',ONE);
 let total=ZERO;for(let prob of output.values())total=add(total,prob);
 insist(cmp(total,ONE)===0n,'world mass not normalized');return output;
}
function stat(world,bits){let t=0,c=0,n1=0;
 for(let i=0;i<bits.length;i++){if(bits[i]==='1'){t+=world[i][1];n1++;}else c+=world[i][0];}
 const n0=bits.length-n1;return n1===0||n0===0?0:n0*t-n1*c;
}
function* reportWorlds(a,r){const n=a.length;
 for(let idx=0;idx<2**n;idx++){
  const world=[];
  for(let i=0;i<n;i++){let hidden=(idx>>(n-1-i))&1;
   world.push(a[i]===0?[r[i],hidden]:[hidden,r[i]]);}
  yield world;
 }}
function trueWorlds(a,labels,K){const n=a.length,worlds=[];
 for(let idx=0;idx<4**n;idx++){
  let v=idx,world=Array(n);
  for(let i=n-1;i>=0;i--){let c=v%4;v=Math.floor(v/4);world[i]=[Math.floor(c/2),c%2];}
  let misses=0;
  for(let i=0;i<n;i++)if(labels[i]!=='01'&&labels[i]!==String(world[i][a[i]]))misses++;
  if(misses<=K)worlds.push(world);
 }return worlds;
}
function audit(p,e,pin,epin){const d=design(p),v=validate(p,e,d,pin,epin);
 const target=v.a.join(''),trueModels=trueWorlds(v.a,v.labels,d.K);
 insist(trueModels.length>0,'no compatible scientific worlds');
 const best=new Map();let count=0;
 for(const reportWorld of reportWorlds(v.a,v.r)){
  const distribution=law(d,reportWorld);
  insist(distribution.has(target),'observed assignment not possible');
  for(const world of trueModels){
   const ate=world.reduce((t,y)=>t+y[1]-y[0],0);
   const observed=stat(world,target);let tail=ZERO;
   for(const [assignment,prob] of distribution)if(stat(world,assignment)>=observed)tail=add(tail,prob);
   if(!best.has(ate)||cmp(tail,best.get(ate))>0n)best.set(ate,tail);
   count++;
  }
 }
 let peak=null,lower=null;const curve=[];
 for(let h=-d.n;h<=d.n;h++){
  if(best.has(h)&&(peak===null||cmp(best.get(h),peak)>0n))peak=best.get(h);
  const feasible=peak!==null;
  if(feasible&&cmp(peak,d.alpha)>0n&&lower===null)lower=f(BigInt(h),BigInt(d.n));
  curve.push({ate_upper:str(f(BigInt(h),BigInt(d.n))),null_feasible:feasible,max_p:feasible?str(peak):null});
 }
 let selected=null;
 for(const row of curve)if(cmp(parse(row.ate_upper),d.nullATE)<=0n)selected=row;
 insist(selected!==null,'invalid null cutoff');
 return {format:'pcs-evidencekernel-response-adaptive-audit-v22',
  status:selected.null_feasible?'CONDITIONALLY_VERIFIED':'NULL_INCOMPATIBLE',
  conditional_p:selected.max_p,conditional_lower_ate:lower!==null?str(lower):null,
  null_ate_upper:str(d.nullATE),confidence_alpha:str(d.alpha),
  compatible_joint_worlds:count,
  actual_assignment_probability_given_observed_feedback:str(v.prob),
  state_trace:v.states,null_curve:curve,protocol_sha256:pin,evidence_sha256:epin,
  warning:'Research-only. Inference conditions on fixed complete potential-outcome and potential-report schedules, sequential independent assignment randomness, protocol pin before enrollment, and complete retained reports; physical authenticity and potential-outcome stability are not established by hashes.'};
}
module.exports={design,evidenceCommitment,validate,law,stat,audit,digest,parse,str};
if(require.main===module){try{const [protocol,evidence,pin,epin]=process.argv.slice(2);
 console.log(JSON.stringify(audit(readStrict(protocol),readStrict(evidence),pin,epin),null,2));}
 catch(e){console.error('REJECTED:',e.message);process.exit(2);}}
