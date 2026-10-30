"""Fixed Lean token/byte/policy certificate BEFORE any receiving SQL effects.

This adds no production authority. Libraries/compiler/OS remain trusted.
"""
import json,os,re,shutil,subprocess
from pathlib import Path
from pcs.transport_kernel_v1 import _inventory
from research.progress_supervisor_v1.authority import TOOLS
from research.progress_supervisor_v1.binding import SourceBinding
from research.progress_supervisor_v1.certificate import encode,sha,propose
from research.progress_supervisor_v1.example import model
from research.live_agent_lab_v3.report import summary
from research.structured_action_lab_v4.codec import ActionOracle
from research.structured_action_lab_v4.intake import prepare,parse
from research.structured_action_lab_v4.report import write_report

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
THEOREMS=('pair_roundtrip','pair_sound','pair_unique','invalid_never_selected','selected_from_choose','selected_pair_bound','selected_not_forbidden','selected_all_outcomes','canonical_available','forbidden_corrected','unsafe_corrected','erases_to_checked_path','adaptive_run_bound','adaptive_completion_at_rank','mismatched_actions_rejected','no_nonempty_run_at_goal')
NAMES=['PCSTokenPolicyGate.'+n for n in THEOREMS]


def freeze(root,tokenizer):
    oracle=ActionOracle(tokenizer,mode='trie');frozen=prepare(root,oracle)
    if parse(frozen.raw_json)['profile']!='trie':raise ValueError('This new interface requires the explicit canonical profile')
    return frozen


def rows_from_suite(frozen):
    rows=[]
    for episode in frozen.episodes:
        if parse(episode.case_json)['mode']!='model':continue
        for frame in parse(episode.frames_json):
            record=frame['record']
            rows.append(dict(state=record['source'],tokens=frame['response']['generated']['generated_ids'],raw_hex=frame['proposal_hex'],selected=record['action']))
    if not rows:raise ValueError('A genuine captured model-pair inventory is required')
    return rows


def render_rows(rows):
    if type(rows) is not list or not 1<=len(rows)<=64:raise ValueError('Bounded pair inventory required')
    inputs=[];outputs=[]
    for row in rows:
        if type(row) is not dict or set(row)!={'state','tokens','raw_hex','selected'}:raise ValueError('Exact pair schema required')
        if type(row['state']) is not int or not 0<=row['state']<65536:raise ValueError('Exact bounded state required')
        tokens=row['tokens']
        if type(tokens) is not list or not 1<=len(tokens)<=32 or any(type(t) is not int or not 0<=t<151936 for t in tokens):raise ValueError('Bounded exact token IDs required')
        raw=row['raw_hex']
        if type(raw) is not str or len(raw)>8192 or re.fullmatch('(?:[0-9a-f]{2})*',raw) is None:raise ValueError('Exact bounded byte hex required')
        selected=row['selected']
        if selected is not None and (type(selected) is not int or not 0<=selected<65536):raise ValueError('Exact selected action or negative control required')
        nums=lambda xs:'['+','.join(map(str,xs))+']'
        inputs.append('('+str(row['state'])+',('+nums(tokens)+','+nums(bytes.fromhex(raw))+'))')
        outputs.append('.invalid' if selected is None else '.selected '+str(selected))
    return ('import Data\nimport PairGate\nset_option maxRecDepth 4096\nset_option maxHeartbeats 8000000\nnamespace GateCapture\n'
            'def samples : List (Nat × (List Nat × List Nat)) := ['+','.join(inputs)+']\n'
            'theorem actual : samples.map (fun f => PCSTokenPolicyGate.gate PCSProgressData.spec f.1 f.2.1 f.2.2) = ['+','.join(outputs)+'] := by decide\n'
            'end GateCapture\n#print axioms GateCapture.actual\n').encode()


def require_execution_rows(rows):
    """A true proof of rejection is never permission to execute a model pair."""
    render_rows(rows)  # Require the full bounded, exact data schema first.
    if any(row['selected'] is None for row in rows):
        raise ValueError('Every model pair must prove a selected action before effects')


class Checker:
    """Fixed reviewed source/tool compiler, no caller-supplied verifier or model."""
    def __init__(self,output):
        self.output=Path(output).resolve();self.output.mkdir(parents=True,exist_ok=False)
        lean=shutil.which('lean')
        if lean is None:raise ValueError('Exact Lean 4.28.0 required')
        self.tools={n:Path(lean).with_name(n) for n in TOOLS}
        self._tools()
        raw=encode(model());cert=encode(propose(raw,[4]));self.binding=SourceBinding.capture(raw,cert)
        all_sources=dict(self.binding.native)
        self.sources={n:all_sources[n] for n in ('PCSActionShield.lean','Progress.lean','Wire.lean','Codec.lean','Adapter.lean','RowWire.lean','Data.lean')}
        self.sources['ActionCodec.lean']=(ROOT/'research/structured_action_lab_v4/ActionCodec.lean').read_bytes()
        self.sources['PairGate.lean']=(HERE/'PairGate.lean').read_bytes()
        self.host=Path(__file__).read_bytes();self.logs=[]
        self.env=dict(os.environ,LEAN_PATH=str(self.output))
        for name,blob in self.sources.items():(self.output/name).write_bytes(blob)
        for name in self.sources:
            log=self.call([self.tools['lean'],'-j1','-M2048','-D','Elab.async=false','--root='+str(self.output),'-o',name[:-5]+'.olean',name])
            if name=='PairGate.lean':self.axioms=_inventory(log,NAMES)
        self.call([self.tools['leanchecker'],'--fresh','PairGate'])
        self.check()
        self.objects={p.name:sha(p.read_bytes()) for p in self.output.glob('*.olean*')}

    def _tools(self):
        if {n:sha(p.read_bytes()) for n,p in self.tools.items()}!=TOOLS:raise ValueError('Pinned proof/compiler tool bytes required')

    def call(self,command):
        r=subprocess.run(list(map(str,command)),cwd=self.output,env=self.env,capture_output=True,text=True,timeout=300 if Path(command[0])==self.tools['leanchecker'] else 180)
        self.logs.append(dict(command=list(map(str,command)),returncode=r.returncode,stdout=r.stdout,stderr=r.stderr))
        (self.output/'executions.json').write_text(json.dumps(self.logs,indent=2)+'\n')
        if r.returncode:raise ValueError('Actual Lean checker rejected; see executions.json')
        return r.stdout

    def check(self):
        self._tools()
        raw=encode(model());cert=encode(propose(raw,[4]))
        if SourceBinding.capture(raw,cert)!=self.binding or Path(__file__).read_bytes()!=self.host:raise ValueError('Fixed source identity changed')
        if (HERE/'PairGate.lean').read_bytes()!=self.sources['PairGate.lean'] or (ROOT/'research/structured_action_lab_v4/ActionCodec.lean').read_bytes()!=self.sources['ActionCodec.lean']:raise ValueError('Format/gate source changed')
        if any((self.output/n).read_bytes()!=b for n,b in self.sources.items()):raise ValueError('Staged source changed')
        if hasattr(self,'objects') and any(sha((self.output/n).read_bytes())!=v for n,v in self.objects.items()):raise ValueError('Checked import object changed')

    def certify(self,rows,label):
        if re.fullmatch('[a-z][a-z0-9_-]{0,30}',label) is None:raise ValueError('Safe unique certificate label required')
        proof=render_rows(rows);name='GateCapture_'+label.replace('-','_')
        path=self.output/(name+'.lean')
        with path.open('xb') as f:f.write(proof)
        self.check();log=self.call([self.tools['lean'],'-j1','-M2048','-D','Elab.async=false','--root='+str(self.output),'-o',name+'.olean',path])
        inventory=_inventory(log,['GateCapture.actual'])
        self.call([self.tools['leanchecker'],'--fresh',name]);self.check()
        self.objects.update({p.name:sha(p.read_bytes()) for p in self.output.glob(name+'.olean*')})
        if path.read_bytes()!=proof:raise ValueError('Capture proof source changed')
        report=dict(format='pcs-token-policy-pair-check-v1',kernel_checked=True,resource_limits=dict(elaboration_seconds=180,fresh_kernel_seconds=300,memory_mib=2048,pairs=64),pairs=len(rows),proof_sha256=sha(proof),general_axiom_closures=self.axioms,captured_axiom_closures=inventory,source_sha256={n:sha(b) for n,b in self.sources.items()},host_sha256=sha(self.host),pcs_authority=False,scope='Exact finite token/byte/policy equality before effects; host/Rust/tokenizer/neural computation/SQL correspondence are not proved')
        (self.output/(label+'-report.json')).write_text(json.dumps(report,indent=2)+'\n');return report


def receive(root,tokenizer,output):
    frozen=freeze(root,tokenizer)  # Entire submitted suite before outputs/effects.
    rows=rows_from_suite(frozen)
    require_execution_rows(rows)
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    checker=Checker(output/'pair-checker');report=checker.certify(rows,'model-pairs')
    # Only after actual kernel authorization of every model token/byte pair.
    from research.progress_supervisor_v1.__main__ import execute
    from research.real_model_safety_v1.audit import same
    received=output/'replayed';received.mkdir()
    for episode in frozen.episodes:
        case=parse(episode.case_json);target=received/case['id'];checker.check()
        execute(target,capture=parse(episode.capture_json))
        same((target/'capture.json').read_bytes(),episode.capture_json)
        expected=parse(episode.expected_proofs_json);actual=parse((target/'result.json').read_bytes());same({k:actual[k] for k in expected},expected)
    (received/'suite.json').write_bytes(frozen.raw_json)
    write_report(frozen,received/'report.html','replay');checker.check()
    result=dict(format='pcs-token-policy-receiving-v1',suite_sha256=frozen.sha256,pair_check=report,summary=summary(frozen),inference_performed=False,controls_pair_checked=False,control_scope='Deterministic controls are separately native-authorized, not neural-pair certificates',pcs_authority=False)
    (output/'receiving.json').write_text(json.dumps(result,indent=2)+'\n');return result
