const panel = document.getElementById('panel');
let current = null;

function show(card){
  current = card;
  panel.hidden = false;
  document.getElementById('project').textContent = card.project_id || '(unknown)';
  document.getElementById('tech').textContent = JSON.stringify(card.technical_verification ?? card.statuses?.computational_replay ?? {}, null, 2);
  document.getElementById('sci').textContent = JSON.stringify(card.scientific_validation ?? card.external_lab_validation ?? {}, null, 2);
  const ul = document.getElementById('questions');
  ul.innerHTML = '';
  for (const q of (card.unresolved_questions || [])){
    const li = document.createElement('li');
    li.textContent = q;
    ul.appendChild(li);
  }
}

document.getElementById('file').addEventListener('change', async (e) => {
  const f = e.target.files?.[0];
  if (!f) return;
  const text = await f.text();
  show(JSON.parse(text));
});

document.getElementById('demo').addEventListener('click', () => {
  show({
    project_id: 'synth-pkpd-001',
    technical_verification: {status: 'COMPUTATIONALLY_TESTED', reason: 'demo'},
    scientific_validation: {status: 'OPEN', reason: 'No outside laboratory has completed this pilot.'},
    unresolved_questions: ['Would an independent laboratory accept this workflow on real PK data?'],
    disclaimer: 'Demo card only.'
  });
});

document.getElementById('export').addEventListener('click', () => {
  if (!current) return;
  const blob = new Blob([JSON.stringify(current, null, 2)], {type:'application/json'});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'assurance_card.json';
  a.click();
});
