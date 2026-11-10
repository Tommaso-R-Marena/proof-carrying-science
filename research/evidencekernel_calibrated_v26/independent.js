'use strict';
/* Independent exact BigInt calibration and v25 reference integration.
   A pretrial record and SHA pins do NOT establish chronological custody. */
const crypto=require('node:crypto');
const {readStrict}=require('../evidencekernel_propensity_v25/strict_json');
const v25=require('../evidencekernel_propensity_v25/independent');
const FORMAT='pcs-evidencekernel-prestudy-propensity-calibration-v26';
const RESULT='pcs-evidencekernel-calibrated-inference-audit-v26';
const SAMPLING='prestudy_fixed_size_stationary_statewise_bernoulli';
function need(v,msg){if(!v)throw Error(msg);}
function keys(o,fields,msg){need(o!==null&&typeof o==='object'&&!Array.isArray(o)&&
  Object.keys(o).sort().join('|')===fields.slice().sort().join('|'),msg);}
function canon(v){if(Array.isArray(v))return '['+v.map(canon).join(',')+']';
 if(v!==null&&typeof v==='object')return '{'+Object.keys(v).sort().map(k=>JSON.stringify(k)+':'+canon(v[k])).join(',')+'}';
 return JSON.stringify(v);}
function digest(v){return crypto.createHash('sha256').update(canon(v)).digest('hex');}
function pin(p){need(typeof p==='string'&&/^[0-9a-f]{64}$/.test(p),'external SHA256 pins required');}
function recordPin(c,records){return digest({domain:'pcs-evidencekernel-v26-prestudy-records',contract_sha256:c,records});}
const F=v25.F,rat=v25.rat,out=v25.out,add=v25.add,cmp=v25.cmp;
const Z=F(0n),O=F(1n),Q=F(1n,4n);
function int(v,lo,hi){need(typeof v==='number'&&Number.isSafeInteger(v)&&v>=lo&&v<=hi,'invalid bounded integer');return v;}
function tailNumerator(n,x,q,D){int(n,1,4096);int(x,0,n);int(q,0,D);int(D,16,4096);
  let combination=1n,total=0n;
  for(let j=0;j<=x;j++){
    total+=combination*(BigInt(q)**BigInt(j))*(BigInt(D-q)**BigInt(n-j));
    combination=combination*BigInt(n-j)/BigInt(j+1);
  }
  return total;
}
function findUpper(n,x,beta,D){const denom=BigInt(D)**BigInt(n);
 let lo=1,hi=D;
 while(lo<hi){const mid=Math.floor((lo+hi)/2);
  const num=tailNumerator(n,x,mid,D);
  if(num*beta[1]<=denom*beta[0])hi=mid;else lo=mid+1;
 }
 const upper=F(BigInt(lo),BigInt(D)),tail=F(tailNumerator(n,x,lo,D),denom);
 need(lo===D||cmp(tail,beta)<=0,'tail threshold rejected');
 if(lo>1){const prev=F(tailNumerator(n,x,lo-1,D),denom);need(cmp(prev,beta)>0,'non-minimal upper');}
 return [upper,tail];
}
function calibrate(c,r,contractPin,recordsPin){pin(contractPin);pin(recordsPin);
 need(digest(c)===contractPin,'calibration contract pin mismatch');
 need(recordPin(contractPin,r)===recordsPin,'calibration record pin mismatch');
 keys(c,['format','state_count','minimum_sample_sizes','maximum_sample_sizes',
  'sample_size_policy','beta_spend_by_state','grid_denominator',
  'sampling_model','require_nontrivial_ceiling'],'calibration contract keys');
 keys(r,['assignment_bits_by_state','stage'],'calibration records keys');
 need(c.format===FORMAT&&c.sampling_model===SAMPLING&&r.stage==='prestudy','unsupported calibration model');
 const states=int(c.state_count,1,16),D=int(c.grid_denominator,16,4096);
 need(Array.isArray(c.minimum_sample_sizes)&&c.minimum_sample_sizes.length===states&&
  Array.isArray(c.maximum_sample_sizes)&&c.maximum_sample_sizes.length===states&&
  Array.isArray(c.beta_spend_by_state)&&c.beta_spend_by_state.length===states&&
  Array.isArray(r.assignment_bits_by_state)&&r.assignment_bits_by_state.length===states,
  'calibration state counts');
 need(typeof c.require_nontrivial_ceiling==='boolean','invalid nontrivial policy');
 need(['fixed_per_state','anytime_within_registered_range'].includes(c.sample_size_policy),
  'unsupported calibration stopping policy');
 const caps=[],replayed=[];let spent=Z;
 for(let s=0;s<states;s++){
  const min=int(c.minimum_sample_sizes[s],16,4096),max=int(c.maximum_sample_sizes[s],min,4096);
  if(c.sample_size_policy==='fixed_per_state')need(min===max,'fixed calibration size mismatch');
  const arr=r.assignment_bits_by_state[s];
  need(Array.isArray(arr)&&arr.length>=min&&arr.length<=max,'truncated or unregistered sample size');
  const n=arr.length;
  const beta=rat(c.beta_spend_by_state[s]);
  need(cmp(beta,Z)>0&&cmp(beta,Q)<=0,'beta spend');
  need(Array.isArray(arr)&&arr.length===n&&arr.every(x=>x===0||x===1),'truncated/invalid calibration stream');
  const successes=arr.reduce((a,b)=>a+b,0);
  const permittedLooks=max-min+1,spend=F(beta[0],beta[1]*BigInt(permittedLooks));
  const [upper,tail]=findUpper(n,successes,spend,D);
  if(c.require_nontrivial_ceiling)need(cmp(upper,O)<0,'vacuous ceiling forbidden');
  caps.push(out(upper));
  replayed.push({state:s,sample_size:n,treated_count:successes,beta_spend:out(beta),permitted_calibration_looks:permittedLooks,
   effective_tail_threshold:out(spend),ceiling:out(upper),binomial_lower_tail_at_ceiling:out(tail)});
  spent=add(spent,beta);
 }
 return {format:FORMAT,propensity_ceiling_by_state:caps,statewise_calibration:replayed,
 total_propensity_failure_budget:out(spent),
 calibration_sample_size_policy:c.sample_size_policy,contract_sha256:contractPin,records_sha256:recordsPin,
 stationarity_assumption:'fixed-state conditional Bernoulli probabilities carry over from pretrial to study'};
}
function audit(c,r,p,e,cp,crp,pp,ep){const cal=calibrate(c,r,cp,crp);
 pin(pp);pin(ep);
 need(digest(p)===pp,'v25 study contract pin mismatch');
 need(p.states===c.state_count,'calibration/study state mismatch');
 need(Array.isArray(p.propensity_upper_by_state)&&
  JSON.stringify(p.propensity_upper_by_state)===JSON.stringify(cal.propensity_ceiling_by_state),
  'v25 propensity ceilings must match derived caps');
 const study=v25.audit(p,e,pp,ep);
 const alpha=rat(study.conditional_confidence_alpha),delta=rat(study.asserted_joint_calibration_failure_bound),
  beta=rat(cal.total_propensity_failure_budget),sum=add(add(alpha,delta),beta);
 need(cmp(sum,O)<=0,'total error budget > 1');
 return {format:RESULT,status:study.status,calibration:cal,study_v25:study,
 conditional_statistical_error:out(alpha),asserted_measurement_failure_budget:out(delta),
 derived_propensity_calibration_failure_budget:out(beta),
 joint_failure_bound_if_all_physical_assumptions_hold:out(sum),
 warning:'PRESTUDY SEPARATION, STATIONARY STATEWISE PROPENSITIES, HONEST RECORDING, independent physical randomness, stable potential outcomes, measurement calibration and authenticated timestamps are NOT established by these hashes. No real scientific claim is certified by the synthetic demonstration.'};
}
module.exports={calibrate,audit,tailNumerator,findUpper,recordPin,digest};
if(require.main===module){try{
 need(process.argv.length===10,'usage: node independent.js CAL_CONTRACT CAL_RECORDS STUDY_CONTRACT STUDY_RECORDS PIN1 PIN2 PIN3 PIN4');
 const [c,r,p,e]=process.argv.slice(2,6).map(readStrict);
 console.log(JSON.stringify(audit(c,r,p,e,...process.argv.slice(6,10)),null,2));
}catch(err){console.error('REJECTED:',err.message);process.exit(2);}}
