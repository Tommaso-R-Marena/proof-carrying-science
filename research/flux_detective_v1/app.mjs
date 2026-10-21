import {puzzle, parseSeed, exportCase, LEVEL_COUNT} from './engine.mjs';
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
  const blob = new Blob([JSON.stringify(exportCase(current, choice), null, 2) + '\n'], {type:'application/json'});
  const url = URL.createObjectURL(blob), a = el('a'); a.href = url;
  a.download = `flux-${seed}-level-${level+1}-trace-${choice+1}.json`;
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
}
function start(text) {
  try { const parsed = parseSeed(text); seed = parsed; level = 0; score = 0; $('seed').value = String(seed); history.replaceState(null, '', `#seed=${seed}`); $('error').textContent = ''; render(); }
  catch (e) { $('error').textContent = e.message; }
}
$('seed-form').addEventListener('submit', e => { e.preventDefault(); start($('seed').value); });
$('hint').addEventListener('click', () => { if (solved) return; hinted = true; $('hint').disabled = true; reveal(); $('feedback').textContent = 'Residual = observed − expected. Zero at every cell and step is what the model requires.'; });
$('next').addEventListener('click', () => { if (!solved || level >= LEVEL_COUNT-1) return; level++; render(); $('case-title').scrollIntoView({block:'start'}); });
const match = /^#seed=(.*)$/.exec(location.hash);
start(match ? match[1] : '20261021');
