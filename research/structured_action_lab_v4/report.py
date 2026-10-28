"""Explicit format profile above the existing passive execution report."""
from research.live_agent_lab_v3.report import html,summary
from .intake import parse
from research.live_agent_lab_v3.report import CSS


def write_report(suite,path,mode):
    profile=parse(suite.raw_json)['profile']
    page=html(suite,mode)
    note=('Format profile: raw greedy generation; no token constraint.' if profile=='raw' else
          'Format profile: seven-action token trie. All actions, including bypass and dead end, remain representable. This constrains syntax, not policy or model reasoning.')
    page=page.replace('<section class="metrics"',f'<p class="notice">{note}</p><section class="metrics"',1)
    with path.open('x',encoding='utf-8') as out:out.write(page)
    return summary(suite)


def write_index(counts,path,*,replayed=False):
    if set(counts)!={'raw','trie'}:raise ValueError('Both completed profiles required')
    cards=[]
    for mode,title in (('raw','Unconstrained output'),('trie','Canonical action output')):
        c=counts[mode]
        if any(type(c.get(k)) is not int or c[k]<0 for k in ('model_proposals','malformed_proposals','corrections')):raise ValueError('Exact nonnegative counters required')
        cards.append(f'<section class="case"><h2>{title}</h2><p>{c["model_proposals"]} model proposals · {c["malformed_proposals"]} malformed · {c["corrections"]} corrected by PCS</p><a href="{mode}/report.html">Explore this checked workflow →</a></section>')
    status='Recorded responses independently replayed; no new inference' if replayed else 'Live paired experiment · local execution checked'
    page=f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'"><title>PCS · Action Format Experiment</title><style>{CSS}</style></head><body><main><div class="eyebrow">Proof-Carrying Science · Research</div><h1>Correct format.<br>Still an untrusted proposal.</h1><p class="status">{status}</p><p class="lead">The same model, tasks and tool policy, with two output interfaces. Open either report to follow actual tool actions and corrections.</p><p class="notice">Prompt → model output (raw or token-constrained) → Lean action gate → SQL effect. The format constraint can express all seven actions, including bypass and dead end. It cannot authorize them.</p>{''.join(cards)}<footer><p>Canonical output is imposed by the decoding algorithm, not learned alignment. One fixed-order comparison on synthetic tools does not establish general model utility or AI safety. Host and implementation correspondence remain assumptions. No training or production deployment.</p></footer></main></body></html>'''
    with path.open('x',encoding='utf-8') as out:out.write(page)
