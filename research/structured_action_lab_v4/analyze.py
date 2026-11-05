"""Paired descriptive accounting; no causal generalization or learning claim."""
import argparse,json
from pathlib import Path
from research.live_agent_lab_v3.report import summary
from research.real_model_safety_v1.audit import same
from .codec import ActionOracle
from .intake import prepare,parse


def compare(root,tokenizer,output):
    frozen={mode:prepare(root/mode,ActionOracle(tokenizer,mode=mode)) for mode in ('raw','trie')}
    a,b=(parse(frozen[m].raw_json) for m in ('raw','trie'))
    for key in ('plan','execution_sources','authority_sources'):same(a[key],b[key])
    for key in ('files','versions','device','dtype','threads'):same(a['ready'][key],b['ready'][key])
    matched=0;cases=[];timings={}
    for mode,suite in frozen.items():
        frames=[f for e in suite.episodes if parse(e.case_json)['mode']=='model' for f in parse(e.frames_json)]
        timings[mode]=dict(model_generation_seconds=sum(f['response']['generated']['seconds'] for f in frames),generated_tokens=sum(len(f['response']['generated']['generated_ids']) for f in frames))
    for ca,cb,case in zip(a['episodes'],b['episodes'],a['plan']['cases']):
        same(ca['id'],cb['id']);same(len(ca['frames']),len(cb['frames']))
        if case['mode']=='model':
            for fa,fb in zip(ca['frames'],cb['frames']):same(fa['request']['messages'],fb['request']['messages']);matched+=1
        cases.append(dict(id=ca['id'],mode=case['mode'],turns=len(ca['frames'])))
    result=dict(format='pcs-structured-action-comparison-v1',profiles={m:summary(s) for m,s in frozen.items()},timings=timings,matched_model_prompts=matched,cases=cases,suite_sha256={m:s.sha256 for m,s in frozen.items()},same_weights_and_task_plan=True,training_performed=False,pcs_authority=False,
                scope='One fixed-order raw/trie execution on authored synthetic tasks. Format adherence is imposed by decoding, not learned model alignment. Timings are descriptive on this host; no randomized causal or general utility estimate.')
    with output.open('x',encoding='utf-8') as out:out.write(json.dumps(result,indent=2)+'\n')
    return result


def main():
    p=argparse.ArgumentParser();p.add_argument('input',type=Path);p.add_argument('tokenizer',type=Path);p.add_argument('output',type=Path);a=p.parse_args();print(json.dumps(compare(a.input,a.tokenizer,a.output)))


if __name__=='__main__':main()
