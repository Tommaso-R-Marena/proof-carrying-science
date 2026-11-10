'use strict';
/* Independent Node.js witness signature, commitment-chain and exact allocation audit.
   Invokes separately implemented v25 BigInt scientific receiver after verification. */
const crypto=require('node:crypto');
const v25=require('../evidencekernel_propensity_v25/independent.js');
const {readStrict}=require('../evidencekernel_propensity_v25/strict_json.js');
const FORMAT='pcs-evidencekernel-witness-ceremony-v28', RESULT='pcs-evidencekernel-witness-audit-v28';
function need(x,m){if(!x)throw Error(m);}
function keys(o,ls,m){need(o&&typeof o==='object'&&!Array.isArray(o)&&Object.keys(o).sort().join('|')===ls.slice().sort().join('|'),m);}
function canonical(o){if(Array.isArray(o))return '['+o.map(canonical).join(',')+']';
 if(o!==null&&typeof o==='object')return '{'+Object.keys(o).sort().map(k=>JSON.stringify(k)+':'+canonical(o[k])).join(',')+'}';
 return JSON.stringify(o);}
function sha(s){return crypto.createHash('sha256').update(s).digest('hex');}
function digest(o){return sha(canonical(o));}
function bytes32(s,name){need(typeof s==='string'&&/^[0-9a-f]{64}$/.test(s),'invalid '+name);return Buffer.from(s,'hex');}
function b64(s,n,name){need(typeof s==='string'&&/^[a-zA-Z0-9+/]+={0,2}$/.test(s),'invalid '+name);
 const v=Buffer.from(s,'base64');need(v.length===n&&v.toString('base64')===s,'noncanonical '+name);return v;}
function commit(role,pin,index,prior,seed){need(role==='operator'||role==='witness','role');bytes32(pin,'pin');bytes32(prior,'prior');bytes32(seed,'seed');
 need(Number.isInteger(index)&&index>=0,'index');return sha(`pcs-evidencekernel-v28-share|${role}|${pin}|${index}|${prior}|${seed}`);}
function commitment(pin,index,prior,state,oc,wc){return {domain:'pcs-ek-v28-both-committed',protocol_sha256:pin,
 index,prev_sha256:prior,state,operator_commit_sha256:oc,witness_commit_sha256:wc};}
function revealed(pin,body,receipt,os,ws,a,r){return {domain:'pcs-ek-v28-draw-revealed',protocol_sha256:pin,commitment:body,
 commit_receipt_signature_b64:receipt,operator_share_hex:os,witness_share_hex:ws,action:a,report:r};}
function sigCheck(pub,body,s){need(crypto.verify(null,Buffer.from(canonical(body),'ascii'),pub,b64(s,64,'signature')),'witness signature failed');}
function drawFromShares(os,ws,bits,q){need(Number.isInteger(bits)&&bits>=1&&bits<=20,'invalid bits');
 const a=bytes32(os,'operator share'),b=bytes32(ws,'witness share');
 const num=v25.mul(q,v25.F(1n<<BigInt(bits)));
 need(num[1]===1n&&num[0]>0n&&num[0]<(1n<<BigInt(bits)),'probability cannot be exactly represented');
 let x=0n;for(let i=0;i<32;i++)x=(x<<8n)|BigInt(a[i]^b[i]);
 return x>>BigInt(256-bits)<num[0]?1:0;}
function audit(c,p,e,cp,sp,ep){bytes32(cp,'contract pin');bytes32(sp,'study pin');bytes32(ep,'evidence pin');
 need(digest(c)===cp&&digest(p)===sp,'registration digest mismatch');
 need(digest({domain:'pcs-ek-v28-witness-records',contract_pin:cp,study_pin:sp,evidence:e})===ep,'evidence commitment mismatch');
 keys(c,['format','v25_protocol_sha256','witness_public_key_b64','denominator_bits','registered_units'],'witness contract fields');
 keys(e,['draws','true_intervals'],'witness evidence fields');
 need(c.format===FORMAT&&c.v25_protocol_sha256===sp,'protocol binding mismatch');
 const d=v25.design(p),bits=c.denominator_bits;
 need(Number.isInteger(bits)&&bits>=1&&bits<=20&&c.registered_units===d.n,'unsupported bits or cohort');
 const keyBytes=b64(c.witness_public_key_b64,32,'Ed25519 public key');
 const pub=crypto.createPublicKey({key:Buffer.concat([Buffer.from('302a300506032b6570032100','hex'),keyBytes]),format:'der',type:'spki'});
 const qs=[];for(let s=0;s<d.S;s++){
  const q=d.tuning[0].qs[s];need(v25.cmp(q,d.caps[s])===0&&d.tuning.every(t=>v25.cmp(t.qs[s],q)===0),
    'reference policy not exactly witnessed');
  drawFromShares('00'.repeat(32),'00'.repeat(32),bits,q);qs.push(q);
 }
 need(Array.isArray(e.draws)&&e.draws.length>=d.min&&e.draws.length<=d.n&&
 Array.isArray(e.true_intervals)&&e.true_intervals.length===e.draws.length,'invalid prefix');
 let state=d.init,prev=cp;const acts=[],reports=[];
 for(let i=0;i<e.draws.length;i++){
  const row=e.draws[i];keys(row,['index','prev_sha256','state','operator_commit_sha256','witness_commit_sha256',
   'commit_receipt_signature_b64','operator_share_hex','witness_share_hex','action','report','draw_signature_b64'],'draw fields');
  need(row.index===i&&row.prev_sha256===prev&&row.state===state,'chain or state discontinuity');
  const oc=row.operator_commit_sha256,wc=row.witness_commit_sha256;bytes32(oc,'operator commit');bytes32(wc,'witness commit');
  need(commit('operator',cp,i,prev,row.operator_share_hex)===oc&&
       commit('witness',cp,i,prev,row.witness_share_hex)===wc,'commitment mismatch');
  const body=commitment(cp,i,prev,state,oc,wc);sigCheck(pub,body,row.commit_receipt_signature_b64);
  const a=row.action,r=row.report;
  need((a===0||a===1)&&(r===0||r===1),'invalid action/report bits');
  need(a===drawFromShares(row.operator_share_hex,row.witness_share_hex,bits,qs[state]),'invalid assignment draw');
  sigCheck(pub,revealed(cp,body,row.commit_receipt_signature_b64,row.operator_share_hex,row.witness_share_hex,a,r),row.draw_signature_b64);
  acts.push(a);reports.push(r);prev=digest(row);
  const stopped=i+1===d.n||(i+1>=d.min&&d.st[state][a][r]);
  need(stopped===(i===e.draws.length-1),'incorrect study stopping');
  state=d.tr[state][a][r];
 }
 const scientificEvidence={assignments:acts,reports,true_intervals:e.true_intervals};
 const internalPin=digest({domain:'pcs-evidencekernel-v25-observed-prefix',protocol_sha256:sp,evidence:scientificEvidence});
 const scientific=v25.audit(p,scientificEvidence,sp,internalPin);
 return {format:RESULT,status:scientific.status,verified_signed_draws:e.draws.length,
 exact_treatment_probabilities_by_state:qs.map(v25.out),first_signed_commit_anchor:cp,
 terminal_signed_record_sha256:prev,conditional_lower_ate:scientific.anytime_lower_ate,
 conditional_confidence_alpha:scientific.conditional_confidence_alpha,
 asserted_measurement_calibration_failure:scientific.asserted_joint_calibration_failure_bound,
 conditional_scientific_report:scientific,ceremony_contract_sha256:cp,study_protocol_sha256:sp,
 transcript_sha256:ep,
 trust_boundary:'Ed25519 authenticates witness signatures, and XOR mapping is exactly unbiased IF at least one share per draw is conditionally uniform/unpredictable, commits are completed before reveals, an independent witness enforces the chronology, no selective abort/dropout occurs, and enrollment is complete. Signatures/hashes alone cannot prove those premises.'};
}
module.exports={audit,commit,commitment,revealed,drawFromShares,digest,canonical};
if(require.main===module){try{
 need(process.argv.length===8,'usage: node independent.js contract.json study.json evidence.json CONTRACT_PIN STUDY_PIN EVIDENCE_PIN');
 const out=audit(readStrict(process.argv[2]),readStrict(process.argv[3]),readStrict(process.argv[4]),
 process.argv[5],process.argv[6],process.argv[7]);
 console.log(JSON.stringify(out,null,2));
 }catch(err){console.error('REJECTED:',err.message);process.exit(2);}}
