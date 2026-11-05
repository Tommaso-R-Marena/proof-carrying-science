'use strict';
// No external frameworks or telemetry. Never interpolate untrusted artifact text into HTML.
const el = id => document.getElementById(id);
const state = {files:[], reports:[], sample:false};
const fmt = n => Number(n).toLocaleString();
const readableFraction = s => {
  if(s===undefined||s===null)return null;
  const parts=String(s).split('/');const n=Number(parts[0]),d=Number(parts[1]||'1');
  if(Number.isFinite(n)&&Number.isFinite(d)&&d!==0){
   const value=n/d;if(Number.isFinite(value))return Number(value.toPrecision(10));
  }
  return String(s).slice(0,70)+'… (exact value in downloaded receipt)';
};
const short = s => s.length>24 ? s.slice(0,24)+'…':s;
const make = (tag, cls, text) => {const x=document.createElement(tag); if(cls)x.className=cls;if(text!==undefined)x.textContent=String(text);return x;};
function setNotice(s){el('notice').textContent=s}
function policy(){return {
  forbid_stochastic_onnx_ops:el('stochastic').checked,
  forbid_custom_onnx_domains:el('custom').checked,
  require_self_contained_onnx:el('external').checked,
  require_onnx_official_checker:el('official').checked,
  max_onnx_nodes:Number(el('nodes').value),max_pdb_clashes:Number(el('clashes').value),
  check_output_bounds:el('bound').checked,
  search_scalar_witness:el('witness').checked,
  enable_reference_replay:el('reference').checked,
  enable_partition_proof:el('partition').checked,
  max_partition_leaves:Number(el('partition-leaves').value),
  enable_torch_crosscheck:el('torch').checked,
  enable_milp_challenger:el('milp').checked,
  milp_timeout_seconds:Number(el('milp-timeout').value),
  enable_relational_certificate:el('relational').checked,
  relational_coefficients:el('relation-coeffs').value.split(',').map(x=>x.trim()).filter(Boolean),
  relational_input_box:JSON.parse(el('per-feature-box').value.trim()||'[]'),
  relational_upper_limit:el('relation-limit').value.trim(),
  enable_activation_case_cover:el('activation-cases').checked,
  max_activation_leaves:Number(el('activation-leaves').value),
  input_min:Number(el('inmin').value),input_max:Number(el('inmax').value),
  output_min:Number(el('outmin').value),output_max:Number(el('outmax').value)
}}
function addFiles(fs){
  for(const f of fs){if(!state.files.some(x=>x.name===f.name&&x.size===f.size))state.files.push(f)}
  state.sample=false; renderFiles(); setNotice('');
}
function renderFiles(){const host=el('files');host.replaceChildren();
 state.files.forEach((f,i)=>{let row=make('div','file');let n=make('span','nm',f.name);n.title=f.name;row.append(n,make('span','muted small',`${(f.size/1024).toFixed(1)} KiB`));
  let rm=make('button','', '×');rm.title='Remove '+f.name;rm.addEventListener('click',()=>{state.files.splice(i,1);renderFiles()});row.append(rm);host.append(row)});
 el('analyze').disabled=!state.files.length;el('analyze').textContent=`Inspect ${state.files.length||'selected'} file${state.files.length===1?'':'s'}`;
}
const drop=el('drop');
drop.addEventListener('dragenter',e=>{e.preventDefault();drop.classList.add('over')});
drop.addEventListener('dragover',e=>{e.preventDefault();drop.classList.add('over')});
drop.addEventListener('dragleave',e=>{e.preventDefault();if(!drop.contains(e.relatedTarget))drop.classList.remove('over')});
drop.addEventListener('drop',e=>{e.preventDefault();drop.classList.remove('over');addFiles([...e.dataTransfer.files])});
drop.addEventListener('click',e=>{if(e.target.id!=='browse')el('input').click()});
drop.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();el('input').click()}});
el('browse').onclick=()=>el('input').click();
el('input').onchange=e=>{addFiles([...e.target.files]);e.target.value=''};
el('clear').onclick=()=>{state.files=[];state.reports=[];state.sample=false;setNotice('');renderFiles();renderReports()};
const familyMetricKeys = {agent_trace:['proposals','proposals_denied','executions_reported','executions_approved_by_synthetic_policy'],mmcif:['models','atoms','residues','chains','severe_close_pairs_heuristic'],onnx:['nodes','initializers','inputs','outputs','external_tensors'],safetensors:['tensors','parameters','nonfinite_sampled'],pdb:['atoms','residues','chains','severe_close_pairs_heuristic'],sbml:['species','reactions','linear_conserved_quantities_reaction_only','broken_species_references'],fasta:['sequences','residues','unexpected_characters']};
function download(name,obj){const b=new Blob([JSON.stringify(obj,null,2)+'\n'],{type:'application/json'});const u=URL.createObjectURL(b);let a=document.createElement('a');a.href=u;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(u),500)}
function metricDisplay(key,value){if(typeof value==='object')return JSON.stringify(value).slice(0,55);if(typeof value==='number')return fmt(value);return String(value)}
function renderReports(){const host=el('reports');host.replaceChildren();el('empty').hidden=state.reports.length>0;el('exportall').hidden=state.reports.length===0;
 for(const [idx,r] of state.reports.entries()){
  const rep=make('article','report');const hd=make('div','report-top');const info=make('div');info.append(make('div','fname',r.filename));info.append(make('div','metadata',`${r.family.toUpperCase()} · ${fmt(r.bytes)} bytes · SHA-256 ${short(r.sha256)}`));
  hd.append(info,make('span','pill '+r.decision,r.decision));rep.append(hd);
  const m=make('div','metricwrap');const ks=familyMetricKeys[r.family]||Object.keys(r.metrics).slice(0,4);
  for(const k of ks){if(r.metrics[k]===undefined)continue;const item=make('div','metric');item.append(make('strong','',metricDisplay(k,r.metrics[k])),make('small','',k.replaceAll('_',' ')));m.append(item)}rep.append(m);
  const counts={PASS:0,OPEN:0,FAIL:0};r.checks.forEach(c=>counts[c.status]++);
  const total=r.checks.length||1, bar=make('div','bar');for(const s of ['PASS','OPEN','FAIL']){if(!counts[s])continue;const seg=make('span',s);seg.style.width=(counts[s]*100/total)+'%';bar.append(seg)}rep.append(bar);
  rep.append(make('p','hint',`${counts.PASS} passed checks · ${counts.OPEN} open obligations · ${counts.FAIL} failed checks. Overall ${r.decision} is not a general deployment-safety verdict.`));
  const checks=make('div','checks');for(const c of r.checks){const ck=make('div','check');ck.append(make('span','pill '+c.status,c.status));const desc=make('div');desc.append(make('h4','',c.title),make('p','',c.evidence));ck.append(desc);checks.append(ck)}rep.append(checks);
  const d=r.details||{};
  if(d.candidate_counterexample){
    const w=d.candidate_counterexample;
    const panel=make('section','evidencebox');panel.append(make('h3','','Rational counterexample candidate'));
    panel.append(make('p','',`Idealized rational arithmetic found a candidate. The optional NumPy float32 replay below, if present, is a limited independent computation—not official ONNX Runtime verification.`));
    panel.append(make('pre','',JSON.stringify({inputs:w.inputs,outputs:w.outputs,violating_outputs:w.violating_outputs},null,2)));
    const wb=make('button','btn secondary','Download candidate witness');wb.onclick=()=>download(`pcs-candidate-${idx+1}.json`,w);panel.append(wb);rep.append(panel);
  }
  if(d.denied_proposals_sample || d.reported_unauthorized_executions){
    const panel=make('section','evidencebox');panel.append(make('h3','','Tool-use agent policy evaluation (synthetic)'));
    panel.append(make('p','','The reviewer-controlled demo policy is fixed outside uploaded traces. Reported executions are NOT authenticated, and this inspector does not dispatch any tools.'));
    const ev={denied_proposals_sample:d.denied_proposals_sample||[],reported_unauthorized_executions:d.reported_unauthorized_executions||[]};
    panel.append(make('pre','',JSON.stringify(ev,null,2)));rep.append(panel);
  }
  if(d.reference_replay){
    const w=d.reference_replay, panel=make('section','evidencebox');
    panel.append(make('h3','',w.status==='VIOLATION_REPRODUCED'?'Float32 numerical violation reproduced (scoped)': 'NumPy scalar replay: '+w.status));
    panel.append(make('p','',w.scope || w.reason || 'Reference replay incomplete. Not an ONNX Runtime certificate.'));
    if(w.outputs)panel.append(make('pre','',JSON.stringify({outputs:w.outputs,violating_outputs:w.violating_outputs,output_bits_hex:w.output_bits_hex,numpy:w.numpy},null,2)));
    rep.append(panel);
  }
  if(d.dense_network){
    const b=d.dense_network,w=d.dense_counterexample,run=d.dense_replay;
    const panel=make('section','evidencebox');panel.append(make('h3','','Neural-network box assurance (experimental)'));
    panel.append(make('p','',`${b.input_width} inputs · ${b.output_width} outputs · ${b.operator_count} operations · ${b.conditional_real_range}. Exact rational intervals, not floating-point runtime guarantees.`));
    panel.append(make('pre','',JSON.stringify({exact_output_intervals:b.enclosure_exact,probes_tested:b.probes_tested,violating_candidate:w?.inputs||null,replay_status:run?.status||'not attempted',float32_outputs:run?.outputs||null,violating_indices:run?.violating_indices||null},null,2)));
    rep.append(panel);
  }
  if(d.partition_proof){
    const pp=d.partition_proof, panel=make('section','evidencebox');
    panel.append(make('h3','',pp.status==='PROVED_CONDITIONALLY'?'Conditional real bound: finite-cover certificate':'Finite-cover attempt: unresolved'));
    panel.append(make('p','',pp.status==='PROVED_CONDITIONALLY'?`${pp.leaves} exact input regions checked. The certificate includes all subdivision boundaries and recomputable leaf enclosures. This is not ONNX Runtime, IEEE-754, or Lean certification.`:(pp.reason||'Partition budget exhausted.')));
    if(pp.certificate){panel.append(make('pre','',JSON.stringify({input_box:pp.certificate.input_box,target:pp.certificate.target,leaves:pp.leaves,certificate_sha256:pp.certificate.certificate_sha256},null,2)));
      const save=make('button','btn secondary','Download conditional proof certificate');save.onclick=()=>download('pcs-partition-certificate-v0.5.json',pp.certificate);panel.append(save);
    }rep.append(panel);
  }
  if(d.relational_proof){
    const p=d.relational_proof, panel=make('section','evidencebox');
    panel.append(make('h3','',p.status==='PROVED_CONDITIONALLY'?'Independent neural invariant certificate: VERIFIED':'Relational claim remains OPEN'));
    panel.append(make('p','',p.status==='PROVED_CONDITIONALLY'?'The optimizer proposed nonnegative rational multipliers; the exact-arithmetic checker independently verified the full constraint identity and property for every real-valued input in the stated box. This does NOT guarantee IEEE-754/ONNX Runtime behavior.':(p.reason||'No sound certificate obtained; no safety conclusion.')));
    if(p.certificate){
      const c=p.certificate;
      panel.append(make('pre','',JSON.stringify({property:c.relation,assumed_input:c.input_box,verified_upper_bound:p.verification.verified_upper_bound,certificate_sha256:c.certificate_sha256,nonzero_multipliers:p.verification.nonzero_multipliers},null,2)));
      const save=make('button','btn secondary','Download exact rational proof');save.onclick=()=>download('pcs-relational-farkas-certificate-v06.json',c);panel.append(save);
      const pol={schema:'pcs-relational-reviewer-policy-v0.6',input_box:c.input_box,output_coefficients:c.relation.output_coefficients,upper_limit:c.relation.upper_limit};
      const reviewer=make('button','btn secondary','Download REVIEW POLICY (check independently)');reviewer.onclick=()=>download('pcs-relational-reviewer-policy-v06.json',pol);panel.append(reviewer);
    }
    rep.append(panel);
  }
  if(d.activation_proof){
    const p=d.activation_proof,panel=make('section','evidencebox');
    panel.append(make('h3','',p.status==='PROVED_CONDITIONALLY'?'Exhaustive activation-case proof: VERIFIED':'Activation-case proof: incomplete'));
    panel.append(make('p','',p.status==='PROVED_CONDITIONALLY'?`${p.verification.fully_checked_cases} complete activation cases verified, including exact-rational leaf witnesses. An absent branch makes the entire certificate invalid. This is an idealized real-number result, NOT ONNX Runtime or Lean.`:(p.reason||'No complete coverage found.')));
    if(p.certificate){
      const c=p.certificate;
      panel.append(make('pre','',JSON.stringify({input_box:c.input_box,relation:c.relation,cases:p.verification.fully_checked_cases,certificate_sha256:c.certificate_sha256},null,2)));
      const btn=make('button','btn secondary','Download complete activation proof');btn.onclick=()=>download('pcs-activation-case-proof-v06.json',c);panel.append(btn);
      const policy={schema:'pcs-relational-reviewer-policy-v0.6',input_box:c.input_box,output_coefficients:c.relation.output_coefficients,upper_limit:c.relation.upper_limit};
      const check=make('button','btn secondary','Download reviewer policy');check.onclick=()=>download('pcs-activation-reviewer-policy-v06.json',policy);panel.append(check);
    }
    rep.append(panel);
  }
  if(d.milp_challenge){
    const a=d.milp_challenge, w=d.milp_counterexample, q=d.milp_replay;
    const panel=make('section','evidencebox');panel.append(make('h3','','MILP challenge: interior counterexample search'));
    panel.append(make('p','',`Status: ${a.status}. ${a.variables||0} variables, ${a.unstable_relu_units||0} undecided ReLU gates. The solver is a counterexample candidate generator, not a safety proof.`));
    panel.append(make('pre','',JSON.stringify({input:w?.inputs||null,idealized_output:w?.idealized_outputs||null,numpy_replay:q?.status||'not run',numpy_outputs:q?.outputs||null,limitations:a.limitation},null,2)));
    rep.append(panel);
  }
  if(d.torch_reference){
    const a=d.torch_reference,panel=make('section','evidencebox');panel.append(make('h3','','Independent PyTorch CPU reference'));
    panel.append(make('p','',`Status: ${a.status}. Agreement: ${a.agreement||'not established'}. Two operator interpreters; neither executes the original ONNX file in ONNX Runtime.`));
    panel.append(make('pre','',JSON.stringify({outputs:a.outputs,violating_indices:a.violating_indices,both_reproduced_violation:a.both_reproduced_violation,torch:a.torch},null,2)));
    rep.append(panel);
  }
  if(d.charge_balance){
    const b=d.charge_balance,panel=make('section','evidencebox');panel.append(make('h3','','Explicit charge bookkeeping'));
    panel.append(make('p','',`${b.balanced_reactions} charge-balanced; ${b.imbalanced_reactions_at_least} charge-imbalanced; ${b.unresolved_reactions} unknown. Assumes chemical annotations.`));
    if(b.unbalanced_sample?.length)panel.append(make('pre','',JSON.stringify(b.unbalanced_sample,null,2)));rep.append(panel);
  }
  if(d.reaction_only_invariants){
    const i=d.reaction_only_invariants;const panel=make('section','evidencebox');
    panel.append(make('h3','','Exact reaction-only stoichiometric invariants'));
    panel.append(make('p','',`Rank ${i.stoichiometric_rank}. ${i.linear_invariant_count} independent linear invariants (d(amount)/dt = N·v). This does not prove physical mass conservation.`));
    if(i.conservation_basis.length)panel.append(make('pre','',JSON.stringify(i.conservation_basis.slice(0,8),null,2)));
    rep.append(panel);
  }
  if(d.elemental_balance){
    const b=d.elemental_balance;const panel=make('section','evidencebox');
    panel.append(make('h3','','Explicit-formula element balance'));
    panel.append(make('p','',`${b.balanced_reactions} balanced; ${b.imbalanced_reactions_at_least} imbalanced; ${b.unresolved_reactions} unresolved reaction(s).`));
    if(b.imbalanced_reactions_sample.length)panel.append(make('pre','',JSON.stringify(b.imbalanced_reactions_sample.slice(0,6),null,2)));
    rep.append(panel);
  }
  const disclaimer=make('div','disclaimer',r.limitations.join(' '));rep.append(disclaimer);
  const actions=make('div','report-actions');const receipt=make('button','btn secondary','Download JSON receipt');receipt.onclick=()=>download(`pcs-assessment-${idx+1}.json`,r);actions.append(receipt);
  const pcs=make('button','btn secondary','Download PCS claim inventory');pcs.onclick=()=>download(`pcs-claims-${idx+1}.json`,r.pcs_claim_inventory);actions.append(pcs);
  const btn=make('button','btn secondary','Copy SHA-256');btn.onclick=async()=>{try{await navigator.clipboard.writeText(r.sha256);btn.textContent='Copied'}catch{btn.textContent='Copy unavailable (use receipt)'}};actions.append(btn);
  rep.append(actions);host.append(rep);
 }
 renderComparison();
}
function renderComparison(){const host=el('compare');host.replaceChildren();
 const byFamily=new Map();for(const r of state.reports){if(!byFamily.has(r.family))byFamily.set(r.family,[]);byFamily.get(r.family).push(r)}
 for(const [family,rs] of byFamily){if(rs.length<2)continue;
 const box=make('section','compare');box.append(make('h3','',`Automatic ${family.toUpperCase()} comparison`));
 const a=rs[0],b=rs[rs.length-1];let changes=[];
 for(const k of familyMetricKeys[family]||[]){if(a.metrics[k]!==undefined&&b.metrics[k]!==undefined&&JSON.stringify(a.metrics[k])!==JSON.stringify(b.metrics[k]))changes.push(`${k.replaceAll('_',' ')}: ${metricDisplay(k,a.metrics[k])} → ${metricDisplay(k,b.metrics[k])}`)}
 if(a.sha256!==b.sha256&&changes.length===0)changes.push('Artifact bytes differ although tracked summary metrics match');
 box.append(make('p','',`${short(a.filename)} → ${short(b.filename)}. ${changes.length?changes.join(' · '):'No differences in tracked metrics or file hash.'} This is a structural drift comparison, not a safety regression verdict.`));host.append(box);
 }
}
async function inspect(files){el('analyze').disabled=true;state.reports=[];renderReports();
 for(let i=0;i<files.length;i++){
  setNotice(`Inspecting ${i+1}/${files.length}: ${files[i].name}…`);
  try{
   const resp=await fetch('/api/analyze',{method:'POST',body:files[i],headers:{
     'Content-Type':'application/octet-stream',
     'X-PCS-Filename':encodeURIComponent(files[i].name),
     'X-PCS-Policy':encodeURIComponent(JSON.stringify(policy()))
   }});const obj=await resp.json();
   if(!resp.ok)throw Error(obj.detail||('HTTP '+resp.status));
   state.reports.push(obj);renderReports();
  }catch(err){const r={filename:files[i].name,bytes:files[i].size,sha256:'unavailable',family:'unknown',decision:'OPEN',metrics:{},checks:[{id:'UPLOAD_FAILED',status:'OPEN',title:'Inspection did not complete',evidence:String(err)}],limitations:['No safety result or artifact fingerprint is available.']};state.reports.push(r);renderReports();}
 }
 setNotice(`Analyzed ${state.reports.length} file(s). Check OPEN obligations before drawing conclusions.`);el('analyze').disabled=false;
}
el('analyze').onclick=()=>{if(state.files.length)inspect(state.files)};
el('experiment').onclick=async()=>{
 try{
   el('bound').checked=true;el('witness').checked=true;el('reference').checked=true;
   el('inmin').value='-1';el('inmax').value='1';el('outmin').value='0';el('outmax').value='0.5';
   const res=await fetch('/api/sample/demo_relu_violation.onnx');if(!res.ok)throw Error('Demo artifact missing');
   const f=new File([await res.blob()],'demo_relu_violation.onnx');
   state.files=[f];renderFiles();await inspect([f]);
 }catch(e){setNotice('Experiment could not run: '+String(e))}
};
el('dense-demo').onclick=async()=>{
 try{
  el('bound').checked=true;el('witness').checked=true;el('reference').checked=true;
  el('inmin').value='-1';el('inmax').value='1';el('outmin').value='0';el('outmax').value='1';
  const name='demo_dense_neural_violation.onnx',res=await fetch('/api/sample/'+name);
  if(!res.ok)throw Error('Neural example unavailable');const f=new File([await res.blob()],name);
  state.files=[f];renderFiles();await inspect([f]);
 }catch(e){setNotice('Neural experiment could not run: '+String(e))}
};
el('partition-demo').onclick=async()=>{
 try{
  el('bound').checked=true;el('partition').checked=true;el('partition-leaves').value='16';
  el('witness').checked=false;el('reference').checked=false;el('torch').checked=false;
  el('inmin').value='-1';el('inmax').value='1';el('outmin').value='0';el('outmax').value='1';
  const name='demo_partition_abs.onnx',res=await fetch('/api/sample/'+name);
  if(!res.ok)throw Error('Proof demonstration unavailable');const f=new File([await res.blob()],name);
  state.files=[f];renderFiles();await inspect([f]);
 }catch(e){setNotice('Partition experiment failed: '+String(e))}
};
el('iris-demo').onclick=async()=>{
 try{
  const profileRes=await fetch('/api/iris-demo-profile');if(!profileRes.ok)throw Error('Iris review policy unavailable');
  const prof=await profileRes.json();el('bound').checked=false;el('relational').checked=true;el('activation-cases').checked=false;
  el('relation-coeffs').value=prof.properties[0].output_coefficients.join(',');
  el('relation-limit').value=prof.properties[0].upper_limit;
  el('per-feature-box').value=JSON.stringify(prof.reviewer_box);
  const name='demo_trained_iris_mlp.onnx',res=await fetch('/api/sample/'+name);
  if(!res.ok)throw Error('Trained Iris model unavailable');const f=new File([await res.blob()],name);
  state.files=[f];renderFiles();await inspect([f]);
 }catch(e){setNotice('Trained neural network demo failed: '+String(e))}
};
async function compareUpdate(oldFile,newFile){
 const host=el('update-results');host.replaceChildren();
 if(!oldFile||!newFile||!oldFile.name.toLowerCase().endsWith('.onnx')||!newFile.name.toLowerCase().endsWith('.onnx')){
   setNotice('Choose exactly two ONNX models: old first, new second.');return;
 }
 try{
  const old=new Uint8Array(await oldFile.arrayBuffer()),next=new Uint8Array(await newFile.arrayBuffer());
  if(old.length+next.length>8*1024*1024)throw Error('Paired analysis is limited to 8 MiB total');
  const body=new Uint8Array(4+old.length+next.length);
  new DataView(body.buffer).setUint32(0,old.length,true);
  body.set(old,4);body.set(next,4+old.length);
  const pol={input_box:JSON.parse(el('per-feature-box').value.trim()||'[]'),
   output_coefficients:el('relation-coeffs').value.split(',').map(x=>x.trim()).filter(Boolean),
   baseline_upper_limit:el('relation-limit').value.trim(),
   drift_upper_limit:el('drift-limit').value.trim(),
   required_new_upper_limit:el('new-limit').value.trim()};
  // For 1D examples, use the shared box. For a higher-dimensional model,
  // the reviewer must provide a matching independently chosen feature box.
  if(!pol.input_box.length)pol.input_box=[[String(el('inmin').value),String(el('inmax').value)]];
  const result=await fetch('/api/compare-update',{method:'POST',body,
   headers:{'Content-Type':'application/octet-stream','X-PCS-Update-Policy':encodeURIComponent(JSON.stringify(pol))}});
  const r=await result.json();if(!result.ok)throw Error(r.detail||('HTTP '+result.status));
  const panel=make('section','evidencebox');
  panel.append(make('h3','',r.status==='PROVED_CONDITIONALLY'?'Proof-gated model update: CONDITIONAL ACCEPTANCE':'Model update: OPEN / NO PROOF'));
  panel.append(make('p','',r.status==='PROVED_CONDITIONALLY'?`The old model's scoped property and the same-input update-drift bound independently check out. Derived new bound: ${r.composition.derived_new_model_upper_bound}. Do not confuse this with deployment or arbitrary runtime safety.`:'A complete, independently checkable update argument could not be constructed; no acceptance issued.'));
  panel.append(make('pre','',JSON.stringify({baseline:r.baseline.status,drift:r.update.status,
    derived_new_upper:r.composition?.derived_new_model_upper_bound||null,
    baseline_reason:r.baseline.reason||null,drift_reason:r.update.reason||null,
    old_sha256:r.old_model_sha256,new_sha256:r.new_model_sha256},null,2)));
  const save=make('button','btn secondary','Download model-update evidence');
  save.onclick=()=>download('pcs-proof-gated-update-assessment-v06.json',r);panel.append(save);
  if(r.baseline.certificate){const btn=make('button','btn secondary','Download baseline proof');btn.onclick=()=>download('pcs-baseline-proof.json',r.baseline.certificate);panel.append(btn)}
  if(r.update.certificate){const btn=make('button','btn secondary','Download drift proof');btn.onclick=()=>download('pcs-update-drift-proof.json',r.update.certificate);panel.append(btn)}
  panel.append(make('p','hint','The suggested reviewer policies embedded in the evidence are not trust anchors. A reviewer must obtain and pin the intended old/new model hashes, input box and safety thresholds independently.'));
  host.append(panel);
  setNotice('Two-model analysis finished. Exact rational conditional verdict: '+r.status);
 }catch(err){const panel=make('section','evidencebox');panel.append(make('h3','','Model update analysis unavailable'),make('p','',String(err)));host.append(panel);setNotice(String(err))}
}
el('update-selected').onclick=()=>compareUpdate(state.files[0],state.files[1]);
async function fp32Selected(file){
 const host=el('fp32-results');host.replaceChildren();
 if(!file || !file.name.toLowerCase().endsWith('.onnx')){setNotice('Select one supported dense ONNX model for IEEE binary32 analysis.');return}
 try{
  const claim={input_box:JSON.parse(el('per-feature-box').value.trim()||'[]'),
    input_min:el('inmin').value.trim(),input_max:el('inmax').value.trim(),
    output_coefficients:el('relation-coeffs').value.split(',').map(x=>x.trim()).filter(Boolean),
    upper_limit:el('relation-limit').value.trim()};
  const resp=await fetch('/api/fp32-assure',{method:'POST',body:file,
    headers:{'Content-Type':'application/octet-stream','X-PCS-Fp32-Claim':encodeURIComponent(JSON.stringify(claim))}});
  const r=await resp.json();if(!resp.ok)throw Error(r.detail||'HTTP '+resp.status);
  const a=r.assessment,panel=make('section','evidencebox');
  panel.append(make('h3','',a.status==='PROVED_CONDITIONALLY'?'Sequential binary32 property: CONDITIONAL PROOF':'Binary32 property remains OPEN'));
  panel.append(make('p','',a.status==='PROVED_CONDITIONALLY'?
    'Exact rational interval checker covers all float32 input values in the stated box, assuming separately rounded, ordered binary32 operations. It is not a Lean proof or a statement about every ONNX Runtime backend.':
    (a.reason||'The interval analysis could not establish this output relation; OPEN is not an unsafe or safe verdict.')));
  panel.append(make('pre','',JSON.stringify({status:a.status,upper_bound:a.computed_upper_bound||null,
    required_upper_limit:a.required_upper_limit||null,model_sha256:a.model_sha256||null,
    output_intervals:a.output_intervals||null,lean:a.lean_kernel_verification,runtime:a.external_runtime_equivalence},null,2)));
  const save=make('button','btn secondary','Download float32 analysis and suggested policy');
  save.onclick=()=>download('pcs-binary32-conditional-assurance-v07.json',r);panel.append(save);
  panel.append(make('p','hint','A reviewer must independently pin model bytes, box, coefficients and limit. This is a particular sequential float32 value-semantics claim, not a live ONNX Runtime or Lean-kernel verdict.'));
  host.append(panel);setNotice('Binary32 interval analysis finished: '+a.status);
 }catch(e){setNotice('Binary32 analysis: '+String(e));const panel=make('section','evidencebox');panel.append(make('p','',String(e)));host.append(panel)}
}
el('fp32-selected').onclick=()=>fp32Selected(state.files.find(f=>f.name.toLowerCase().endsWith('.onnx')));
async function compareUpdateFp32(oldFile,newFile){
 const host=el('fp32-results');host.replaceChildren();
 if(!oldFile||!newFile||!oldFile.name.endsWith('.onnx')||!newFile.name.endsWith('.onnx')){
  setNotice('Select two ONNX models: original first, updated second.');return;
 }
 try{
  const old=new Uint8Array(await oldFile.arrayBuffer()),next=new Uint8Array(await newFile.arrayBuffer());
  if(old.length+next.length>8*1024*1024)throw Error('Combined model size exceeds 8 MiB');
  const body=new Uint8Array(4+old.length+next.length);new DataView(body.buffer).setUint32(0,old.length,true);
  body.set(old,4);body.set(next,4+old.length);
  const p={input_box:JSON.parse(el('per-feature-box').value.trim()||'[]'),
   output_coefficients:el('relation-coeffs').value.split(',').map(x=>x.trim()).filter(Boolean),
   baseline_upper_limit:el('relation-limit').value.trim(),drift_upper_limit:el('drift-limit').value.trim(),
   required_new_upper_limit:el('new-limit').value.trim(),
   fp32_required_new_upper_limit:el('fp32-new-limit').value.trim()};
  if(!p.input_box.length)p.input_box=[[el('inmin').value,el('inmax').value]];
  const res=await fetch('/api/compare-update-fp32',{method:'POST',body,
    headers:{'Content-Type':'application/octet-stream','X-PCS-Fp32-Update-Policy':encodeURIComponent(JSON.stringify(p))}});
  const report=await res.json();if(!res.ok)throw Error(report.detail||('HTTP '+res.status));
  const a=report.binary32_lift;const panel=make('section','evidencebox');
  panel.append(make('h3','',a.status==='PROVED_CONDITIONALLY'?
    'Model update and rounding budget: CONDITIONAL PROOF':'Model update and rounding budget: OPEN'));
  panel.append(make('p','',a.status==='PROVED_CONDITIONALLY'?
    'The exact-real baseline and update-drift certificates replay, and a conservative IEEE binary32 rounding allowance still meets the requested bound under declared arithmetic assumptions. Not Lean verified; no actual ONNX Runtime equivalence.':
    (a.reason||'No complete conditional update argument; no deployment approval.')));
  panel.append(make('pre','',JSON.stringify({exact_real:report.exact_real.status,
    float32_status:a.status,derived_float32_upper_approx:readableFraction(a.derived_float32_upper_bound),
    reviewer_required_limit:a.reviewer_required_upper_limit||null,
    rounding_margin_approx:readableFraction(a.new_model_rounding_cushion),
    baseline:a.verified_real_baseline_upper_bound||null,drift:a.verified_real_drift_upper_bound||null,
    lean:report.lean_kernel_verification,runtime:report.runtime_equivalence},null,2)));
  const save=make('button','btn secondary','Download FP32 proof-gated update evidence');
  save.onclick=()=>download('pcs-fp32-model-update-v07.json',report);panel.append(save);
  panel.append(make('p','hint','User-interface policies are only suggested: external reviewers must independently pin both model hashes, input box and limits. No proof of full runtime safety.'));
  host.append(panel);setNotice('Float32 model-update analysis finished: '+a.status);
 }catch(e){setNotice('Float32 update error: '+String(e));host.append(make('p','',String(e)))}
}
el('fp32-update-selected').onclick=()=>compareUpdateFp32(state.files[0],state.files[1]);
el('fp32-update-demo').onclick=async()=>{
 try{
  const pr=await fetch('/api/iris-demo-profile');if(!pr.ok)throw Error('Missing Iris demonstration');
  const profile=await pr.json();el('per-feature-box').value=JSON.stringify(profile.reviewer_box);
  el('relation-coeffs').value='-1,1,0';el('relation-limit').value='-1/2';
  el('drift-limit').value='1/8';el('new-limit').value='-3/8';el('fp32-new-limit').value='-37/100';
  const names=['demo_trained_iris_mlp.onnx','demo_trained_iris_updated.onnx'];let fs=[];
  for(const name of names){const res=await fetch('/api/sample/'+name);if(!res.ok)throw Error('Sample unavailable');fs.push(new File([await res.blob()],name))}
  state.files=fs;renderFiles();await compareUpdateFp32(fs[0],fs[1]);
 }catch(e){setNotice('FP32 updated-model demo failed: '+String(e))}
};

el('fp32-demo').onclick=async()=>{
 try{
  el('per-feature-box').value='[["-1","1"],["-1","1"]]';
  el('relation-coeffs').value='1,0';el('relation-limit').value='5/4';
  const name='demo_dense_neural_violation.onnx',res=await fetch('/api/sample/'+name);
  if(!res.ok)throw Error('Demo unavailable');const f=new File([await res.blob()],name);
  state.files=[f];renderFiles();await fp32Selected(f);
 }catch(e){setNotice('Binary32 demo: '+String(e))}
};

el('update-demo').onclick=async()=>{
 try{
  const pr=await fetch('/api/iris-demo-profile');if(!pr.ok)throw Error('Missing Iris demo policy');
  const p=await pr.json();el('per-feature-box').value=JSON.stringify(p.reviewer_box);
  el('relation-coeffs').value='-1,1,0';el('relation-limit').value='-1/2';
  el('drift-limit').value='1/8';el('new-limit').value='-3/8';
  const names=['demo_trained_iris_mlp.onnx','demo_trained_iris_updated.onnx'];let files=[];
  for(const name of names){const r=await fetch('/api/sample/'+name);if(!r.ok)throw Error('Missing model '+name);files.push(new File([await r.blob()],name))}
  state.files=files;renderFiles();await compareUpdate(files[0],files[1]);
 }catch(err){setNotice('Proof-gated update demo failed: '+String(err))}
};
el('activation-demo').onclick=async()=>{
 try{
  el('bound').checked=false;el('relational').checked=true;el('activation-cases').checked=true;
  el('activation-leaves').value='16';el('relation-coeffs').value='1';el('relation-limit').value='0';
  el('inmin').value='-1';el('inmax').value='1';el('per-feature-box').value='[]';
  const name='demo_activation_identity.onnx',res=await fetch('/api/sample/'+name);
  if(!res.ok)throw Error('Activation example unavailable');const f=new File([await res.blob()],name);
  state.files=[f];renderFiles();await inspect([f]);
 }catch(e){setNotice('Activation proof experiment failed: '+String(e))}
};
el('relational-demo').onclick=async()=>{
 try{
  el('bound').checked=false;el('relational').checked=true;el('relation-coeffs').value='-1,1';
  el('relation-limit').value='-1/4';el('inmin').value='-1';el('inmax').value='1';el('per-feature-box').value='[]';
  const name='demo_relational_margin.onnx',res=await fetch('/api/sample/'+name);
  if(!res.ok)throw Error('Relational example unavailable');const f=new File([await res.blob()],name);
  state.files=[f];renderFiles();await inspect([f]);
 }catch(e){setNotice('Invariant experiment could not run: '+String(e))}
};
el('milp-demo').onclick=async()=>{
 try{
  el('bound').checked=true;el('witness').checked=true;el('reference').checked=true;
  el('milp').checked=true;el('milp-timeout').value='6';el('partition').checked=false;
  el('inmin').value='-1';el('inmax').value='1';el('outmin').value='0';el('outmax').value='0.5';
  const name='demo_hidden_spike.onnx',res=await fetch('/api/sample/'+name);
  if(!res.ok)throw Error('Hidden spike sample unavailable');const f=new File([await res.blob()],name);
  state.files=[f];renderFiles();await inspect([f]);
 }catch(e){setNotice('Solver-guided challenge failed: '+String(e))}
};
el('guarded-live').onclick=async()=>{
 const host=el('guarded-results');host.replaceChildren();
 try{
  const selected=state.files.find(f=>f.name.endsWith('.agenttrace.json'));
  let body=selected;
  if(!body){const res=await fetch('/api/sample/demo_agent_attack_blocked.agenttrace.json');if(!res.ok)throw Error('Demo unavailable');body=await res.blob()}
  const res=await fetch('/api/guarded-demo',{method:'POST',body,headers:{'Content-Type':'application/json'}});
  const data=await res.json();if(!res.ok)throw Error(data.detail||('HTTP '+res.status));
  const panel=make('section','evidencebox');panel.append(make('h3','','Actual pre-dispatch guard — synthetic backend'));
  panel.append(make('p','',`${data.executions} allowed tool actions executed on the in-memory synthetic backend, ${data.denied} denied before any effect. The host verified its local HMAC audit chain: ${data.audit_chain_verified_inside_host}. NO external publication or trusted runtime attestation.`));
  panel.append(make('pre','',JSON.stringify({publications:data.publications,decisions:data.audit_records.map(e=>({sequence:e.record.sequence,action_id:e.record.action_id,decision:e.record.decision}))},null,2)));
  const save=make('button','btn secondary','Download synthetic execution evidence');save.onclick=()=>download('pcs-guarded-execution-v0.5.json',data);
  panel.append(save);host.append(panel);setNotice('Guarded in-memory action demo completed. No network tools were invoked.');
 }catch(e){setNotice('Guarded execution demo failed: '+String(e))}
};
el('attack-demo').onclick=async()=>{
 const host=el('guarded-results');host.replaceChildren();
 try{
  const res=await fetch('/api/attack-campaign',{method:'POST'});
  const data=await res.json();if(!res.ok)throw Error(data.detail||('HTTP '+res.status));
  const panel=make('section','evidencebox');panel.append(make('h3','','Host-side synthetic metamorphic challenge'));
  panel.append(make('p','',`${data.denied_before_effect}/${data.total_adversarial_proposals} unauthorized proposals denied. ${data.synthetic_publications} synthetic publications. Only fixed test variants and an in-memory backend were exercised.`));
  panel.append(make('pre','',JSON.stringify({categories_tested:data.categories_tested,unexpected_authorizations:data.unexpected_authorizations,host_hmac_chain_verified:data.host_hmac_chain_verified},null,2)));
  const save=make('button','btn secondary','Download adversarial challenge results');save.onclick=()=>download('pcs-agent-challenge-v0.5.json',data);
  panel.append(save);host.append(panel);setNotice('Synthetic adversarial campaign completed; this does not establish general prompt-injection immunity.');
 }catch(e){setNotice('Guard challenge failed: '+String(e))}
};
el('agentdemo').onclick=async()=>{
 try{
  const name='demo_agent_attack_blocked.agenttrace.json',res=await fetch('/api/sample/'+name);
  if(!res.ok)throw Error('Agent demo artifact missing');const f=new File([await res.blob()],name);
  state.files=[f];renderFiles();await inspect([f]);
 }catch(e){setNotice('Agent demo could not run: '+String(e))}
};
el('sample').onclick=async()=>{
 try{const manifest=await fetch('/api/samples');if(!manifest.ok)throw Error('Sample index unavailable');const names=await manifest.json();const samples=[];
 for(const n of names){const res=await fetch(`/api/sample/${encodeURIComponent(n)}`);if(!res.ok)throw Error('Sample unavailable');const blob=await res.blob();samples.push(new File([blob],n))}addFiles(samples);setNotice('Real sample files loaded. Click Inspect selected files.')
 }catch(e){setNotice(String(e))}
};
el('exportall').onclick=()=>download('pcs-assessments-bundle-unsigned.json',{schema:'pcs-assessment-bundle-v0.5',reports:state.reports});
fetch('/api/status').then(r=>r.json()).then(s=>{el('backend').textContent=s.ok?`Local Studio v${s.extension_version||s.version} (intake ${s.version}) · ONNX official checker: ${s.onnx_checker_version||'not installed'} · conditional proofs + exact relational dual certificates + solver-guided challenges`:'Inspector offline'}).catch(()=>el('backend').textContent='Inspector unavailable');
renderFiles();renderReports();
