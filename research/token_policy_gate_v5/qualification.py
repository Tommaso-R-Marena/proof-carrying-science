"""Require real native tests, complete accounting, and pre-effect receiving replay."""
import json
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET
from .receiver import HERE, ROOT, THEOREMS, receive


def qualify(output, tokenizer):
    output=Path(output).resolve()
    output.mkdir(parents=True,exist_ok=False)
    tokenizer=Path(tokenizer).resolve()
    report_path=output/'tests.xml'
    env=dict(os.environ,PCS_TOKENIZER_DIR=str(tokenizer))
    subprocess.run([sys.executable,'-m','pytest','-q',str(HERE),
                    '--junitxml='+str(report_path)],cwd=ROOT,env=env,check=True)
    cases=list(ET.parse(report_path).getroot().iter('testcase'))
    identities=[(c.get('classname'),c.get('name')) for c in cases]
    if len(cases)!=28 or len(set(identities))!=28 or any(
        c.find(tag) is not None for c in cases for tag in ('failure','error','skipped')
    ):
        raise ValueError('Require all 28 unique unit/native cases without skips')
    result=receive(ROOT/'research/structured_action_lab_v4/demo/trie',tokenizer,output/'receiving')
    pair=result['pair_check']
    if pair['pairs']!=42 or not pair['kernel_checked'] or len(pair['general_axiom_closures'])!=len(THEOREMS):
        raise ValueError('Require every pair and every general theorem closure')
    summary=dict(format='pcs-token-policy-qualification-v1',tests_passed=28,
                 skipped=0,model_pairs=42,new_general_theorems=len(THEOREMS),
                 receiving_suite_sha256=result['suite_sha256'],
                 inference_performed=False,pcs_authority=False,
                 receiving_report='receiving/receiving.json')
    (output/'qualification.json').write_text(json.dumps(summary,indent=2)+'\n')
    return summary


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output',type=Path)
    parser.add_argument('--tokenizer',type=Path,required=True)
    args=parser.parse_args()
    print(json.dumps(qualify(args.output,args.tokenizer)))
