"""Ordinary kernel audit of policy maximality and exact finite majority bounds."""
from pathlib import Path
import json
from pcs.transport_kernel_v1 import _inventory
from research.llm_firewall_v1.monitor import digest
from ..authority import Authority
HERE=Path(__file__).resolve().parent
NAMES=('safe_iff_all_worlds','unsafe_has_disclosing_world','maximal_truthful_uniform_gate','finite_class_closure','every_class_bounded','initial_in_classes','closed_step','closed_history','no_transcript_majority_above_two_thirds','two_thirds_is_attained','adaptive_closed','adaptive_majority_bound')
def prove(a):
    if type(a) is not Authority:raise ValueError('Fixed checked authority required')
    a.check();source=(HERE/'Bounds.lean').read_bytes();names=['PCSDisclosureBounds.'+n for n in NAMES]
    raw=source+('\n'+'\n'.join('#print axioms '+n for n in names)+'\n').encode()
    p=a.out/'Bounds.lean'
    if p.exists():raise ValueError('Fresh proof module required')
    p.write_bytes(raw)
    log=a._run([a.tools['lean'],'-j1','-M2048','-D','Elab.async=false','--root='+str(a.out),'-o','Bounds.olean','Bounds.lean'],60)
    if p.read_bytes()!=raw or source!=(HERE/'Bounds.lean').read_bytes():raise ValueError('Bounds source changed')
    inventory=_inventory(log,names)
    a._run([a.tools['leanchecker'],'--fresh','Bounds'],180);a.check()
    d=dict(kernel_checked=True,fresh_object_checked=True,source_sha256=digest(source),object_sha256=digest((a.out/'Bounds.olean').read_bytes()),axiom_closures=inventory,tools=a.tool_hashes,uniform_prior_interpretation_is_assumption=True,host_correspondence_proved=False)
    (a.out/'bounds-audit.json').write_text(json.dumps(d,indent=2)+'\n')
    return d
