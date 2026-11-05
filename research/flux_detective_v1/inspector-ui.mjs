import {MAX_INPUT_BYTES} from './inspector.mjs';
const $=id=>document.getElementById(id);
const node=(tag,text)=>{const e=document.createElement(tag);if(text!==undefined)e.textContent=text;return e;};
let epoch=0,worker=null,timer=null,snapshot=null,copyEpoch=0;
const COMMAND='python -m research.flux_detective_v1.check inspected-case.json ./new-evidence';
$('inspect-command').textContent=COMMAND;
function stop(){clearTimeout(timer);worker?.terminate();worker=null;}
function clear(message){snapshot=null;$('inspect-download').disabled=true;$('inspect-status').textContent=message;$('inspect-result').replaceChildren();$('inspect-digest').textContent='';}
function refuse(id,message){if(id!==epoch)return;stop();clear('Browser analysis refused. Lean has not run.');$('inspect-error').textContent=message;}
function present(result){
  $('inspect-status').textContent=result.status==='BROWSER_MODEL_MATCH'?'Exact browser arithmetic matches the declared model. Lean has not run.':'The browser found an exact model mismatch. Lean has not run.';
  const root=$('inspect-result'),s=result.summaries;
  root.replaceChildren(node('p',`${result.ids.length} cells · ${result.steps} updates · Mass ${s.mass?'PASS':'FAIL'} · Bounds ${s.bounds?'PASS':'FAIL'} · Historical energy ${s.historical_energy?'PASS':'FAIL'}`),
    node('p',`Declared amount ${s.declared_amount}; recorded final amount ${s.final_amount}; recorded final energy ${s.final_energy}.`));
  const f=result.fault;
  root.append(node('p',f?`${f.kind==='recurrence'?'Update '+(f.step+1):f.kind+' row '+f.step}${f.cell===null?'':', '+result.ids[f.cell]}: observed ${f.observed}; expected ${f.expected}; exact residual ${f.residual}.`:'Every recorded initial value, update and time matches the model.'));
  const chart=node('div');chart.className='concentration-bars';
  result.ids.forEach((id,i)=>{const label=node('label',`${id}: ${result.states.at(-1)[i]}`),meter=node('meter');meter.min=0;meter.max=1000;meter.value=result.bars[i];meter.setAttribute('aria-label',`${id}, relative concentration; exact value ${result.states.at(-1)[i]}`);label.append(meter);chart.append(label);});
  root.append(node('p','Final-state bars are normalized to the declared initial range and clipped for display. The exact values above each bar determine the calculation.'),chart);
  const details=node('details'),summary=node('summary','Inspect every recorded row'),wrap=node('div'),table=node('table');wrap.className='table-wrap inspector-table';
  const head=node('thead'),header=node('tr');['Time',...result.ids].forEach(text=>{const th=node('th',text);th.scope='col';header.append(th);});head.append(header);table.append(head);
  const body=node('tbody');result.states.forEach((row,k)=>{const tr=node('tr'),th=node('th',result.times[k]);th.scope='row';tr.append(th);row.forEach(x=>tr.append(node('td',x)));body.append(tr);});table.append(body);wrap.append(table);details.append(summary,wrap);root.append(details);
}
async function inspectBytes(bytes,id){
  if(id!==epoch)return;
  if(bytes.byteLength>MAX_INPUT_BYTES){refuse(id,'Choose a JSON export no larger than 256 KiB.');return;}
  try{
    const raw=new TextDecoder('utf-8',{fatal:true,ignoreBOM:true}).decode(bytes);
    const digest=globalThis.crypto?.subtle?Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),b=>b.toString(16).padStart(2,'0')).join(''):null;
    if(id!==epoch)return;
    const task=new Worker(new URL('./inspector-worker.mjs',import.meta.url),{type:'module'});worker=task;
    timer=setTimeout(()=>refuse(id,'The five-second browser budget expired. Use the independent CLI for this case.'),5000);
    task.onerror=()=>refuse(id,'The local analysis worker could not run. Use the independent CLI.');
    task.onmessage=event=>{
      if(id!==epoch||worker!==task||event.data?.id!==id)return;
      const {result,error}=event.data;
      if(error){refuse(id,error);return;}
      if(!result||result.format!=='pcs-browser-trace-diagnostic-v1'||!['BROWSER_MODEL_MATCH','BROWSER_MODEL_MISMATCH'].includes(result.status)||result.kernel_checked!==false||result.pcs_authority!==false||result.empirical_validation!==false){refuse(id,'Unexpected diagnostic response. No verification verdict was accepted.');return;}
      stop();snapshot=bytes;present(result);$('inspect-error').textContent='';$('inspect-download').disabled=false;
      $('inspect-digest').textContent=digest?`Input SHA-256: ${digest}`:'Input digest unavailable in this browser context. Original captured bytes are retained.';
    };
    task.postMessage({id,raw});
  }catch(error){refuse(id,`Input could not be inspected: ${error.message}`);}
}
function begin(){const id=++epoch;stop();clear('Reading captured input; Lean has not run.');$('inspect-error').textContent='';return id;}
$('inspect-file').addEventListener('change',async event=>{
  const id=begin(),file=event.target.files?.[0];if(!file){clear('Choose an exported case. Lean has not run.');return;}
  if(file.size>MAX_INPUT_BYTES){refuse(id,'Choose a JSON export no larger than 256 KiB.');return;}
  try{await inspectBytes(new Uint8Array(await file.arrayBuffer()),id);}catch(error){refuse(id,error.message);}
});
window.addEventListener('pcs:inspect-case',event=>{
  const id=begin();if(typeof event.detail?.raw!=='string'){refuse(id,'Case text required.');return;}
  void inspectBytes(new TextEncoder().encode(event.detail.raw),id);$('inspect-title').scrollIntoView({block:'start'});
});
$('inspect-download').addEventListener('click',()=>{
  if(!snapshot)return;const url=URL.createObjectURL(new Blob([snapshot],{type:'application/json'})),a=node('a');a.href=url;a.download='inspected-case.json';document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);
});
$('inspect-copy').addEventListener('click',async()=>{
  const request=++copyEpoch;let budget;
  $('inspect-copy-status').textContent='Copying command. You can also select the command below.';
  try{
    await Promise.race([navigator.clipboard.writeText(COMMAND),new Promise((_,reject)=>{budget=setTimeout(()=>reject(Error('Clipboard budget expired')),2000);})]);
    if(request===copyEpoch)$('inspect-copy-status').textContent='Replay command copied. Run it from the reviewed research checkout.';
  }catch{if(request===copyEpoch)$('inspect-copy-status').textContent='Clipboard unavailable. Select and copy the command below.';}
  finally{clearTimeout(budget);}
});
for(const button of document.querySelectorAll('[data-lab-target]'))button.addEventListener('click',()=>$(button.dataset.labTarget).scrollIntoView({block:'start'}));
