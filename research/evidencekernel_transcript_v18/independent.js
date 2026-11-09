'use strict';
/* Independently written BigInt audit for exact transcript-conditioned inference.
   Design histogram reuses audited v17 JavaScript, but conditional rank and
   potential-outcome logic are independently implemented here. */
const {design, digest} = require('../evidencekernel_selective_v17/independent');
const {readStrict} = require('../evidencekernel_selective_v17/strict_json');
const FMT = 'pcs-evidencekernel-transcript-rank-v18';
const TIE = 'conditional_selected_assignment_transcript_rank';
function check(c,msg){if(!c)throw Error(msg);}
function keys(o,fields){check(o&&typeof o==='object'&&!Array.isArray(o)&&
  Object.keys(o).sort().join('|')===fields.slice().sort().join('|'), 'malformed protocol or evidence');}
function bgcd(a,b){a=a<0n?-a:a;b=b<0n?-b:b;while(b){const x=a%b;a=b;b=x;}return a;}
function rational(a,b){check(b>0n,'negative rational denominator');const g=bgcd(a,b);
  return (b/g===1n?String(a/g):String(a/g)+'/'+String(b/g));}
function parseR(s){check(typeof s==='string'&&/^-?(0|[1-9]\d*)(?:\/[1-9]\d*)?$/.test(s),'invalid rational');
  const [n,d='1']=s.split('/');const a=BigInt(n),b=BigInt(d);
  check(b>0n&&rational(a,b)===s,'noncanonical rational');return [a,b];}
function lessEq(a,b){return a[0]*b[1]<=b[0]*a[1];}
function falling(n,k){let v=1n;if(k>n)return 0n;for(let j=0;j<k;j++)v*=BigInt(n-j);return v;}
function adapter(p){
  keys(p,['format','n','k','baseline_covariate','candidate_draws','candidate_law',
          'selection_rule','null_ate_upper','max_interval_misses','confidence_alpha','tie_rule']);
  check(p.format===FMT&&p.tie_rule===TIE,'unsupported tie protocol');
  const {...q}=p;delete q.tie_rule;q.format='pcs-evidencekernel-balanced-selection-v17';
  q.randomizer_support=2;q.randomizer_rule='independent_right_endpoint_uniform';return q;
}
function winnerOf(prefix,scores){let w=prefix[0];for(const x of prefix)if(scores[x]<scores[w])w=x;return w;}
function suffixHistogram(scores,prefix,r,law){
  const N=scores.length;const used=new Set(prefix);
  check(law==='iid_with_replacement'||used.size===prefix.length,'repeated distinct draw');
  const pool=Array.from({length:N},(_,i)=>i).filter(i=>law==='iid_with_replacement'||!used.has(i));
  check(r>=0&&(law==='iid_with_replacement'||r<=pool.length),'invalid suffix');
  const F=n=>law==='iid_with_replacement'?BigInt(n)**BigInt(r):falling(n,r);
  const mass=Array(N).fill(0n),winner=prefix.length?winnerOf(prefix,scores):null;
  const bound=winner===null?Infinity:scores[winner];
  if(winner!==null)mass[winner]=F(pool.filter(i=>scores[i]>=bound).length);
  const groups=[...new Set(pool.map(i=>scores[i]))].sort((a,b)=>a-b);
  for(const s of groups){if(s>=bound)continue;
    const tie=pool.filter(i=>scores[i]===s);
    const g=F(pool.filter(i=>scores[i]>=s).length)-F(pool.filter(i=>scores[i]>s).length);
    check(g%BigInt(tie.length)===0n,'nonintegral score symmetry');
    for(const i of tie)mass[i]=g/BigInt(tie.length);
  }
  check(mass.reduce((a,b)=>a+b,0n)===F(pool.length),'suffix did not normalize');
  return mass;
}
function beforeHistogram(d,attempts,law){
  const seq=attempts.map(a=>{const idx=d.A.findIndex(x=>JSON.stringify(a)===JSON.stringify(x));
    check(idx>=0,'malformed candidate allocation');return idx;});
  const N=d.A.length, prior=Array(N).fill(0n),prefix=[];
  for(let j=0;j<seq.length;j++){
    for(let alt=0;alt<seq[j];alt++){
      if(law==='ordered_without_replacement'&&prefix.includes(alt))continue;
      const sub=suffixHistogram(d.scores,[...prefix,alt],seq.length-j-1,law);
      for(let i=0;i<N;i++)prior[i]+=sub[i];
    }
    prefix.push(seq[j]);
  }
  let rank=0n;
  if(law==='iid_with_replacement'){
    for(let j=0;j<seq.length;j++)rank+=BigInt(seq[j])*BigInt(N)**BigInt(seq.length-j-1);
  }else{
    const seen=new Set();
    for(let j=0;j<seq.length;j++){
      let smaller=0;for(let i=0;i<seq[j];i++)if(!seen.has(i))smaller++;
      rank+=BigInt(smaller)*falling(N-j-1,seq.length-j-1);seen.add(seq[j]);
    }
  }
  check(prior.reduce((a,b)=>a+b,0n)===rank,'rank mismatch');
  return prior;
}
function stat(world,z,n,k){const assigned=new Set(z);let treated=0,control=0;
  for(let i=0;i<n;i++){if(assigned.has(i))treated+=world[i][1];else control+=world[i][0];}
  return (n-k)*treated-k*control;
}
function attemptCommitment(pin,attempts){return digest({domain:'pcs-evidencekernel-v18-attempts-v1',protocol_sha256:pin,attempts});}
function audit(p,e,pin,attemptsPin){
  check(typeof pin==='string'&&/^[0-9a-f]{64}$/.test(pin),'external pin required');
  check(digest(p)===pin,'untrusted or mismatched protocol');
  check(typeof attemptsPin==='string'&&/^[0-9a-f]{64}$/.test(attemptsPin),'independently retained attempt pin required');
  check(e&&Array.isArray(e.attempts)&&attemptCommitment(pin,e.attempts)===attemptsPin,'attempt transcript differs from externally pinned commitment');
  const d=design(adapter(p));
  keys(e,['attempts','selected_assignment','observed_intervals']);
  check(Array.isArray(e.attempts)&&e.attempts.length===p.candidate_draws,'wrong attempt length');
  check(Array.isArray(e.selected_assignment)&&e.selected_assignment.length===p.k,'invalid selected assignment');
  check(Array.isArray(e.observed_intervals)&&e.observed_intervals.length===p.n&&
        e.observed_intervals.every(x=>x==='0'||x==='1'||x==='01'),'invalid observations');
  const attempts=e.attempts.map(a=>d.A.findIndex(z=>JSON.stringify(a)===JSON.stringify(z)));
  check(attempts.every(i=>i>=0),'invalid attempt');
  if(p.candidate_law==='ordered_without_replacement')check(new Set(attempts).size===attempts.length,'duplicate attempt');
  const win=winnerOf(attempts,d.scores);
  check(JSON.stringify(d.A[win])===JSON.stringify(e.selected_assignment),'selected assignment mismatch');
  check(d.mass[win]>0n,'selected assignment impossible');
  check(4**p.n*d.A.length<=5000000,'latent world capacity exceeded');
  const before=beforeHistogram(d,e.attempts,p.candidate_law), m=d.mass[win], rank=before[win]+1n;
  check(rank>0n&&rank<=m,'bad ancillary rank');
  const labels=e.observed_intervals,zset=new Set(e.selected_assignment);
  const byAte=new Map(), witnesses=new Map();let compatible=0;
  for(let j=0;j<4**p.n;j++){
    let tmp=j;const world=Array(p.n);
    for(let i=p.n-1;i>=0;i--){const v=tmp%4;tmp=Math.floor(tmp/4);world[i]=[(v>>1)&1,v&1];}
    let misses=0,ate=0;
    for(let i=0;i<p.n;i++){
      ate+=world[i][1]-world[i][0];
      const actual=String(world[i][zset.has(i)?1:0]);
      if(labels[i]!=='01'&&labels[i]!==actual)misses++;
    }
    if(misses>p.max_interval_misses)continue;
    compatible++;
    const t=stat(world,d.A[win],p.n,p.k);
    let gt=0n,eq=0n;
    for(let i=0;i<d.A.length;i++){const v=stat(world,d.A[i],p.n,p.k);
      if(v>t)gt+=d.mass[i];else if(v===t)eq+=d.mass[i];}
    const h=gt*m+rank*eq;
    check(h>=1n&&h<=m*d.denom,'invalid conditional rank p');
    if(!byAte.has(ate)||byAte.get(ate)<h){byAte.set(ate,h);witnesses.set(ate,world.map(a=>a.join('')));}
  }
  check(compatible>0,'no compatible potential outcome model');
  const alpha=parseR(p.confidence_alpha),upper=parseR(p.null_ate_upper);
  const curve=[];let best=-1n;
  for(let j=-p.n;j<=p.n;j++){
    if(byAte.has(j)&&byAte.get(j)>best)best=byAte.get(j);
    curve.push({ate_upper:rational(BigInt(j),BigInt(p.n)),null_feasible:best>=0n,
      max_p:best>=0n?rational(best,m*d.denom):null});
  }
  // ATE <= 1 is a mathematical tautology for binary outcomes.
  curve[curve.length-1].max_p='1';
  const target=curve.filter(x=>lessEq(parseR(x.ate_upper),upper)).at(-1);
  const first=curve.find(x=>x.null_feasible&&!lessEq(parseR(x.max_p),alpha));
  const eligible=[...byAte].filter(([t])=>BigInt(t)*upper[1]<=upper[0]*BigInt(p.n));
  let witness=null;if(eligible.length){const max=eligible.reduce((v,[_t,h])=>h>v?h:v,-1n);
    const winning=eligible.filter(([_t,h])=>h===max).sort((a,b)=>a[0]-b[0])[0][0];
    witness=witnesses.get(winning);}
  return {
    status:target.null_feasible?'CONDITIONALLY_VERIFIED':'INCONSISTENT_NULL',
    conditional_rank_p:target.max_p,conditional_lower_ate:first?first.ate_upper:null,
    confidence_set_status:first?'NONEMPTY':'EMPTY_SET',compatible_worlds:compatible,
    design_denominator:String(d.denom),selected_assignment_mass:String(m),
    lexicographically_prior_transcripts:String(before.reduce((a,b)=>a+b,0n)),
    within_selected_assignment_transcript_rank:String(rank),
    within_selected_assignment_transcript_mass:String(m),
    confidence_alpha:rational(...alpha),maximizing_world:witness,null_curve:curve,
    protocol_sha256:pin,attempts_sha256:attemptsPin,
    warning:'Conditional inference only. Transcript completeness, ex ante protocol pinning, random candidate draws, outcome blindness, and interval coverage are external premises; the attempt pin must have been independently retained before outcomes, which this program cannot prove. No auxiliary post-outcome random draw is assumed.'
  };
}
if(require.main===module){try{
  check(process.argv.length===6,'Usage: node independent.js protocol.json evidence.json PROTOCOL_PIN ATTEMPTS_PIN');
  console.log(JSON.stringify(audit(readStrict(process.argv[2]),readStrict(process.argv[3]),process.argv[4],process.argv[5]),null,2));
}catch(err){console.error('REJECTED: '+err.message);process.exit(2);}}
module.exports={audit,suffixHistogram,beforeHistogram,attemptCommitment};
