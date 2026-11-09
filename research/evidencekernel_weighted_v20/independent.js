'use strict';
// Independent exact BigInt audit of preregistered nonstationary weighted stopping.
// No production PCS authority; no claims of independently controlled randomness.
const crypto=require('node:crypto');
const {readStrict}=require('../evidencekernel_selective_v17/strict_json');
function insist(c,m){if(!c)throw Error(m);}
function canonical(v){if(Array.isArray(v))return '['+v.map(canonical).join(',')+']';
 if(v&&typeof v==='object')return '{'+Object.keys(v).sort().map(k=>JSON.stringify(k)+':'+canonical(v[k])).join(',')+'}'; return JSON.stringify(v);}
function digest(v){return crypto.createHash('sha256').update(canonical(v)).digest('hex');}
function exact(v,keys){insist(v&&typeof v==='object'&&!Array.isArray(v)&&Object.keys(v).sort().join('|')===keys.sort().join('|'),'invalid object keys');}
function gcd(a,b){if(a<0n)a=-a;if(b<0n)b=-b;while(b){[a,b]=[b,a%b];}return a;}
function rat(n,d){insist(d>0n,'nonpositive fraction denominator');const g=gcd(n,d);n/=g;d/=g;return d===1n?String(n):String(n)+'/'+String(d);}
function parseRat(s){insist(typeof s==='string'&&s.length<=30&&/^-?(0|[1-9]\d*)(?:\/[1-9]\d*)?$/.test(s),'invalid rational');const t=s.split('/');const n=BigInt(t[0]),d=BigInt(t[1]||1);insist(rat(n,d)===s,'noncanonical rational');return [n,d];}
function cmp(a,b){return a[0]*b[1]-b[0]*a[1];}
function assigns(n,k){const out=[];function rec(start,z){if(z.length===k){out.push(z);return;}for(let i=start;i<=n-(k-z.length);i++)rec(i+1,z.concat(i));}rec(0,[]);return out;}
const PFIELDS=['format','n','k','baseline_covariate','max_attempts','accept_if_score_le','selection_rule','candidate_law','candidate_weights_by_step','null_ate_upper','max_interval_misses','confidence_alpha','tie_rule'];
function design(p){exact(p,PFIELDS);
 insist(p.format==='pcs-evidencekernel-weighted-stopping-v20'&&p.selection_rule==='first_acceptable_else_last'&&p.tie_rule==='weighted_conditional_rejected_prefix_right_cdf','unsupported rule');
 insist(p.candidate_law==='registered_independent_weighted_by_step','unsupported weighted sampling');
 const n=p.n,k=p.k,H=p.max_attempts;
 insist(Number.isSafeInteger(n)&&n>=2&&n<=8&&Number.isSafeInteger(k)&&k>0&&k<n&&Number.isSafeInteger(H)&&H>=1&&H<=128,'bad trial dimensions');
 const x=p.baseline_covariate;
 insist(Array.isArray(x)&&x.length===n&&x.every(v=>Number.isSafeInteger(v)&&v>=-16&&v<=16),'bad baseline');
 insist(Number.isSafeInteger(p.accept_if_score_le)&&p.accept_if_score_le>=0&&p.accept_if_score_le<=10000,'bad acceptance cutoff');
 insist(Number.isSafeInteger(p.max_interval_misses)&&p.max_interval_misses>=0&&p.max_interval_misses<=n,'bad miss budget');
 const alpha=parseRat(p.confidence_alpha),nullUpper=parseRat(p.null_ate_upper);
 insist(cmp(alpha,[0n,1n])>0n&&cmp(alpha,[1n,1n])<0n&&cmp(nullUpper,[-1n,1n])>=0n&&cmp(nullUpper,[1n,1n])<=0n,'bad alpha/null');
 const space=assigns(n,k),N=space.length;
 insist(N*4**n<=5000000,'too many latent worlds');
 const rows=p.candidate_weights_by_step;
 insist(Array.isArray(rows)&&rows.length===H,'missing per-step weights');
 const weights=[],W=[];
 for(const row of rows){insist(Array.isArray(row)&&row.length===N&&row.every(q=>Number.isSafeInteger(q)&&q>=0&&q<=10000),'invalid weight row');
  const big=row.map(q=>BigInt(q)),s=big.reduce((a,b)=>a+b,0n);insist(s>0n,'empty weighted draw');weights.push(big);W.push(s);}
 const sumX=x.reduce((a,b)=>a+b,0),scores=space.map(z=>Math.abs(n*z.reduce((a,i)=>a+x[i],0)-k*sumX));
 const accepted=scores.map(v=>v<=p.accept_if_score_le);
 const R=weights.map(row=>row.reduce((a,q,i)=>a+(!accepted[i]?q:0n),0n));
 let total=1n;for(const v of W)total*=v;
 insist(total.toString(2).length<=32768,'design denominator too large');
 const mass=Array(N).fill(0n);let prefix=1n;
 for(let t=0;t<H;t++){let suffix=1n;for(let j=t+1;j<H;j++)suffix*=W[j];
  for(let i=0;i<N;i++)if(t===H-1||accepted[i])mass[i]+=prefix*weights[t][i]*suffix;
  prefix*=R[t];}
 insist(mass.reduce((a,b)=>a+b,0n)===total,'design normalization failed');
 return {n,k,H,N,space,weights,W,R,accepted,mass,total,alpha,nullUpper,K:p.max_interval_misses};}
function attemptCommit(protocolPin,attempts){return digest({domain:'pcs-evidencekernel-v20-registered-weighted-attempts',protocol_sha256:protocolPin,attempts});}
function validate(p,e,d,protocolPin,attemptsPin){insist(/^[a-f0-9]{64}$/.test(protocolPin)&&/^[a-f0-9]{64}$/.test(attemptsPin),'external pins required');
 insist(digest(p)===protocolPin,'protocol pin mismatch');exact(e,['attempts','selected_assignment','observed_intervals']);
 insist(Array.isArray(e.attempts)&&e.attempts.length>=1&&e.attempts.length<=d.H,'incomplete attempts');
 insist(Array.isArray(e.observed_intervals)&&e.observed_intervals.length===d.n&&e.observed_intervals.every(v=>v==='0'||v==='1'||v==='01'),'invalid intervals');
 insist(Array.isArray(e.selected_assignment)&&d.space.some(z=>JSON.stringify(z)===JSON.stringify(e.selected_assignment)),'bad terminal assignment');
 const ids=e.attempts.map((z,j)=>{insist(Array.isArray(z),'invalid attempt');const i=d.space.findIndex(a=>JSON.stringify(a)===JSON.stringify(z));
  insist(i>=0,'unknown assignment');insist(d.weights[j][i]>0n,'zero-probability recorded draw');return i;});
 insist(ids.slice(0,-1).every(i=>!d.accepted[i]),'early accepted candidate omitted');
 insist(ids.length===d.H||d.accepted[ids.at(-1)],'premature stopping');
 insist(JSON.stringify(e.selected_assignment)===JSON.stringify(e.attempts.at(-1)),'terminal selection mismatch');
 insist(attemptCommit(protocolPin,e.attempts)===attemptsPin,'attempt pin mismatch');return ids;}
function prefixCDF(d,ids){const L=ids.length-1;if(L===0)return [1n,1n];
 let denominator=1n;for(let j=0;j<L;j++){insist(d.R[j]>0n,'impossible rejection');denominator*=d.R[j];}
 let left=0n,prev=1n;
 for(let j=0;j<L;j++){
  let smaller=0n;for(let i=0;i<ids[j];i++)if(!d.accepted[i])smaller+=d.weights[j][i];
  let suffix=1n;for(let h=j+1;h<L;h++)suffix*=d.R[h];
  left+=prev*smaller*suffix;prev*=d.weights[j][ids[j]];}
 const numerator=left+prev;insist(numerator>0n&&numerator<=denominator,'invalid conditional right CDF');return [numerator,denominator];}
function stat(w,z,n,k){const s=new Set(z);let t=0,c=0;for(let i=0;i<n;i++)if(s.has(i))t+=w[i][1];else c+=w[i][0];return (n-k)*t-k*c;}
function audit(p,e,protocolPin,attemptsPin){const d=design(p),ids=validate(p,e,d,protocolPin,attemptsPin),zid=ids.at(-1),z=d.space[zid];
 const [rank,M]=prefixCDF(d,ids);const best=new Map(),who=new Map();let compatible=0;
 for(let q=0;q<4**d.n;q++){let v=q;const w=Array(d.n);for(let i=d.n-1;i>=0;i--){const x=v%4;v=Math.floor(v/4);w[i]=[(x>>1)&1,x&1];}
  let misses=0,ate=0;for(let i=0;i<d.n;i++){ate+=w[i][1]-w[i][0];if(e.observed_intervals[i]!=='01'&&e.observed_intervals[i]!==String(w[i][z.includes(i)?1:0]))misses++;}
  if(misses>d.K)continue;compatible++;
  const stats=d.space.map(a=>stat(w,a,d.n,d.k)),observed=stats[zid];let gt=0n,eq=0n;
  for(let j=0;j<d.N;j++){if(stats[j]>observed)gt+=d.mass[j];else if(stats[j]===observed)eq+=d.mass[j];}
  const numerator=gt*M+eq*rank;
  if(!best.has(ate)||numerator>best.get(ate)){best.set(ate,numerator);who.set(ate,w.map(y=>y.join('')));}}
 insist(compatible>0,'no compatible worlds');let peak=-1n;const curve=[];
 for(let h=-d.n;h<=d.n;h++){if(best.has(h)&&best.get(h)>peak)peak=best.get(h);
  curve.push({ate_upper:rat(BigInt(h),BigInt(d.n)),null_feasible:peak>=0n,max_p:peak>=0n?rat(peak,d.total*M):null});}
 curve[curve.length-1].max_p='1';curve[curve.length-1].null_feasible=true;
 const relevant=curve.filter(row=>cmp(parseRat(row.ate_upper),d.nullUpper)<=0n).at(-1);
 const lower=curve.find(row=>row.null_feasible&&cmp(parseRat(row.max_p),d.alpha)>0n);
 const possibilities=[...best.keys()].filter(a=>cmp([BigInt(a),BigInt(d.n)],d.nullUpper)<=0n);
 const witness=possibilities.length?who.get(possibilities.reduce((a,b)=>best.get(a)>=best.get(b)?a:b)):null;
 return {status:relevant.null_feasible?'CONDITIONALLY_VERIFIED':'INCONSISTENT_NULL',conditional_p:relevant.max_p,
 conditional_lower_ate:lower?lower.ate_upper:null,confidence_alpha:rat(...d.alpha),compatible_worlds:compatible,
 design_denominator:String(d.total),selected_assignment_mass:String(d.mass[zid]),stopping_time:ids.length,
 weighted_prefix_right_numerator:String(rank),weighted_prefix_right_denominator:String(M),null_curve:curve,maximizing_world:witness,
 protocol_sha256:protocolPin,attempts_sha256:attemptsPin,
 warning:'Conditional statistical result only. Candidate draw probabilities must follow the preregistered outcome-blind and independently controlled per-step weights; attempted allocations and final observations require independent custody. Signed bytes alone cannot establish these premises.'};}
if(require.main===module){try{insist(process.argv.length===6,'usage: node independent.js protocol.json evidence.json PROTOCOL_PIN ATTEMPTS_PIN');
 console.log(JSON.stringify(audit(readStrict(process.argv[2]),readStrict(process.argv[3]),process.argv[4],process.argv[5]),null,2));}
 catch(e){console.error('REJECTED:',e.message);process.exit(2);}}
module.exports={design,attemptCommit,prefixCDF,audit,digest};
