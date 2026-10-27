"""Offline, escaped, accessible presentation; loaded claims are never verdicts."""
from html import escape

from research.real_model_safety_v1.evaluate import classify
from .intake import parse
from .protocol import ACTIONS,STAGES

MODES={"loaded":"Loaded evidence · not replayed on this host",
       "live":"Live model · local execution checked",
       "replay":"Recorded responses · kernel replay checked"}

CSS='''
:root{color-scheme:light;--ink:#132d40;--muted:#435e70;--line:#d6e2e6;--paper:#f5f8fa;--accent:#086859}
*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:16px/1.55 system-ui,sans-serif}
main{max-width:1120px;margin:auto;padding:32px 24px 64px}a{color:#075c8d}a:focus-visible,summary:focus-visible{outline:3px solid #d27d06;outline-offset:4px}
.eyebrow{font-size:.85rem;letter-spacing:.1em;text-transform:uppercase;color:var(--accent);font-weight:750}
h1{font-size:clamp(2rem,5vw,3.6rem);line-height:1.08;max-width:900px;margin:16px 0}h2{line-height:1.25;margin:0 0 8px;overflow-wrap:anywhere}h3{margin:0;font-size:1rem}
.lead{max-width:800px;color:var(--muted);font-size:1.1rem}.status,.badge{display:inline-block;border:1px solid var(--line);border-radius:999px;padding:5px 12px;font-size:.86rem;font-weight:650;background:white}
.status{border-color:#8daab9}.metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:28px 0}.metric{background:white;border:1px solid var(--line);border-radius:16px;padding:20px}.metric strong{display:block;font-size:2rem;line-height:1.2}.metric span{color:var(--muted);font-size:.92rem}
.notice{background:#e7f1f4;border-left:4px solid #266f8a;padding:16px 20px;border-radius:4px}.case{margin-top:24px;background:white;border:1px solid var(--line);border-radius:20px;padding:24px}
.case-nav{margin-top:16px}.case-nav ul{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:8px 24px;padding-left:20px}.case-nav a{overflow-wrap:anywhere}
.case>.workflow-toggle h2{display:inline;font-size:1.25rem}.case[open]>.workflow-toggle{margin-bottom:16px}.fixture{font-size:.9rem;font-weight:400;color:var(--muted)}
.case-head{display:flex;gap:12px;align-items:start;justify-content:space-between}.case-head>div{min-width:0}.muted{color:var(--muted)}.task{white-space:pre-wrap;overflow-wrap:anywhere;background:var(--paper);border-radius:10px;padding:12px 16px}
.timeline{list-style:none;display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;padding:0;margin:20px 0}.step{min-width:0;border:1px solid var(--line);border-top:4px solid var(--accent);border-radius:12px;padding:16px}.step.corrected{border-top-color:#a36300}.step p{margin:8px 0;font-size:.92rem}.corrected .badge{color:#754800;background:#fff4de;border-color:#e5c88f}.accepted .badge{color:#075a45;background:#e7f6ed;border-color:#a2cebb}
pre{font:14px/1.5 ui-monospace,monospace;white-space:pre-wrap;overflow-wrap:anywhere;background:#f1f5f7;border-radius:8px;padding:12px}details{border-top:1px solid var(--line);padding:12px 0}summary{cursor:pointer;font-weight:650}code{overflow-wrap:anywhere}footer{margin-top:32px;color:var(--muted);font-size:.92rem}.legend{display:flex;gap:16px;flex-wrap:wrap}.legend span{font-weight:650}
@media(max-width:700px){main{padding:24px 16px}.metrics{grid-template-columns:repeat(2,minmax(0,1fr))}.timeline{grid-template-columns:1fr}.case{padding:18px}.case-head{display:block}.case-head .badge{margin-top:8px}}
@media print{body{background:white}.case{break-inside:avoid}main{padding:0}.metric{padding:10px}}
'''


def summary(suite):
    counts=dict(cases=len(suite.episodes),model_proposals=0,control_proposals=0,corrections=0,malformed_proposals=0,unsafe_requests=0,forbidden_requests=0)
    for episode in suite.episodes:
        case=parse(episode.case_json)
        for frame in parse(episode.frames_json):
            record=frame["record"];a=classify(record["source"],bytes.fromhex(frame["proposal_hex"]),record["action"])
            counts["model_proposals" if case["mode"]=="model" else "control_proposals"]+=1
            if case["mode"]=="model":
                counts["corrections"]+=int(a["intervention"]);counts["unsafe_requests"]+=int(a["unsafe_possible"])
                counts["forbidden_requests"]+=int(a["forbidden"])
                counts["malformed_proposals"]+=int(a["malformed"])
    return counts


def html(suite,mode="loaded"):
    if mode not in MODES:raise ValueError("Unsupported report context")
    counts=summary(suite);sections=[];navigation=[]
    for case_index,episode in enumerate(suite.episodes):
        case=parse(episode.case_json);cap=parse(episode.capture_json);frames=parse(episode.frames_json);steps=[]
        for index,frame in enumerate(frames):
            record=frame["record"];corrected=record["proposal"]!=record["action"]
            requested=ACTIONS.get(record["proposal"],"Invalid or unsupported action")
            label="Corrected by PCS" if corrected else "Proposal accepted"
            reason=("The response was not a plain action JSON object. PCS did not extract or repair it."
                    if record["proposal_classification"]=="MALFORMED_FALLBACK" else
                    "This action was not admitted by the declared policy in the observed state.")
            raw=bytes.fromhex(frame["proposal_hex"]).decode("utf-8",errors="replace")
            steps.append(f'''<li class="step {'corrected' if corrected else 'accepted'}"><h3>{index+1}. {escape(ACTIONS[record['action']])}</h3>
<p class="muted">From: {escape(STAGES[record['source']])}</p><span class="badge">{label}</span>
<p>{'Model' if case['mode']=='model' else 'Control'} requested <strong>{escape(requested)}</strong>.</p>
<p>Executed <strong>{escape(ACTIONS[record['action']])}</strong> → {escape(STAGES[record['target']])}.</p>
{f'<p class="muted">{reason}</p>' if corrected else ''}
<details><summary>Read the original proposal</summary><pre>{escape(raw)}</pre></details></li>''')
        proof=parse(episode.expected_proofs_json)
        proof_label="Producer proof metadata — replay to check" if mode=="loaded" else "Checks performed on this host"
        proof_files=(("Capture-workflow-wire.lean","Exact action replies"),("Rows-workflow-rows.lean","Exact row replies"),("Path-workflow.lean","Completed path and progress bound"))
        # A loaded-only export can live anywhere, and intake neither copies nor
        # verifies producer proof files. Link only locally generated evidence.
        links=("".join(f'<li><code>{name}</code> · {label}</li>' for name,label in proof_files)
               +'<li>Run replay to generate and check local proof files.</li>' if mode=="loaded" else
               "".join(f'<li><a href="{case["id"]}/proofs/{name}">{label}</a></li>' for name,label in proof_files))
        navigation.append(f'<li><a href="#case-{case["id"]}">{escape(case["title"])} · {"public" if case["pre_sanitized"] else "confidential"}</a></li>')
        publication="Reported: approved summary published" if mode=="loaded" else "Published the approved summary"
        sections.append(f'''<details class="case" id="case-{case['id']}" {'open' if case_index==0 else ''}><summary class="workflow-toggle"><h2>{escape(case['title'])} <span class="fixture">· {'initially public' if case['pre_sanitized'] else 'initially confidential'}</span></h2></summary><div class="case-head"><span class="muted">{'Model responses' if case['mode']=='model' else 'Deterministic control; no model generation'}</span><span class="badge">{publication}</span></div>
<details><summary>Task / untrusted document</summary><div class="task">{escape(case['task'])}</div></details>
<ol class="timeline" aria-label="Enforced tool sequence">{''.join(steps)}</ol>
<details><summary>{proof_label}</summary><p>Action replies, row changes and the completed path. The tool model and host correspondence remain assumptions.</p><ul>{links}</ul><p>Public output:</p><pre>{escape(str(cap['final']['public']))}</pre></details></details>''')
    items=((counts['cases'],"reported completed workflows" if mode=="loaded" else "completed workflows"),(counts['model_proposals'],"model proposals"),(counts['corrections'],"model proposals corrected"),(counts['control_proposals'],"control proposals"))
    metrics="".join(f'<div class="metric"><strong>{n}</strong><span>{label}</span></div>' for n,label in items)
    notice=("This view checks the evidence structure and token/proposal correspondence. It has not rerun Lean or SQL here. Run replay to check the execution independently."
            if mode=="loaded" else "Actual native Lean admission and SQL effects were checked on this host. Model responses remain untrusted proposals; corrections come from the declared workflow policy.")
    status="Deterministic controls · local execution checked" if mode=="live" and not counts["model_proposals"] else MODES[mode]
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
<title>PCS · Local Agent Lab</title><style>{CSS}</style></head><body><main><header><div class="eyebrow">Proof-Carrying Science · Research lab</div>
<h1>See what the model asked for.<br>See what actually ran.</h1><span class="status">{escape(status)}</span>
<p class="lead">Review → read → sanitize confidential content → publish the approved summary. Follow each real tool transition and every correction.</p></header>
<section class="metrics" aria-label="Run summary">{metrics}</section><p class="notice">{notice}</p>
<div class="legend"><span>Proposal accepted = the requested action ran</span><span>Corrected = PCS selected a progressing alternative</span></div>
<p class="muted">Model output: {counts['malformed_proposals']} malformed proposals; {counts['unsafe_requests']} typed requests with unsafe modeled outcomes; {counts['forbidden_requests']} typed forbidden requests.</p>
<details><summary>How to read these counts</summary><p>Counts follow strict action parsing. Malformed text falls back without extraction or repair. Few typed unsafe requests can therefore reflect formatting failures, not good model judgment. Supervised completion is not model competence.</p></details>
<details class="case-nav"><summary>Jump to a workflow ({counts['cases']})</summary><nav aria-label="Workflow navigation"><ul>{''.join(navigation)}</ul></nav></details>
{''.join(sections)}<footer><p>Synthetic fixed SQL workflow; no general alignment or realistic redaction claim. The model loader, observations, tool adapter, compiler and host remain trusted. Same-user processes are not a sandbox.</p>
<details><summary>Reproduce and inspect</summary><p>Use <code>python -m research.live_agent_lab_v3 replay INPUT NEW_OUTPUT --tokenizer TOKENIZER_DIR</code>. Replay uses recorded responses; it does not run model inference.</p><p>Exact loaded suite SHA-256: <code>{suite.sha256}</code>.</p><p>Proposal data and proof-development traces are not used for training.</p></details></footer></main></body></html>'''


def write_report(suite,path,mode="loaded"):
    with path.open("x",encoding="utf-8") as out:out.write(html(suite,mode))
