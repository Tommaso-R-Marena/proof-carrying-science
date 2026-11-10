'use strict';
/* Independent exact BigInt replay; research-only. No physical custody claim. */
const crypto=require('node:crypto');
const {readStrict}=require('../evidencekernel_propensity_v25/strict_json');
const v25=require('../evidencekernel_propensity_v25/independent');
const F=v25.F,rat=v25.rat,out=v25.out,add=v25.add,mul=v25.mul,div=v25.div,cmp=v25.cmp;
const Z=F(0n), O=F(1n), Q=F(1n,4n);
const FORMAT='pcs-evidencekernel-anytime-mixture-calibration-v27';
const RESULT='pcs-evidencekernel-anytime-mixture-audit-v27';
const SAMPLING='prestudy_statewise_stationary_conditional_bernoulli';
function need(test,msg){if(!test)throw Error(msg);}
function keys(v,fields,label){need(v&&typeof v==='object'&&!Array.isArray(v)&&
 Object.keys(v).sort().join('|')===fields.slice().sort().join('|'),'invalid keys: '+label);}
function bounded(v,lo,hi){need(typeof v==='number'&&Number.isSafeInteger(v)&&v>=lo&&v<=hi,'invalid bounded integer');return v;}
function pin(s){need(typeof s==='string'&&/^[0-9a-f]{64}$/.test(s),'invalid external pin');}
function canonical(v){if(Array.isArray(v))return '['+v.map(canonical).join(',')+']';
 if(v!==null&&typeof v==='object')return '{'+Object.keys(v).sort().map(x=>JSON.stringify(x)+':'+canonical(v[x])).join(',')+'}';
 return JSON.stringify(v);}
function digest(v){return crypto.createHash('sha256').update(canonical(v)).digest('hex');}
function recordPin(cp,records){return digest({domain:'pcs-evidencekernel-v27-raw-calibration',contract_sha256:cp,records});}
function powFrac(a,n){return F(a[0]**BigInt(n),a[1]**BigInt(n));}
function eUpper(n,s,u,ratios){bounded(n,0,4096);bounded(s,0,n);need(cmp(u,Z)>0&&cmp(u,O)<0,'interior u');
 let total=Z,failures=n-s;
 for(const c of ratios){const oneMinusCu=v25.sub(O,mul(c,u));const oneMinusU=v25.sub(O,u);
  const value=mul(powFrac(c,s),powFrac(div(oneMinusCu,oneMinusU),failures));total=add(total,value);}
 return div(total,F(BigInt(ratios.length)));}
function invertUpper(n,s,beta,D,ratios){let lo=1,hi=D;const target=div(O,beta);
 while(lo<hi){const mid=Math.floor((lo+hi)/2);
  if(cmp(eUpper(n,s,F(BigInt(mid),BigInt(D)),ratios),target)>=0)hi=mid;else lo=mid+1;}
 const upper=F(BigInt(lo),BigInt(D)),reached=lo<D;
 const value=reached?eUpper(n,s,upper,ratios):O;
 need(!reached||cmp(value,target)>=0,'mixture inversion');
 if(lo>1)need(cmp(eUpper(n,s,F(BigInt(lo-1),BigInt(D)),ratios),target)<0,'non-minimal cap');
 return [upper,value,reached];}
function params(c){keys(c,['format','sampling_model','state_count','minimum_sample_sizes','maximum_sample_sizes','beta_spend_by_state',
 'grid_denominator','e_mixture_ratios','drift_mixture_ratios','drift_alarm_spend_by_state','require_nontrivial_ceiling'],'contract');
 need(c.format===FORMAT&&c.sampling_model===SAMPLING,'sampling model');
 const S=bounded(c.state_count,1,16),D=bounded(c.grid_denominator,16,4096);
 need(typeof c.require_nontrivial_ceiling==='boolean','nontrivial policy');
 const items=['minimum_sample_sizes','maximum_sample_sizes','beta_spend_by_state','drift_alarm_spend_by_state'];
 for(const k of items)need(Array.isArray(c[k])&&c[k].length===S,'state arrays');
 const mins=[],maxs=[];
 for(let s=0;s<S;s++){mins.push(bounded(c.minimum_sample_sizes[s],16,4096));
  maxs.push(bounded(c.maximum_sample_sizes[s],mins[s],4096));}
 const betas=c.beta_spend_by_state.map(rat),gammas=c.drift_alarm_spend_by_state.map(rat);
 need([...betas,...gammas].every(x=>cmp(x,Z)>0&&cmp(x,Q)<=0),'risk budgets');
 const lists=[];
 for(const key of ['e_mixture_ratios','drift_mixture_ratios']){
  const a=c[key];need(Array.isArray(a)&&a.length>=1&&a.length<=16,'mixture size');
  const values=a.map(rat);
  need(values.every(x=>cmp(x,Z)>0&&cmp(x,O)<0)&&new Set(values.map(out)).size===values.length,'mixture ratios');lists.push(values);}
 return {S,D,mins,maxs,betas,gammas,ratios:lists[0],drift:lists[1],nontrivial:c.require_nontrivial_ceiling};}
function calibrate(c,records,cp,rp){pin(cp);pin(rp);need(digest(c)===cp,'contract pin mismatch');
 need(recordPin(cp,records)===rp,'calibration records pin mismatch');
 const d=params(c);keys(records,['stage','assignment_bits_by_state'],'records');
 need(records.stage==='prestudy','non-prestudy records');
 const arrays=records.assignment_bits_by_state;need(Array.isArray(arrays)&&arrays.length===d.S,'statewise streams');
 const ceilings=[],replayed=[];let spent=Z;
 for(let s=0;s<d.S;s++){
  const arr=arrays[s];need(Array.isArray(arr)&&arr.length>=d.mins[s]&&arr.length<=d.maxs[s]&&
   arr.every(x=>x===0||x===1),'truncated/invalid streams');
  const n=arr.length,successes=arr.reduce((a,b)=>a+b,0);
  const [u,e,cross]=invertUpper(n,successes,d.betas[s],d.D,d.ratios);
  if(d.nontrivial)need(cmp(u,O)<0,'vacuous cap');
  ceilings.push(out(u));replayed.push({state:s,sample_size:n,treated_count:successes,
   calibration_beta:out(d.betas[s]),calibration_mixture_e_at_ceiling:out(e),
   mixture_boundary_crossed:cross,ceiling:out(u),per_look_penalty:'none (Ville anytime-valid e-mixture)'});
  spent=add(spent,d.betas[s]);}
 return {format:FORMAT,propensity_ceiling_by_state:ceilings,statewise_calibration:replayed,
  joint_propensity_failure_budget:out(spent),
  statewise_drift_alarm_budgets:d.gammas.map(out),contract_sha256:cp,records_sha256:rp,
  assurance:'conditional on stable statewise Bernoulli probability carrying from prestudy to trial'};}
function driftReplay(p,records,ceilings,gammas,ratios){
 const S=ceilings.length,capitals=Array.from({length:S},()=>ratios.map(()=>O));
 const maxE=Array.from({length:S},()=>O),firstAlarm=Array.from({length:S},()=>null),counts=Array.from({length:S},()=>0);
 let state=p.initial_state;
 for(let j=0;j<records.assignments.length;j++){
  const a=records.assignments[j],r=records.reports[j],cap=ceilings[state];counts[state]++;
  if(cmp(cap,O)<0){
   for(let h=0;h<ratios.length;h++){
    const alternative=add(cap,mul(ratios[h],v25.sub(O,cap)));
    const multiplier=a?div(alternative,cap):div(v25.sub(O,alternative),v25.sub(O,cap));
    capitals[state][h]=mul(capitals[state][h],multiplier);
   }
   const evidence=div(capitals[state].reduce(add,Z),F(BigInt(ratios.length)));
   if(cmp(evidence,maxE[state])>0)maxE[state]=evidence;
   if(firstAlarm[state]===null && cmp(evidence,div(O,gammas[state]))>=0)firstAlarm[state]=j+1;
  }
  state=p.next_state_by_state_action_report[state][a][r];
 }
 return {alarm:firstAlarm.some(x=>x!==null),first_alarm_enrollment_by_state:firstAlarm,
  max_e_value_by_state:maxE.map(out),observations_by_state:counts,
  calibration_warning:'No alarm does not establish stationarity or correct true assignment probabilities.'};}
function audit(c,r,p,e,cp,rp,pp,ep){const cal=calibrate(c,r,cp,rp);
 pin(pp);pin(ep);need(digest(p)===pp,'study pin mismatch');
 need(p.states===c.state_count,'state mismatch');
 need(JSON.stringify(p.propensity_upper_by_state)===JSON.stringify(cal.propensity_ceiling_by_state),'mismatched calibration ceilings');
 const study=v25.audit(p,e,pp,ep),d=params(c);
 const monitor=driftReplay(p,e,cal.propensity_ceiling_by_state.map(rat),d.gammas,d.drift);
 const alpha=rat(study.conditional_confidence_alpha),delta=rat(study.asserted_joint_calibration_failure_bound);
 const beta=rat(cal.joint_propensity_failure_budget),sum=add(add(alpha,delta),beta);
 need(cmp(sum,O)<=0,'joint confidence budget exceeds one');
 return {format:RESULT,status:monitor.alarm?'DRIFT_ALARM_NO_CLAIM':study.status,
  calibration:cal,drift_monitor:monitor,study_v25:study,
  scientific_type_i_upper_if_premises_hold:out(sum),
  extra_drift_false_alarm_budget_if_stationary_and_calibration_valid:out(d.gammas.reduce(add,Z)),
  warning:'Research only: recorded hashes do not establish chronology, independent custody, physical assignment law, stability, actual endpoint truth, or measurement calibration. No drift alarm NEVER establishes those premises.'};}
module.exports={eUpper,invertUpper,params,calibrate,driftReplay,audit,recordPin,digest};
if(require.main===module){try{
 need(process.argv.length===10,'expected four paths and four pins');
 const [c,r,p,e]=process.argv.slice(2,6).map(readStrict);
 console.log(JSON.stringify(audit(c,r,p,e,...process.argv.slice(6,10)),null,2));
}catch(err){console.error('REJECTED:',err.message);process.exit(2);}}
