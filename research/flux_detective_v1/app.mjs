import {puzzle, parseSeed, exportCase, LEVEL_COUNT} from './engine.mjs';
import {forgeCase, regionFor, sliderAmount} from './forge.mjs';
const $ = id => document.getElementById(id);
let seed, level = 0, score = 0, mistakes = 0, hinted = false, solved = false, current;
function el(tag, text, cls) { const e = document.createElement(tag); if (text !== undefined) e.textContent = text; if (cls) e.className = cls; return e; }
function reveal() {
  $('explanation').replaceChildren();
  current.candidates.forEach((c, i) => {
    const f = c.analysis.fault;
    $('explanation').append(el('p', f ? `Trace ${i+1}: update ${f.step+1}, ${current.contract.cells[f.cell].id}. Observed ${f.observed}; expected ${f.expected}; residual ${f.residual}. A nonzero residual breaks the recurrence.` : `Trace ${i+1}: every exact update matches the declared recurrence.`, 'residual'));
  });
}
function download(choice) {
  saveBundle(exportCase(current, choice), `flux-${seed}-level-${level+1}-trace-${choice+1}.json`);
}
function saveBundle(bundle, name) {
  const blob = new Blob([JSON.stringify(bundle, null, 2) + '\n'], {type:'application/json'});
  const url = URL.createObjectURL(blob), a = el('a'); a.href = url;
  a.download = name;
  document.body.append(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000);
}
function choose(i) {
  if (solved) return;
  const c = current.candidates[i], card = $('candidates').children[i];
  if (c.analysis.fault) { mistakes++; card.classList.add('wrong'); card.querySelector('.choose').disabled = true; $('feedback').textContent = 'A convincing impostor. These summaries pass, but an exact update differs. Try again, or inspect the residuals.'; return; }
  solved = true; score += Math.max(0, 3 - mistakes - Number(hinted)); card.classList.add('correct');
  $('score').textContent = `${score} / ${LEVEL_COUNT*3} stars`;
  $('feedback').textContent = level === LEVEL_COUNT-1 ? 'Campaign complete. You distinguished a model check from an attractive summary. Try another seed or export a case for Lean replay.' : 'Case solved. This trace follows every declared update.';
  for (const b of document.querySelectorAll('.choose')) b.disabled = true;
  $('hint').disabled = true; $('next').hidden = level === LEVEL_COUNT-1; reveal();
}
function render() {
  mistakes = 0; hinted = false; solved = false; current = puzzle(seed, level);
  $('progress').textContent = `Case ${level+1} of ${LEVEL_COUNT}`;
  $('case-title').textContent = ['The quiet shortcut', 'Unequal compartments', 'The delayed swap', 'A longer chain', 'History matters', 'The final audit'][level];
  $('score').textContent = `${score} / ${LEVEL_COUNT*3} stars`;
  $('brief').textContent = `Find the trace that obeys the model across ${current.contract.steps} update${current.contract.steps === 1 ? '' : 's'}. Start with three stars per case; each wrong choice or hint costs one. Every green summary below is true—even for the impostors.`;
  $('model').replaceChildren();
  for (const c of current.contract.cells) { const box = el('div', undefined, 'cell'); box.append(el('strong', c.id), el('div', `Volume ${c.volume}`), el('div', `Starts at ${c.initial_concentration}`)); $('model').append(box); }
  $('model').append(el('div', `Connected in order: ${current.contract.cells.map(c => c.id).join(' ↔ ')}. Every edge has conductance 1/8. Time step = 1/4.`, 'model-note'));
  $('candidates').replaceChildren();
  current.candidates.forEach((c, i) => {
    const card = el('article', undefined, 'candidate'), heading = el('h3', `Trace ${i+1}`); heading.append(el('span', 'EXACT FRACTIONS', 'badge')); card.append(heading);
    const wrap = el('div', undefined, 'table-wrap'), table = el('table');
    const caption = el('caption', `Concentrations for trace ${i+1}`); table.append(caption);
    const head = el('thead'), hr = el('tr');
    ['Step', ...current.contract.cells.map(c => c.id)].forEach(s => { const th = el('th', s); th.scope = 'col'; hr.append(th); }); head.append(hr); table.append(head);
    const body = el('tbody'); c.rows.forEach((row, k) => { const tr = el('tr'); const th = el('th', String(k)); th.scope = 'row'; tr.append(th); row.forEach(x => tr.append(el('td', String(x)))); body.append(tr); }); table.append(body); wrap.append(table); card.append(wrap);
    card.append(el('p', [[c.analysis.mass, 'Mass conserved'], [c.analysis.bounds, 'In bounds'], [c.analysis.energy, 'Energy nonincreasing']].map(([pass, label]) => `${pass ? '✓' : '✗'} ${label}`).join(' · '), 'checks'));
    const chooseButton = el('button', 'This follows the model', 'choose'); chooseButton.addEventListener('click', () => choose(i)); card.append(chooseButton);
    const exportButton = el('button', `Export trace ${i+1}`, 'download'); exportButton.addEventListener('click', () => download(i)); card.append(exportButton); $('candidates').append(card);
  });
  $('feedback').textContent = ''; $('explanation').replaceChildren(); $('next').hidden = true; $('hint').disabled = false;
  resetForge();
}
let forged;
function updateForge(amount) {
  try {
    forged=forgeCase(current, Number($('forge-left').value), Number($('forge-right').value), amount);
    const s=forged.summary, f=forged.analysis.fault;
    $('forge-amount').value=amount; $('forge-error').textContent=''; $('forge-export').disabled=false;
    $('forge-status').textContent=s.invariant_impostor ? 'Impostor constructed: all stronger summaries pass, but the exact model fails.' : s.exact_model ? 'Exact model restored. No recurrence fault.' : 'The model fails. One or more stronger conditions also fail.';
    const label=`[${s.low}, ${s.high}]`; $('forge-slider').setAttribute('aria-valuetext', `Amount ${amount}; exact interval ${label}`);
    $('forge-slider').disabled=s.low===s.high;
    const range=forged.region.high.sub(forged.region.low);
    if(range.n===0n) $('forge-slider').value='0';
    else {
      const ratio=forged.region.v.mul(forged.region.x.sub(forged.rows.at(-1)[forged.left])).sub(forged.region.low).div(range);
      const tick=ratio.n*100n/ratio.d;
      $('forge-slider').value=String(tick<0n?0n:tick>100n?100n:tick);
    }
    $('forge-details').replaceChildren(el('p',`Exact stronger interval: ${label} mol. Transfer: ${amount} mol. Energy change from the model: ${s.energy_delta}.`),
      el('p',`Mass ${forged.analysis.mass?'PASS':'FAIL'} · Bounds ${forged.analysis.bounds?'PASS':'FAIL'} · Historical energy ${forged.analysis.energy?'PASS':'FAIL'} · Stronger interval ${s.inside?'PASS':'FAIL'}`),
      el('p',f ? `Exact mismatch at update ${f.step+1}, ${current.contract.cells[f.cell].id}: observed ${f.observed}, expected ${f.expected}, residual ${f.residual}.` : 'Every model update matches.'),
      el('p',`Final concentrations: ${forged.rows.at(-1).map((x,i)=>`${current.contract.cells[i].id} = ${x}`).join('; ')}`));
    if(s.low===s.high) $('forge-details').append(el('p','Only zero is allowed for this pair. Choose cells with different concentrations.'));
  } catch(e) { forged=null; $('forge-export').disabled=true; $('forge-error').textContent=e.message; $('forge-status').textContent='No current workshop result. Correct the input.'; $('forge-details').replaceChildren(); }
}
function resetForge() {
  for(const id of ['forge-left','forge-right']) { $(id).replaceChildren(); current.contract.cells.forEach((c,i)=>{ const option=el('option',c.id); option.value=String(i); $(id).append(option); }); }
  $('forge-left').value='0'; $('forge-right').value='1'; updateForge('0');
}
function start(text) {
  try { const parsed = parseSeed(text); seed = parsed; level = 0; score = 0; $('seed').value = String(seed); history.replaceState(null, '', `#seed=${seed}`); $('error').textContent = ''; render(); }
  catch (e) { $('error').textContent = e.message; }
}
$('seed-form').addEventListener('submit', e => { e.preventDefault(); start($('seed').value); });
$('hint').addEventListener('click', () => { if (solved) return; hinted = true; $('hint').disabled = true; reveal(); $('feedback').textContent = 'Residual = observed − expected. Zero at every cell and step is what the model requires.'; });
$('next').addEventListener('click', () => { if (!solved || level >= LEVEL_COUNT-1) return; level++; render(); $('case-title').scrollIntoView({block:'start'}); });
$('forge-form').addEventListener('submit', e=>{ e.preventDefault(); updateForge($('forge-amount').value); });
for(const id of ['forge-left','forge-right']) $(id).addEventListener('change',()=>updateForge('0'));
$('forge-half').addEventListener('click',()=>{ try { updateForge(sliderAmount(regionFor(current,Number($('forge-left').value),Number($('forge-right').value)),50)); } catch(e) { updateForge($('forge-amount').value); } });
$('forge-reset').addEventListener('click',()=>updateForge('0'));
$('forge-slider').addEventListener('input',()=>{ try { const r=regionFor(current,Number($('forge-left').value),Number($('forge-right').value)); updateForge(sliderAmount(r,Number($('forge-slider').value))); } catch(e) { updateForge($('forge-amount').value); } });
$('forge-export').addEventListener('click',()=>{ if(forged) saveBundle(forged.bundle,`flux-${seed}-level-${level+1}-workshop.json`); });
const match = /^#seed=(.*)$/.exec(location.hash);
start(match ? match[1] : '20261021');
