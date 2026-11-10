'use strict';
/* Independent Node.js BigInt verifier for a report-adaptive STOPPED experiment.
 * Does not import Python or any other EvidenceKernel inference engine. */
const crypto=require('node:crypto');
const {readStrict}=require('./strict_json');
function requireIt(x,msg){if(!x)throw Error(msg);}
function objKeys(x,keys,what){requireIt(x!==null&&typeof x==='object'&&!Array.isArray(x)&&
 Object.keys(x).sort().join('|')===keys.slice().sort().join('|'),what+': unknown/missing fields');}
function encode(x){if(Array.isArray(x))return '['+x.map(encode).join(',')+']';
 if(x!==null&&typeof x==='object')return '{'+Object.keys(x).sort().map(k=>JSON.stringify(k)+':'+encode(x[k])).join(',')+'}';
 return JSON.stringify(x);}
function hash(x){return crypto.createHash('sha256').update(encode(x)).digest('hex');}
function abs(x){return x<0n?-x:x;}
function gcd(x,y){x=abs(x);y=abs(y);while(y){const z=x%y;x=y;y=z;}return x;}
function F(a,b=1n){requireIt(b!==0n,'zero denominator');if(b<0n){a=-a;b=-b;}const d=gcd(a,b);return [a/d,b/d];}
const ZERO=F(0n),ONE=F(1n),NEG=F(-1n);
function plus(x,y){return F(x[0]*y[1]+y[0]*x[1],x[1]*y[1]);}
function times(x,y){return F(x[0]*y[0],x[1]*y[1]);}
function compare(x,y){let v=x[0]*y[1]-y[0]*x[1];return v<0n?-1:v>0n?1:0;}
function repr(x){return x[1]===1n?String(x[0]):String(x[0])+'/'+String(x[1]);}
function readFraction(s){requireIt(typeof s==='string'&&s.length<=32&&/^-?(0|[1-9]\d*)(?:\/[1-9]\d*)?$/.test(s),'bad rational');
 const p=s.split('/'),f=F(BigInt(p[0]),BigInt(p[1]||'1'));requireIt(repr(f)===s,'noncanonical fraction');return f;}
const FORMAT='pcs-evidencekernel-stopping-v23';
function design(p){
 objKeys(p,['format','registered_units','states','initial_state','allocation_weights_by_state',
 'next_state_by_state_action_report','stop_after_by_state_action_report','min_enrollment',
 'potential_schedule_model','statistic','inference_rule','max_interval_misses',
 'null_ate_upper','confidence_alpha'],'registration');
 requireIt(p.format===FORMAT&&p.potential_schedule_model==='fixed_binary_potential_truth_and_report_schedule'&&
  p.statistic==='stopped_binary_mean_difference_integer'&&p.inference_rule==='exact_stopped_path_weak_null_maximization',
  'unsupported protocol');
 const n=p.registered_units,S=p.states,init=p.initial_state,min=p.min_enrollment,K=p.max_interval_misses;
 requireIt(Number.isInteger(n)&&n>=2&&n<=5,'invalid n');
 requireIt(Number.isInteger(S)&&S>=1&&S<=5,'invalid states');
 requireIt(Number.isInteger(init)&&init>=0&&init<S,'invalid initial state');
 requireIt(Number.isInteger(min)&&min>=2&&min<=n,'invalid min_enrollment');
 requireIt(Number.isInteger(K)&&K>=0&&K<=n,'invalid interval budget');
 const alpha=readFraction(p.confidence_alpha),h=readFraction(p.null_ate_upper);
 requireIt(compare(alpha,ZERO)>0&&compare(alpha,ONE)<0&&compare(h,NEG)>=0&&compare(h,ONE)<=0,'invalid alpha/null');
 const wt=p.allocation_weights_by_state,tr=p.next_state_by_state_action_report,st=p.stop_after_by_state_action_report;
 requireIt([wt,tr,st].every(x=>Array.isArray(x)&&x.length===S),'state table dimensions');
 const w=[];
 for(let s=0;s<S;s++){
  const row=wt[s],nxt=tr[s],stop=st[s];
  requireIt(Array.isArray(row)&&row.length===2&&row.every(v=>Number.isInteger(v)&&v>=0&&v<=10000)&&
    row[0]+row[1]>0,'bad allocation weights');
  requireIt(Array.isArray(nxt)&&nxt.length===2&&Array.isArray(stop)&&stop.length===2,'bad state row');
  for(let a=0;a<2;a++){
   requireIt(Array.isArray(nxt[a])&&nxt[a].length===2&&nxt[a].every(v=>Number.isInteger(v)&&v>=0&&v<S),
     'bad state transition');
   requireIt(Array.isArray(stop[a])&&stop[a].length===2&&stop[a].every(v=>typeof v==='boolean'),
     'bad stop rule');
  }
  w.push([F(BigInt(row[0]),BigInt(row[0]+row[1])),F(BigInt(row[1]),BigInt(row[0]+row[1]))]);
 }
 return {n,S,init,min,K,alpha,h,w,tr,st};
}
function stopAt(d,t,s,a,r){return t===d.n||(t>=d.min&&d.st[s][a][r]);}
function evidenceHash(pin,e){return hash({domain:'pcs-evidencekernel-v23-stopped-evidence',protocol_sha256:pin,evidence:e});}
function validate(p,e,d,pin,epin){
 requireIt(typeof pin==='string'&&/^[0-9a-f]{64}$/.test(pin)&&typeof epin==='string'&&/^[0-9a-f]{64}$/.test(epin),
   'externally supplied pins required');
 requireIt(hash(p)===pin,'protocol hash mismatch');requireIt(evidenceHash(pin,e)===epin,'evidence hash mismatch');
 objKeys(e,['assignments','reports','true_intervals'],'evidence');
 const a=e.assignments,r=e.reports,v=e.true_intervals,t=Array.isArray(a)?a.length:-1;
 requireIt(t>=2&&t<=d.n&&Array.isArray(r)&&r.length===t&&Array.isArray(v)&&v.length===t,
   'incomplete or invalid stopped record');
 requireIt(a.concat(r).every(x=>Number.isInteger(x)&&(x===0||x===1)),'bad action or report bit');
 requireIt(v.every(x=>x==='0'||x==='1'||x==='01'),'bad outcome interval');
 let s=d.init,states=[],prob=ONE;
 for(let i=0;i<t;i++){
  states.push(s);requireIt(d.w[s][a[i]][0]>0n,'zero-probability observed action');
  prob=times(prob,d.w[s][a[i]]);
  const stopping=stopAt(d,i+1,s,a[i],r[i]);
  requireIt(i===t-1?stopping:!stopping,i===t-1?'invalid terminal stop':'concealed earlier stop');
  s=d.tr[s][a[i]][r[i]];
 }
 return {a,r,v,states,prob};
}
function law(d,R){const out=new Map();
 function go(i,s,path,prob){for(let a=0;a<2;a++){
  const q=d.w[s][a];if(q[0]===0n)continue;
  const r=R[i][a],next=path+String(a),now=times(prob,q),t=i+1;
  if(stopAt(d,t,s,a,r)){requireIt(!out.has(next),'duplicate terminal path');out.set(next,now);}
  else go(t,d.tr[s][a][r],next,now);
 }}
 go(0,d.init,'',ONE);
 let sum=ZERO;for(const mass of out.values())sum=plus(sum,mass);
 requireIt(compare(sum,ONE)===0,'stopping law not normalized');return out;
}
function score(Y,path){let m=0,n1=0,t=0,c=0;
 for(let i=0;i<path.length;i++){
  if(path[i]==='1'){n1++;t+=Y[i][1];}else{m++;c+=Y[i][0];}
 }
 return n1===0||m===0?0:m*t-n1*c;
}
function* reportWorlds(a,r,n){for(let i=0;i<4**n;i++){
 let val=i,R=Array(n);for(let j=n-1;j>=0;j--){const code=val%4;val=Math.floor(val/4);R[j]=[Math.floor(code/2),code%2];}
 if(a.every((action,j)=>R[j][action]===r[j]))yield R;
}}
function trueWorlds(a,v,n,K){let worlds=[];
 for(let i=0;i<4**n;i++){
  let val=i,Y=Array(n);for(let j=n-1;j>=0;j--){const code=val%4;val=Math.floor(val/4);Y[j]=[Math.floor(code/2),code%2];}
  let misses=0;for(let j=0;j<a.length;j++)if(v[j]!=='01'&&v[j]!==String(Y[j][a[j]]))misses++;
  if(misses<=K)worlds.push(Y);
 }return worlds;
}
function inference(d,a,r,v){const R=[...reportWorlds(a,r,d.n)],Y=trueWorlds(a,v,d.n,d.K);
 requireIt(R.length>0&&Y.length>0,'no compatible schedules');
 requireIt(R.length*Y.length*(2**d.n)<=8000000,'resource bound exceeded');
 const observed=a.join(''),best=new Map();let count=0;
 for(const report of R){const dist=law(d,report);
  requireIt(dist.has(observed),'impossible recorded path');
  for(const truth of Y){
   const ate=truth.reduce((z,[x,y])=>z+y-x,0),actual=score(truth,observed);
   let tail=ZERO;
   for(const [path,mass] of dist)if(score(truth,path)>=actual)tail=plus(tail,mass);
   if(!best.has(ate)||compare(tail,best.get(ate))>0)best.set(ate,tail);
   count++;
  }
 }
 const curve=[];let peak=null,lower=null;
 for(let h=-d.n;h<=d.n;h++){
  if(best.has(h)&&(peak===null||compare(best.get(h),peak)>0))peak=best.get(h);
  const feasible=peak!==null;
  if(feasible&&compare(peak,d.alpha)>0&&lower===null)lower=repr(F(BigInt(h),BigInt(d.n)));
  curve.push({ate_upper:repr(F(BigInt(h),BigInt(d.n))),null_feasible:feasible,max_p:feasible?repr(peak):null});
 }
 let target=null;for(const row of curve)if(compare(readFraction(row.ate_upper),d.h)<=0)target=row;
 return {curve,target,lower,count,reportCount:R.length};
}
function audit(p,e,pin,epin){const d=design(p),obs=validate(p,e,d,pin,epin),
 result=inference(d,obs.a,obs.r,obs.v);
 return {format:'pcs-evidencekernel-stopping-audit-v23',
  status:result.target.null_feasible?'CONDITIONALLY_VERIFIED':'NULL_INCOMPATIBLE',
  conditional_p:result.target.max_p,conditional_lower_ate:result.lower,
  null_ate_upper:repr(d.h),confidence_alpha:repr(d.alpha),
  registered_units:d.n,enrolled_units:obs.a.length,
  compatible_joint_worlds:result.count,compatible_report_schedules:result.reportCount,
  actual_stopped_history_probability_given_observed_reports:repr(obs.prob),
  state_trace:obs.states,null_curve:result.curve,
  protocol_sha256:pin,evidence_sha256:epin,
  warning:'Conditional exact stopped-path inference, not proof of physical randomization, external chronology, data authenticity, calibration, independent assignment randomness or scientific effects. All potential scientific outcomes and policy reports are modeled as fixed and stable across assignments.'};
}
module.exports={design,validate,law,score,inference,audit,hash,evidenceHash,reportWorlds,trueWorlds,repr};
if(require.main===module){try{let [p,e,pin,epin]=process.argv.slice(2);
 console.log(JSON.stringify(audit(readStrict(p),readStrict(e),pin,epin),null,2));
 }catch(err){console.error('REJECTED:',err.message);process.exit(2);}}
