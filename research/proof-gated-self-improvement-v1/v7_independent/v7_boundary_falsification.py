#!/usr/bin/env python3
"""Independent V7 boundary experiments (research-only, NOT the Lean authority).

Reconstructs V7 proposal/receipt semantics from released V7 definitions and
compares them to published byte-for-byte receipts. Produces an illustrative
request/governance event log whose hash chaining demonstrates the difference
between semantic validation and request/event provenance. Does not claim
cryptographic authenticity or protected monotonic anchoring.
"""
from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import pathlib
import random
import sys
from dataclasses import dataclass
from typing import Any, Optional

import v7_independent_audit as ref


@dataclass(frozen=True)
class Request:
    requested_policy: bytes
    requested_generation: int
    requested_active: bytes
    certificate: bytes


@dataclass(frozen=True)
class State:
    policy: bytes
    generation: int
    active: bytes


def safe_propose(s: State, r: Request) -> tuple[State, bytes]:
    """Match V7 ProofGatedBoundary.propose, including receipt's omission of r metadata."""
    p=ref.parse_policy(s.policy)
    candidate, _reason=ref.check_cert_semantics(p,s.generation,s.active,r.certificate)
    approved=candidate is not None
    rc=ref.Receipt(version=7, old_gen=s.generation,expected_gen=s.generation,
        accepted=approved,new_gen=s.generation+int(approved),policy=s.policy,
        old=s.active,candidate=candidate if approved else b'',
        certificate=r.certificate,new=candidate if approved else s.active)
    new=State(s.policy,s.generation+int(approved),candidate if approved else s.active)
    return new,ref.receipt_wire(rc)


def strict_propose(s: State, r: Request) -> Optional[tuple[State,bytes]]:
    if (r.requested_policy,r.requested_generation,r.requested_active)!=(s.policy,s.generation,s.active):
        return None
    return safe_propose(s,r)


def trusted_govern(s: State, new_policy: bytes) -> State:
    """V7 `govern`: a trusted policy update, modeled independently for reference."""
    p=ref.parse_policy(new_policy)
    supported=p.version==7 and p.predicate==1 and p.checker in (6,7)
    if supported:
        try: ref.model(s.active,p.width,p.bound)
        except ref.BadWire: supported=False
    return State(new_policy,s.generation,s.active) if supported else s


def obj(o:Any)->Any:
    if isinstance(o,bytes):return {"hex":o.hex(),"byte_len":len(o)}
    if dataclasses.is_dataclass(o):return {k:obj(v) for k,v in dataclasses.asdict(o).items()}
    if isinstance(o,(list,tuple)):return [obj(v) for v in o]
    if isinstance(o,dict):return {k:obj(v) for k,v in o.items()}
    return o


def canonical_json(record:dict)->bytes:
    return json.dumps(record,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode('ascii')


def digest(x:bytes)->str:return hashlib.sha256(x).hexdigest()


def event_payload_request(s:State,r:Request,ns:State,wire:bytes)->dict:
    return {"kind":"proposal","authority_before":obj(s),"request":obj(r),
        "authority_after":obj(ns),"receipt_sha256":digest(wire)}


def event_payload_govern(s:State,p:bytes,ns:State)->dict:
    return {"kind":"govern","authority_before":obj(s),"requested_policy":obj(p),
        "authority_after":obj(ns)}


def make_event_chain(events:list[dict])->tuple[list[dict],str]:
    h='0'*64;out=[]
    for ix,payload in enumerate(events):
        e={"sequence":ix,"previous_sha256":h,"payload":payload}
        h=digest(canonical_json(e))
        out.append({**e,"entry_sha256":h})
    return out,h


def check_event_chain(events:list[dict],anchor:str)->bool:
    last='0'*64
    for i,e in enumerate(events):
        if set(e)!={'sequence','previous_sha256','payload','entry_sha256'}:return False
        if e['sequence']!=i or e['previous_sha256']!=last:return False
        candidate=digest(canonical_json({k:e[k] for k in ('sequence','previous_sha256','payload')}))
        if candidate!=e['entry_sha256']:return False
        last=candidate
    return last==anchor



def undo_bytes(x: dict)->bytes:
    raw=bytes.fromhex(x['hex'])
    if set(x)!={'hex','byte_len'} or len(raw)!=x['byte_len']:
        raise ValueError('invalid serialized byte commitment')
    return raw


def undo_state(x: dict)->State:
    if set(x)!={'policy','generation','active'}:raise ValueError('state field mismatch')
    if type(x['generation']) is not int or x['generation']<0:raise ValueError('invalid generation')
    return State(undo_bytes(x['policy']),x['generation'],undo_bytes(x['active']))


def undo_request(x: dict)->Request:
    if set(x)!={'requested_policy','requested_generation','requested_active','certificate'}:
        raise ValueError('request field mismatch')
    if type(x['requested_generation']) is not int or x['requested_generation']<0:
        raise ValueError('invalid requested generation')
    return Request(undo_bytes(x['requested_policy']),x['requested_generation'],
                   undo_bytes(x['requested_active']),undo_bytes(x['certificate']))


def semantic_event_replay(genesis:State,entries:list[dict],anchor:str,
                          approved_governance_sha256:set[str])->Optional[State]:
    """Reference replay conditional on externally approved governance and fixed anchor.

    This does not authenticate the anchor or approval set and is not a Lean checker.
    A deployer needs independent durable protection and signer verification.
    """
    if not check_event_chain(entries,anchor):return None
    s=genesis
    try:
        for event in entries:
            payload=event['payload']
            if undo_state(payload['authority_before'])!=s:return None
            if payload['kind']=='govern':
                p=undo_bytes(payload['requested_policy'])
                if digest(p) not in approved_governance_sha256:return None
                nxt=trusted_govern(s,p)
            elif payload['kind']=='proposal':
                r=undo_request(payload['request'])
                nxt,rc=safe_propose(s,r)
                if digest(rc)!=payload['receipt_sha256']:return None
            else:return None
            if undo_state(payload['authority_after'])!=nxt:return None
            s=nxt
    except (KeyError,TypeError,ValueError,ref.BadWire):
        return None
    return s


def run(root:pathlib.Path,seed:int=824):
    rng=random.Random(seed)
    policies=root/'policies';rcs=root/'receipts';
    pinned=(policies/'pinned0.pgpol7').read_bytes()
    alt=(policies/'mal_target.pgpol7').read_bytes()
    alt_interval=(policies/'mal_interval.pgpol7').read_bytes()
    old=State(pinned,0,b'PGSI2-WIDE|0')
    counts={'original_receipt_byte_matches':0,'accepted_equivocations':0,
            'rejected_equivocations':0,'governance_silent_pairs':0,'governance_replay_controls':0,'anchored_event_mutations_rejected':0,
            'extra_event_evidence_distinguishes':0,'tamper_cases_caught_with_anchor':0,'cross_policy_regression_controls':0}
    observations=[]
    # Actual recorded V7 receipts: on each, reconstruct V7 safePropose from released bytes.
    state=old
    for ix in range(7):
        rcbytes=(rcs/f'adv_{ix}.pgsr7').read_bytes()
        rc=ref.parse_receipt(rcbytes)
        assert (state.generation,state.active)==(rc.old_gen,rc.old)
        canonical=Request(state.policy,state.generation,state.active,rc.certificate)
        nxt,recreated=safe_propose(state,canonical)
        assert recreated==rcbytes,f'published receipt mismatch at {ix}'
        counts['original_receipt_byte_matches']+=1
        # Construct 30 distinct bogus metadata tuples; *same certificate*, same state.
        for j in range(30):
            bogus=Request(alt if j%2==0 else b'ATTACK|POLICY',
                state.generation+1+j,rng.randbytes(6),rc.certificate)
            assert bogus!=canonical
            result,wire=safe_propose(state,bogus)
            assert result==nxt and wire==rcbytes
            assert strict_propose(state,bogus) is None
            key='accepted_equivocations' if rc.accepted else 'rejected_equivocations'
            counts[key]+=1
            # A separate event payload records the attempted fields; V7 receipt does not.
            hp=digest(canonical_json(event_payload_request(state,canonical,nxt,rcbytes)))
            ha=digest(canonical_json(event_payload_request(state,bogus,nxt,wire)))
            assert hp!=ha
            counts['extra_event_evidence_distinguishes']+=1
        state=nxt
    assert state.generation==3
    # A *trusted* governance operation changes target or robustness interval without
    # changing model/generation or emitting a request receipt at all.
    for changed in (alt,alt_interval):
        ns=trusted_govern(old,changed)
        assert ns!=old and ns.active==old.active and ns.generation==old.generation
        # Definitionally, runEvents [govern p] returns [] receipts (and [] does as well).
        receipt_log_unchanged=[]
        assert receipt_log_unchanged==[]
        counts['governance_silent_pairs']+=1
        observations.append({'policy_change':digest(changed),
            'initial_policy':digest(pinned),'model_sha256':digest(old.active),
            'generation':old.generation,'receipt_count':0})
    # An exact, nonvacuous cross-policy regression. V7 already kernel-proves
    # `malTarget_admissible` and `pinned_rejects_regression` for gen3 -> gen0.
    # Independently reconstruct a PGSC6 candidate with maximal-error witness.
    perfect=(rcs/'adv_6.pgsr7').read_bytes()
    perfect_bytes=ref.parse_receipt(perfect).new
    base_zero=old.active
    weak_policy=ref.parse_policy(alt)
    from_net=ref.model(perfect_bytes)
    to_net=ref.model(base_zero)
    gain=next(x for x in weak_policy.corpus if
        ref.pred(from_net,x)!=ref.pred(weak_policy.target,x) and
        ref.pred(to_net,x)==ref.pred(weak_policy.target,x))
    old_loss=sum(abs(ref.pred(from_net,x)-ref.pred(weak_policy.target,x)) for x in weak_policy.corpus)
    new_loss=sum(abs(ref.pred(to_net,x)-ref.pred(weak_policy.target,x)) for x in weak_policy.corpus)
    max_level,max_where=ref.max_error(from_net,weak_policy.target,weak_policy.lo,weak_policy.hi)
    override_cert=ref.Cert(6,1,weak_policy.width,weak_policy.bound,0,weak_policy.lo,weak_policy.hi,
        gain,old_loss,new_loss,max_where,max_level,weak_policy.corpus,weak_policy.target,
        perfect_bytes,base_zero)
    cert_wire=ref.cert_wire(override_cert)
    override_state=State(alt,0,perfect_bytes)
    override_req=Request(alt,0,perfect_bytes,cert_wire)
    reverted,revert_receipt=safe_propose(override_state,override_req)
    assert reverted.active==base_zero and reverted.generation==1
    baseline=ref.parse_policy(pinned)
    cand_unchanged,_=ref.check_cert_semantics(baseline,0,perfect_bytes,cert_wire)
    assert cand_unchanged is None
    # The old pinned target was the perfect gen3 network, so its loss changes
    # from zero to strictly positive after a *trusted* target-policy switch.
    old_obj_before=sum(abs(ref.pred(from_net,x)-ref.pred(baseline.target,x)) for x in baseline.corpus)
    old_obj_after=sum(abs(ref.pred(to_net,x)-ref.pred(baseline.target,x)) for x in baseline.corpus)
    assert old_obj_before==0 and old_obj_after>0
    counts['cross_policy_regression_controls']+=1
    observations.append({'cross_policy_regression': True,
        'original_policy_loss_before':old_obj_before,
        'original_policy_loss_after':old_obj_after,
        'new_policy_loss_before':old_loss,
        'new_policy_loss_after':new_loss,
        'admitted_under_new_policy':True,
        'rejected_under_original_policy':True,
        'raw_certificate_sha256':digest(cert_wire)})
    pathlib.Path(__file__).with_name('governance_cross_policy_regression.pgsc6').write_bytes(cert_wire)
    # Evidence format is an *illustrative* event journal, outside of V7 authority.
    accepted=ref.parse_receipt((rcs/'adv_2.pgsr7').read_bytes())
    s=State(pinned,accepted.old_gen,accepted.old)
    cr=Request(s.policy,s.generation,s.active,accepted.certificate)
    nr=Request(alt,832, b'MALICIOUS-SUBSTITUTED-INCUMBENT',accepted.certificate)
    ns,b=safe_propose(s,cr)
    assert b==(rcs/'adv_2.pgsr7').read_bytes()
    clean_event=event_payload_request(s,cr,ns,b)
    attacker_event=event_payload_request(s,nr,ns,b)
    # Same successful V7 receipt, distinct external event records.
    assert clean_event['receipt_sha256']==attacker_event['receipt_sha256']
    assert digest(canonical_json(clean_event))!=digest(canonical_json(attacker_event))
    gs=trusted_govern(old,alt)
    entries,anchor=make_event_chain([event_payload_govern(old,alt,gs),
                                     event_payload_request(s,nr,ns,b)])
    assert check_event_chain(entries,anchor)
    assert semantic_event_replay(old,entries,anchor,{digest(alt)}) is None
    # The second payload starts from a different authority state intentionally;
    # the authenticated event-log hash alone does not make this a valid trace.
    counts['governance_replay_controls']+=1
    # A coherent genuine trace: governed state then a request rejected under the
    # new policy. This must replay with a fixed, separately authorized governance id.
    fail_req=Request(gs.policy,gs.generation,gs.active,b'NOT_A_CERTIFICATE')
    gs2,rejection=safe_propose(gs,fail_req)
    good_entries,good_anchor=make_event_chain([
        event_payload_govern(old,alt,gs),
        event_payload_request(gs,fail_req,gs2,rejection)])
    assert semantic_event_replay(old,good_entries,good_anchor,{digest(alt)})==gs2
    counts['governance_replay_controls']+=1
    assert semantic_event_replay(old,good_entries,good_anchor,set()) is None
    counts['governance_replay_controls']+=1
    # Even if an attacker re-hashes the whole chain, the original trusted anchor
    # catches the rewrite. If the attacker can supply a new anchor, it does not.
    other_entries,other_anchor=make_event_chain([
        event_payload_govern(old,alt,gs),
        event_payload_request(gs,fail_req,gs2,rejection)])
    assert other_entries==good_entries and other_anchor==good_anchor
    forged_entries,forged_anchor=make_event_chain([
        event_payload_govern(old,alt_interval,trusted_govern(old,alt_interval))])
    assert semantic_event_replay(old,forged_entries,good_anchor,{digest(alt_interval)}) is None
    assert semantic_event_replay(old,forged_entries,forged_anchor,{digest(alt_interval)}) is not None
    counts['governance_replay_controls']+=1
    # In-scope adversarial log mutation, truncation, reordering, redaction, and
    # re-hashing cannot match *the independently fixed* final anchor.
    mutations=[]
    mutations.append(entries[:-1])
    mutations.append(entries[1:])
    mutations.append(list(reversed(entries)))
    for eidx in (0,1):
        tampered=json.loads(json.dumps(entries))
        tampered[eidx]['payload']['kind']='CORRUPTED'
        mutations.append(tampered)
    for mutant in mutations:
        assert not check_event_chain(mutant,anchor)
        counts['tamper_cases_caught_with_anchor']+=1
    # Large deterministic tamper campaign, fixed original trusted anchor. Re-hash
    # each mutated history from genesis to distinguish tamper evidence from weak
    # per-record checksum checks. No cryptographic authenticity is claimed.
    for k in range(2000):
        mutated=json.loads(json.dumps(entries))
        j=rng.randrange(len(mutated))
        event=mutated[j]
        request_part=event['payload']
        key='kind' if (k&1) else 'receipt_sha256'
        request_part[key]=f'MUTATED_{k}'
        assert not check_event_chain(mutated,anchor)
        counts['anchored_event_mutations_rejected']+=1

    report={"status":"PASS","counts":counts,"published_final_generation":state.generation,
        "published_final_model_sha256":digest(state.active),"governance_experiments":observations,
        "same_receipt_different_request":{"receipt_sha256":digest(b),
            "genuine_event_sha256":digest(canonical_json(clean_event)),
            "malicious_event_sha256":digest(canonical_json(attacker_event))},
        "example_external_event_anchor_sha256":anchor,
        "scope":["Independent Python model derived from V7 source; no direct Lean process invoked",
                 "No V7 soundness counterexample: safe verifier intentionally ignores request metadata",
                 "Trusted governance is allowed by V7 and excluded from runAdv receipt replay",
                 "Hash-only event journal not authenticated without protected anchor/signer"]}
    return report


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--fixtures',type=pathlib.Path,default=pathlib.Path(__file__).with_name('fixtures_v7'))
    ap.add_argument('--out',type=pathlib.Path)
    a=ap.parse_args();r=run(a.fixtures)
    data=json.dumps(r,indent=2,sort_keys=True)+'\n'
    if a.out:a.out.write_text(data)
    print(data)

if __name__=='__main__':main()
