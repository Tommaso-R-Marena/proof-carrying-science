'use strict';
// Independent exact BigInt audit of capped rejection sampling and transcript ranks.
const {readStrict} = require('../evidencekernel_selective_v17/strict_json');
const crypto = require('node:crypto');
function fail(x,m){if(!x)throw Error(m);}
function canonical(v){if(Array.isArray(v))return '['+v.map(canonical).join(',')+']';
 if(v&&typeof v==='object')return '{'+Object.keys(v).sort().map(k=>JSON.stringify(k)+':'+canonical(v[k])).join(',')+'}';return JSON.stringify(v);}
function digest(v){return crypto.createHash('sha256').update(canonical(v)).digest('hex');}
function exact(o,fields){fail(o&&typeof o==='object'&&!Array.isArray(o)&&Object.keys(o).sort().join('|')===fields.sort().join('|'),'invalid object keys');}
function gcd(a,b){if(a<0n)a=-a;if(b<0n)b=-b;while(b){const v=a%b;a=b;b=v;}return a;}
function rat(a,b){fail(b>0n,'zero denominator');const c=gcd(a,b);return b/c===1n?String(a/c):String(a/c)+'/'+String(b/c);}
function parseRat(s){fail(typeof s==='string'&&/^-?(0|[1-9]\d*)(?:\/[1-9]\d*)?$/.test(s)&&s.length<=30,'noncanonical rational');let t=s.split('/');let a=BigInt(t[0]),b=BigInt(t[1]||1);fail(rat(a,b)===s,'noncanonical rational');return [a,b];}
function cmp(a,b){return a[0]*b[1]-b[0]*a[1];}
function assigns(n,k){const out=[];function rec(start,z){if(z.length===k){out.push(z);return;}
for(let i=start;i<=n-(k-z.length);i++)rec(i+1,z.concat(i));}rec(0,[]);return out;}
function design(p){exact(p,['format','n','k','baseline_covariate','max_attempts','accept_if_score_le','selection_rule','candidate_law','null_ate_upper','max_interval_misses','confidence_alpha','tie_rule']);
fail(p.format==='pcs-evidencekernel-stopping-v19'&&p.selection_rule==='first_acceptable_else_last'&&p.tie_rule==='within_stop_and_selected_rejected_prefix_lex_rank'&&p.candidate_law==='iid_with_replacement','wrong design rule');
const n=p.n,k=p.k,H=p.max_attempts;
fail(Number.isSafeInteger(n)&&n>=2&&n<=8&&Number.isSafeInteger(k)&&k>0&&k<n&&Number.isSafeInteger(H)&&H>0&&H<=128,'trial out of bounds');
fail(Array.isArray(p.baseline_covariate)&&p.baseline_covariate.length===n&&p.baseline_covariate.every(v=>Number.isSafeInteger(v)&&v>=-16&&v<=16),'invalid baseline');
fail(Number.isSafeInteger(p.accept_if_score_le)&&p.accept_if_score_le>=0&&p.accept_if_score_le<=10000,'invalid cutoff');
fail(Number.isSafeInteger(p.max_interval_misses)&&p.max_interval_misses>=0&&p.max_interval_misses<=n,'invalid miss budget');
const alpha=parseRat(p.confidence_alpha),nullUpper=parseRat(p.null_ate_upper);
fail(cmp(alpha,[0n,1n])>0n&&cmp(alpha,[1n,1n])<0n&&cmp(nullUpper,[-1n,1n])>=0n&&cmp(nullUpper,[1n,1n])<=0n,'bad alpha or null');
const space=assigns(n,k),N=space.length, x=p.baseline_covariate, sx=x.reduce((a,b)=>a+b,0);
fail(N*(4**n)<=5000000 && (Math.floor(Math.log2(N))+1)*H<=4096,'complexity cap');
const scores=space.map(z=>Math.abs(n*z.reduce((a,i)=>a+x[i],0)-k*sx));
const ok=scores.map(s=>s<=p.accept_if_score_le);const rejects=ok.flatMap((a,i)=>a?[]:[i]);const R=rejects.length;
const total=BigInt(N)**BigInt(H);
let good=0n;for(let t=1;t<=H;t++)good+=BigInt(R)**BigInt(t-1)*BigInt(N)**BigInt(H-t);
const bad=BigInt(R)**BigInt(H-1);const mass=ok.map(a=>a?good:bad);
fail(mass.reduce((a,b)=>a+b,0n)===total,'distribution does not normalize');
return {space,N,n,k,H,scores,ok,rejects,R,total,mass,alpha,nullUpper};}
function attemptCommit(protocolPin, attempts){return digest({domain:'pcs-evidencekernel-v19-attempts-v1',protocol_sha256:protocolPin,attempts});}
function validate(p,e,protocolPin,attemptPin,d){fail(/^[a-f0-9]{64}$/.test(protocolPin)&&/^[a-f0-9]{64}$/.test(attemptPin),'external pins missing');
fail(digest(p)===protocolPin,'protocol pin mismatch');exact(e,['attempts','selected_assignment','observed_intervals']);
fail(Array.isArray(e.attempts)&&e.attempts.length>=1&&e.attempts.length<=d.H,'invalid transcript length');
fail(Array.isArray(e.observed_intervals)&&e.observed_intervals.length===d.n&&e.observed_intervals.every(v=>v==='0'||v==='1'||v==='01'),'invalid observations');
const ids=e.attempts.map(z=>{fail(Array.isArray(z), 'bad allocation');const i=d.space.findIndex(a=>JSON.stringify(a)===JSON.stringify(z));fail(i>=0,'unknown allocation');return i;});
fail(ids.slice(0,-1).every(i=>!d.ok[i]),'earlier accepted allocation omitted by stopping');
fail(ids.length===d.H||d.ok[ids.at(-1)],'premature stopping');
fail(JSON.stringify(e.selected_assignment)===JSON.stringify(e.attempts.at(-1)),'bad terminal selection');
fail(attemptCommit(protocolPin,e.attempts)===attemptPin,'independent transcript pin mismatch');return ids;}
function rankPrefix(ids,d){if(ids.length===1)return [1n,1n];fail(d.R>0,'impossible rejected prefix');let r=0n;
for(let j=0;j<ids.length-1;j++){const i=d.rejects.indexOf(ids[j]);fail(i>=0,'invalid prefix');r=r*BigInt(d.R)+BigInt(i);}
return [r+1n,BigInt(d.R)**BigInt(ids.length-1)];}
function stat(w,z,n,k){const zs=new Set(z);let t=0,c=0;for(let i=0;i<n;i++)if(zs.has(i))t+=w[i][1];else c+=w[i][0];return (n-k)*t-k*c;}
function audit(p,e,protocolPin,attemptPin){const d=design(p),ids=validate(p,e,protocolPin,attemptPin,d),zid=ids.at(-1),z=d.space[zid];
const [rank,M]=rankPrefix(ids,d);const best=new Map(),who=new Map();let compatible=0;
for(let q=0;q<4**d.n;q++){let v=q;const w=Array(d.n);for(let i=d.n-1;i>=0;i--){const x=v%4;v=Math.floor(v/4);w[i]=[(x>>1)&1,x&1];}
let miss=0,ate=0;for(let i=0;i<d.n;i++){ate+=w[i][1]-w[i][0];const obs=w[i][z.includes(i)?1:0];if(e.observed_intervals[i]!=='01'&&e.observed_intervals[i]!==String(obs))miss++;}
if(miss>p.max_interval_misses)continue;compatible++;
const scores=d.space.map(a=>stat(w,a,d.n,d.k));const threshold=scores[zid];let gt=0n,eq=0n;
for(let j=0;j<d.space.length;j++){if(scores[j]>threshold)gt+=d.mass[j];else if(scores[j]===threshold)eq+=d.mass[j];}
const numerator=gt*M+eq*rank;if(!best.has(ate)||numerator>best.get(ate)){best.set(ate,numerator);who.set(ate,w.map(y=>y.join('')));}
}fail(compatible>0,'no compatible latent world');let peak=-1n;const curve=[];
for(let h=-d.n;h<=d.n;h++){if(best.has(h)&&best.get(h)>peak)peak=best.get(h);
curve.push({ate_upper:rat(BigInt(h),BigInt(d.n)),null_feasible:peak>=0n,max_p:peak>=0n?rat(peak,d.total*M):null});}
curve[curve.length-1].max_p='1';curve[curve.length-1].null_feasible=true;
const matches=curve.filter(x=>cmp(parseRat(x.ate_upper),d.nullUpper)<=0n),target=matches.at(-1),
 lower=curve.find(x=>x.null_feasible&&cmp(parseRat(x.max_p),d.alpha)>0n);
const candidates=[...best.keys()].filter(a=>cmp([BigInt(a),BigInt(d.n)],d.nullUpper)<=0n);
const witness=candidates.length?who.get(candidates.reduce((a,b)=>best.get(a)>=best.get(b)?a:b)):null;
return {status:target.null_feasible?'CONDITIONALLY_VERIFIED':'INCONSISTENT_NULL',conditional_p:target.max_p,conditional_lower_ate:lower?lower.ate_upper:null,
confidence_alpha:rat(...d.alpha),compatible_worlds:compatible,design_denominator:String(d.total),selected_assignment_mass:String(d.mass[zid]),stopping_time:ids.length,
rejected_prefix_rank:String(rank),rejected_prefix_mass:String(M),null_curve:curve,maximizing_world:witness,protocol_sha256:protocolPin,attempts_sha256:attemptPin,
warning:'Conditional statistical result, NOT physical authentication. Requires IID candidate draws, preregistered outcome-blind acceptance threshold and stopping cap, immutable attempt history, valid measurement intervals and correct protocol pin.'};}
if(require.main===module){try{fail(process.argv.length===6,'usage: node independent.js protocol.json evidence.json PROTOCOL_SHA256 ATTEMPTS_SHA256');
console.log(JSON.stringify(audit(readStrict(process.argv[2]),readStrict(process.argv[3]),process.argv[4],process.argv[5]),null,2));}
catch(e){console.error('REJECTED:',e.message);process.exit(2);}}
module.exports={design,attemptCommit,rankPrefix,audit,digest};
