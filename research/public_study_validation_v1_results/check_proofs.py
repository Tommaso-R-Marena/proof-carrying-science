"""Compile this analysis and its exact fixed authority dependencies from source."""
from pathlib import Path
import json
import os
import shutil
import subprocess
import sys

from research.progress_supervisor_v1.authority import TOOLS
from research.progress_supervisor_v1.binding import SourceBinding
from research.progress_supervisor_v1.certificate import encode, propose, sha
from research.progress_supervisor_v1.example import model
from pcs.transport_kernel_v1 import _inventory

HERE=Path(__file__).resolve().parent
THEOREMS=['PCSPublicStudy.'+n for n in (
    'choose_proposal_independent','adaptive_tool_trace_independent',
    'projected_tool_trace_independent','actual_spec_unique',
    'actual_adaptive_trace_independent','raw_reply_channel_countermodel')]


def check(out):
    out=Path(out).resolve();out.mkdir(parents=True,exist_ok=False)
    lean=shutil.which('lean')
    if lean is None:raise ValueError('actual pinned Lean required')
    tools={name:Path(lean).with_name(name) for name in TOOLS}
    if {name:sha(path.read_bytes()) for name,path in tools.items()}!=TOOLS:
        raise ValueError('reviewed proof tool bytes required')
    raw=encode(model());cert=encode(propose(raw,[4]));binding=SourceBinding.capture(raw,cert)
    frozen=dict(binding.native)
    frozen['OutputBoundary.lean']=(HERE/'proofs/OutputBoundary.lean').read_bytes()
    env=dict(PATH=str(Path(lean).parent)+':/usr/bin:/bin',LANG='C.UTF-8',LEAN_PATH=str(out))
    logs=[];axioms={}
    def run(command):
        result=subprocess.run(list(map(str,command)),cwd=out,env=env,capture_output=True,text=True,timeout=240)
        logs.append(dict(command=list(map(str,command)),returncode=result.returncode,stdout=result.stdout,stderr=result.stderr))
        (out/'executions.json').write_text(json.dumps(logs,indent=2)+'\n')
        if result.returncode:raise ValueError('actual proof check failed: '+(result.stdout+result.stderr)[-2000:])
        return result.stdout
    for filename in ('PCSActionShield.lean','Progress.lean','Wire.lean','Codec.lean',
                     'Adapter.lean','RowWire.lean','Data.lean','Main.lean','OutputBoundary.lean'):
        (out/filename).write_bytes(frozen[filename])
        log=run([tools['lean'],'-j1','-M2048','-D','maxRecDepth=4096','-D','Elab.async=false',
                 '--root='+str(out),'-o',filename[:-5]+'.olean',filename])
        if filename=='OutputBoundary.lean':axioms=_inventory(log,THEOREMS)
    run([tools['leanchecker'],'--fresh','OutputBoundary'])
    if any((out/name).read_bytes()!=value for name,value in frozen.items()):raise ValueError('staged source changed')
    if SourceBinding.capture(raw,cert)!=binding or (HERE/'proofs/OutputBoundary.lean').read_bytes()!=frozen['OutputBoundary.lean']:
        raise ValueError('reviewed source changed during proof check')
    result=dict(format='pcs-public-study-output-boundary-proof-check-v1',theorems=THEOREMS,
        axiom_closures=axioms,tools=TOOLS,source_sha256={n:sha(v) for n,v in frozen.items()},
        all_dependencies_recompiled=True,fresh_leanchecker=True,new_axioms=False,
        production_authority_changed=False,neural_computation_refinement_proved=False,
        general_ai_safety_proved=False,empirical_rates_are_theorems=False)
    (out/'proof-check.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__=='__main__':print(json.dumps(check(sys.argv[1]),indent=2))
