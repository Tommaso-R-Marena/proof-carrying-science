"""Tests of an offline two-ledger simulator; never claims real-provider safety."""
import concurrent.futures
import copy
import hashlib
import os
import random
import sqlite3
import tempfile
import threading
import unittest
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from research.delegated_action_gate_v1.gate import Denied, sign, digest, public_hex, canonical
from research.effect_finality_v2.protocol import EffectGate, SignedSink, CAP, PROVIDER, hash_body


class Harness(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.keys = {k: Ed25519PrivateKey.generate() for k in ('root','reviewer','agent','agent2','sink','gateway')}
        self.pub = {k:public_hex(v) for k,v in self.keys.items()}
        self.now=200
        self.gate=EffectGate(Path(self.tmp.name)/'gate.sqlite',root_public=self.pub['root'],
            reviewer_public=self.pub['reviewer'],sink_public=self.pub['sink'],
            dispatch_private=self.keys['gateway'],clock=lambda:self.now)
        self.sink=SignedSink(Path(self.tmp.name)/'sink.sqlite',sink_private=self.keys['sink'],
            gateway_public=self.pub['gateway'],root_public=self.pub['root'],clock=lambda:self.now)
        self.idx=0

    def _chain(self, epoch=0, *, agent='agent', caps=None, include_delegate=False):
        root=self.pub['root']
        p=self.pub[agent]
        return [sign(self.keys['root'],'grant',dict(id=f'grant{epoch}',issuer=root,
            subject=p,parent=None,caps=[CAP] if caps is None else caps,
            delegate=include_delegate,epoch=epoch,not_before=100,expires=10000))]

    def _proposal(self,*, rid=None,intent=None,epoch=None,agent='agent',chain=None,payload='ONE',snap=None):
        self.idx+=1
        rid=rid or f'request{self.idx}'
        state=self.gate.status()
        if epoch is None: epoch=state['epoch']
        chain=chain if chain is not None else self._chain(epoch,agent=agent)
        snap=snap if snap is not None else self.sink.snapshot()
        current=snap['body']
        action={'id':rid,'intent':intent or rid,'agent':self.pub[agent],'cap':CAP,'payload':payload,
                'epoch':epoch,'gate_version':state['version'],'sink_version':current['version'],
                'sink_preimage':current['preimage'],'provider':PROVIDER}
        request=sign(self.keys[agent],'effect-v2-action',action)
        review=sign(self.keys['reviewer'],'effect-v2-review',{
            'id':f'approval{self.idx}','action_sha256':digest(action),
            'chain_sha256':digest(chain),'epoch':epoch,'expires':self.now+100})
        return request,chain,review,snap

    def prepare(self,**kwargs):
        packet=self._proposal(**kwargs)
        rid=self.gate.reserve(*packet)
        return rid,self.gate.issue(rid)

    def rotate(self):
        state=self.gate.status()
        cmd=sign(self.keys['root'],'effect-v2-rotate',{
            'id':f'cut{state["epoch"]}', 'epoch':state['epoch'],
            'new_epoch':state['epoch']+1,'expected_gate_version':state['version']})
        self.gate.revoke(cmd)
        return cmd

    def test_authorized_commit(self):
        rid,permit=self.prepare()
        receipt=self.sink.deliver(permit)
        self.assertEqual('APPLIED',self.gate.finish(rid,receipt))
        self.assertEqual('ONE',self._body())
        self.assertEqual(3,self.gate.replay()['events_verified'])
        self.assertEqual('APPLIED',self.gate.reservation(rid)['status'])

    def _body(self):
        with sqlite3.connect(self.sink.path) as c:
            return c.execute('SELECT body FROM state').fetchone()[0]

    def test_crash_after_commit_retry_same_idempotency_key(self):
        rid,permit=self.prepare()
        with self.assertRaises(TimeoutError):
            self.sink.deliver(permit,simulate_response_loss=True)
        self.assertEqual('IN_FLIGHT',self.gate.reservation(rid)['status'])
        self.assertEqual('ONE',self._body())
        permit2=self.gate.issue(rid)
        self.assertEqual(permit,permit2)
        receipt=self.sink.deliver(permit2)
        self.assertEqual('ONE',self._body())
        self.assertEqual(1,self.sink.state()['version'])
        self.assertEqual('APPLIED',self.gate.finish(rid,receipt))

    def test_crash_before_call_remains_ambiguous(self):
        rid,permit=self.prepare()
        self.assertIsNone(self.sink.receipt_if_applied(rid))
        with self.assertRaises(Denied):
            self.sink.no_effect_after_fence(permit)
        self.assertEqual('IN_FLIGHT',self.gate.reservation(rid)['status'])
        self.assertEqual('ONE',self.sink.deliver(permit)['body']['postimage'] and self._body())

    def test_fence_cuts_old_permits(self):
        rid,permit=self.prepare()
        cmd=self.rotate()
        self.assertTrue(self.gate.status()['cut_pending'])
        # Deliberate counterexample: a locally revoked *unfenced* permit still reaches sink.
        # No post-revoke guarantee is claimed before signed provider fence.
        result=self.sink.deliver(permit)
        cert=self.sink.fence(cmd)
        self.gate.complete_fence(cert)
        self.assertEqual('APPLIED',self.gate.finish(rid,result))
        with self.assertRaises(Denied): self.gate.issue(rid)
        self.assertFalse(self.gate.status()['cut_pending'])

    def test_no_effect_requires_sink_fence(self):
        rid,permit=self.prepare()
        cmd=self.rotate()
        with self.assertRaises(Denied): self.sink.no_effect_after_fence(permit)
        with self.assertRaises(Denied): self.gate.issue(rid)
        cert=self.sink.fence(cmd)
        self.gate.complete_fence(cert)
        with self.assertRaises(Denied): self.sink.deliver(permit)
        no_effect=self.sink.no_effect_after_fence(permit)
        self.assertEqual('NO_EFFECT',self.gate.finish(rid,no_effect))
        self.assertEqual('',self._body())
        self.assertEqual('NO_EFFECT',self.gate.reservation(rid)['status'])

    def test_after_fence_new_epoch_authority_works(self):
        rid,p=self.prepare()
        cmd=self.rotate()
        self.gate.complete_fence(self.sink.fence(cmd))
        nr,np=self.prepare(epoch=1,rid='newEpoch')
        self.assertEqual('APPLIED',self.gate.finish(nr,self.sink.deliver(np)))
        with self.assertRaises(Denied): self.sink.deliver(p)
        self.assertEqual('ONE',self._body())

    def test_forged_gateway_permit_rejected_by_sink(self):
        rid,permit=self.prepare()
        p=copy.deepcopy(permit)
        p['body']['payload']='MALICIOUS'
        with self.assertRaises(Denied): self.sink.deliver(p)
        fake=sign(self.keys['agent'],'effect-v2-permit',permit['body'])
        with self.assertRaises(Denied): self.sink.deliver(fake)
        self.assertEqual('',self._body())

    def test_wrong_signed_provider_state(self):
        request,chain,review,snap=self._proposal()
        bad=sign(self.keys['agent'],'effect-v2-snapshot',snap['body'])
        with self.assertRaises(Denied): self.gate.reserve(request,chain,review,bad)
        self.assertEqual(0,self.gate.status()['version'])

    def test_snapshot_preimage_fails_at_commit_after_external_change(self):
        # Two properly approved reservations for the same provider version.
        rid1,p1=self.prepare(rid='first')
        rid2,p2=self.prepare(rid='second')
        self.sink.deliver(p1)
        with self.assertRaises(Denied): self.sink.deliver(p2)
        self.assertEqual('ONE',self._body())
        self.assertEqual('IN_FLIGHT',self.gate.reservation(rid2)['status'])

    def test_review_is_not_just_agent_approval(self):
        request,chain,review,snap=self._proposal()
        forged=sign(self.keys['agent'],'effect-v2-review',review['body'])
        with self.assertRaises(Denied): self.gate.reserve(request,chain,forged,snap)
        self.assertEqual(0,self.gate.status()['version'])

    def test_reviewer_replay_rejected(self):
        request,chain,review,snap=self._proposal()
        self.gate.reserve(request,chain,review,snap)
        r2=copy.deepcopy(request)
        r2['body']['id']='another'
        # Using same review cannot authorize different signed action.
        with self.assertRaises(Denied): self.gate.reserve(r2,chain,review,snap)

    def test_cross_agent_impersonation_rejected(self):
        req,chain,review,snap=self._proposal()
        forged=sign(self.keys['agent2'],'effect-v2-action',req['body'])
        with self.assertRaises(Denied): self.gate.reserve(forged,chain,review,snap)

    def test_stale_gate_version_rejected(self):
        p1=self._proposal(rid='stale')
        self.prepare(rid='fresh')
        with self.assertRaises(Denied): self.gate.reserve(*p1)

    def test_stale_signed_sink_state_rejected(self):
        snap=self.sink.snapshot()
        rid,permit=self.prepare()
        self.sink.deliver(permit)
        req,chain,review,_=self._proposal(rid='staleSink',snap=snap)
        # Reserve may accept a signed stale snapshot, but the sink MUST refuse to execute.
        self.gate.reserve(req,chain,review,snap)
        with self.assertRaises(Denied): self.sink.deliver(self.gate.issue('staleSink'))

    def test_receipt_substitution_and_forgery(self):
        rid,permit=self.prepare()
        receipt=self.sink.deliver(permit)
        fake=sign(self.keys['agent'],'effect-v2-receipt',receipt['body'])
        with self.assertRaises(Denied): self.gate.finish(rid,fake)
        altered=sign(self.keys['sink'],'effect-v2-receipt',{**receipt['body'],'rid':'different'})
        with self.assertRaises(Denied): self.gate.finish(rid,altered)
        self.assertEqual('APPLIED',self.gate.finish(rid,receipt))

    def test_no_effect_not_forgeable_by_user(self):
        rid,permit=self.prepare()
        cmd=self.rotate()
        self.gate.complete_fence(self.sink.fence(cmd))
        fake=sign(self.keys['agent'],'effect-v2-receipt',{
            'outcome':'NO_EFFECT','rid':rid,'permit_sha256':digest(permit),'epoch':1,
            'sink_version':0,'postimage':None})
        with self.assertRaises(Denied): self.gate.finish(rid,fake)
        self.assertEqual('NO_EFFECT',self.gate.finish(rid,self.sink.no_effect_after_fence(permit)))

    def test_unacknowledged_success_cannot_be_replaced_by_no_effect(self):
        rid,permit=self.prepare()
        self.sink.deliver(permit,simulate_response_loss=False)
        cmd=self.rotate()
        self.gate.complete_fence(self.sink.fence(cmd))
        with self.assertRaises(Denied): self.sink.no_effect_after_fence(permit)
        self.assertEqual('APPLIED',self.gate.finish(rid,self.sink.receipt_if_applied(rid)))

    def test_changed_permit_same_reservation_rejected(self):
        rid,permit=self.prepare()
        altered=sign(self.keys['gateway'],'effect-v2-permit',{**permit['body'],'payload':'MISMATCH'})
        self.sink.deliver(permit)
        with self.assertRaises(Denied): self.sink.deliver(altered)
        self.assertEqual('ONE',self._body())

    def test_double_issue_threads_only_one_audit_transition(self):
        rid,p=self.prepare()
        with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
            permits=list(pool.map(lambda _:self.gate.issue(rid),range(12)))
        self.assertTrue(all(x==p for x in permits))
        self.assertEqual(2,self.gate.replay()['events_verified'])

    def test_concurrent_provider_delivery_one_effect(self):
        rid,p=self.prepare()
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
            outcomes=list(pool.map(lambda _:self.sink.deliver(p),range(10)))
        self.assertTrue(all(x==outcomes[0] for x in outcomes))
        self.assertEqual(1,self.sink.state()['version'])
        self.assertEqual('ONE',self._body())

    def test_provider_conflicting_fence_rejected(self):
        self.prepare()
        cmd=self.rotate()
        cert=self.sink.fence(cmd)
        self.assertEqual(cert,self.sink.fence(cmd))
        with self.assertRaises(Denied):
            self.sink.fence(sign(self.keys['root'],'effect-v2-rotate',{
                **cmd['body'],'id':'differentCut'}))

    def test_pending_revoke_denies_new_issue_or_reserve(self):
        r,p=self.prepare()
        cmd=self.rotate()
        req,chain,review,snap=self._proposal(epoch=1)
        with self.assertRaises(Denied): self.gate.reserve(req,chain,review,snap)
        with self.assertRaises(Denied): self.gate.issue(r)
        self.gate.complete_fence(self.sink.fence(cmd))

    def test_bad_fence_receipt_rejected(self):
        self.prepare()
        cmd=self.rotate()
        cert=self.sink.fence(cmd)
        with self.assertRaises(Denied): self.gate.complete_fence(sign(self.keys['agent'],'effect-v2-fence',cert['body']))
        with self.assertRaises(Denied): self.gate.complete_fence(sign(self.keys['sink'],'effect-v2-fence',{**cert['body'],'new_epoch':42}))
        self.assertTrue(self.gate.status()['cut_pending'])
        self.gate.complete_fence(cert)

    def test_corrupted_gate_event_rejected(self):
        rid,p=self.prepare()
        with sqlite3.connect(self.gate.path) as c:
            c.execute("UPDATE events SET hash=? WHERE version=1",('f'*64,))
        with self.assertRaises(Denied):self.gate.replay()
        with self.assertRaises(Denied):self.gate.issue(rid)

    def test_corrupted_gate_index_rejected(self):
        rid,p=self.prepare()
        with sqlite3.connect(self.gate.path) as c:
            c.execute("UPDATE reservations SET status='APPLIED' WHERE rid=?",(rid,))
        with self.assertRaises(Denied):self.gate.replay()

    def test_external_checkpoint_detects_full_rollback(self):
        first_head=self.gate.status()['head']
        self.prepare()
        second=self.gate.status()['head']
        self.assertNotEqual(first_head,second)
        with self.assertRaises(Denied):self.gate.replay(first_head)
        self.assertEqual(second,self.gate.replay(second)['head'])

    def test_unsupported_capabilities_rejected(self):
        req,chain,review,snap=self._proposal()
        bad=sign(self.keys['agent'],'effect-v2-action',{**req['body'],'cap':'delete:private/notes'})
        with self.assertRaises(Denied):self.gate.reserve(bad,chain,review,snap)

    def test_signature_hex_case_malleability_regression(self):
        rid, permit = self.prepare()
        altered=copy.deepcopy(permit)
        old=altered['signature']
        altered['signature']=''.join(c.upper() if c in 'abcdef' else c for c in old)
        self.assertNotEqual(old,altered['signature'])
        with self.assertRaises(Denied):self.sink.deliver(altered)
        receipt=self.sink.deliver(permit)
        self.assertEqual('APPLIED',self.gate.finish(rid,receipt))

    def test_unresolved_intent_blocks_replacement_even_with_new_review(self):
        rid,permit=self.prepare(rid='first',intent='jobA')
        # Exact same task intent, fresh request+independently signed reviewer token.
        new=self._proposal(rid='second',intent='jobA')
        with self.assertRaises(Denied):self.gate.reserve(*new)
        self.assertEqual('IN_FLIGHT',self.gate.reservation(rid)['status'])
        self.assertEqual(1,self.gate.status()['reservations'])

    def test_completed_intent_cannot_be_replayed(self):
        rid,permit=self.prepare(rid='first',intent='jobA')
        self.gate.finish(rid,self.sink.deliver(permit))
        with self.assertRaises(Denied): self.gate.reserve(*self._proposal(rid='second',intent='jobA'))

    def test_successor_after_certified_no_effect(self):
        rid,permit=self.prepare(rid='first',intent='jobA')
        cmd=self.rotate()
        self.gate.complete_fence(self.sink.fence(cmd))
        self.gate.finish(rid,self.sink.no_effect_after_fence(permit))
        nr,np=self.prepare(rid='second',intent='jobA',epoch=1)
        self.assertEqual('APPLIED',self.gate.finish(nr,self.sink.deliver(np)))
        self.assertEqual('ONE',self._body())
        self.assertEqual(2,self.gate.status()['reservations'])
        self.assertGreaterEqual(self.gate.replay()['events_verified'],7)

    def test_abandon_only_never_dispatched_after_fence(self):
        p=self._proposal(rid='first',intent='jobA')
        self.gate.reserve(*p)
        cmd=self.rotate()
        with self.assertRaises(Denied): self.gate.abandon_after_fence('first')
        self.gate.complete_fence(self.sink.fence(cmd))
        self.assertEqual('ABANDONED',self.gate.abandon_after_fence('first'))
        nr,np=self.prepare(rid='second',intent='jobA',epoch=1)
        self.gate.finish(nr,self.sink.deliver(np))
        self.assertEqual('ONE',self._body())

    def test_dispatched_cannot_be_abandoned_after_fence(self):
        rid,p=self.prepare()
        cmd=self.rotate()
        self.gate.complete_fence(self.sink.fence(cmd))
        with self.assertRaises(Denied):self.gate.abandon_after_fence(rid)
        self.assertEqual('NO_EFFECT',self.gate.finish(rid,self.sink.no_effect_after_fence(p)))

    def test_clock_rollback_fails_closed_even_with_valid_signatures(self):
        self.prepare()
        before=self.gate.status()['head']
        self.now=199
        with self.assertRaises(Denied):self.gate.reserve(*self._proposal(rid='clockRoll'))
        self.assertEqual(before,self.gate.status()['head'])
        self.assertEqual(1,self.gate.status()['reservations'])

    def test_reopen_sink_with_different_gateway_denied(self):
        bad=Ed25519PrivateKey.generate()
        with self.assertRaises(Denied):SignedSink(self.sink.path,sink_private=self.keys['sink'],
            gateway_public=public_hex(bad),root_public=self.pub['root'])

    def test_reopen_gate_with_different_reviewer_denied(self):
        bad=Ed25519PrivateKey.generate()
        with self.assertRaises(Denied):EffectGate(self.gate.path,root_public=self.pub['root'],
            reviewer_public=public_hex(bad),sink_public=self.pub['sink'],
            dispatch_private=self.keys['gateway'],clock=lambda:self.now)

    def test_parent_to_child_delegation_with_external_effect(self):
        epoch=0
        parent=self._chain(epoch,include_delegate=True)[0]
        child=sign(self.keys['agent'],'grant',{
            'id':'child1','issuer':self.pub['agent'],'subject':self.pub['agent2'],
            'parent':parent['body']['id'],'caps':[CAP],'delegate':False,
            'epoch':epoch,'not_before':100,'expires':500})
        rid,permit=self.prepare(rid='childAction',intent='delegatedJob',agent='agent2',chain=[parent,child])
        self.assertEqual('APPLIED',self.gate.finish(rid,self.sink.deliver(permit)))
        self.assertEqual('ONE',self._body())

    def test_cross_agent_same_intent_requires_finality(self):
        self.prepare(rid='parentAction',intent='oneJob')
        child=self._chain(epoch=0,agent='agent2')
        candidate=self._proposal(rid='childAction',intent='oneJob',agent='agent2',chain=child)
        with self.assertRaises(Denied):self.gate.reserve(*candidate)

    def test_rehashed_event_semantic_forgery_rejected(self):
        rid,permit=self.prepare()
        from research.delegated_action_gate_v1.gate import loads
        with sqlite3.connect(self.gate.path) as c:
            records=c.execute('SELECT version,record,hash FROM events ORDER BY version').fetchall()
            head='0'*64
            for version,raw,_ in records:
                obj=loads(raw.encode('ascii'))
                obj['prior']=head
                if version==1:
                    obj['detail']['action']['body']['payload']='FORGED'
                head=digest(obj)
                c.execute('UPDATE events SET record=?,hash=? WHERE version=?',(
                    canonical(obj).decode('ascii'),head,version))
            c.execute('UPDATE meta SET head=? WHERE one=1',(head,))
        with self.assertRaises(Denied):self.gate.replay()

    def test_expired_reviewer_approval_cannot_issue(self):
        p=self._proposal(rid='expires')
        self.gate.reserve(*p)
        self.now=301
        with self.assertRaises(Denied):self.gate.issue('expires')
        self.assertEqual('RESERVED',self.gate.reservation('expires')['status'])

    def test_issued_permit_expires_at_provider(self):
        rid,p=self.prepare(rid='expires')
        self.now=301
        with self.assertRaises(Denied):self.sink.deliver(p)
        self.assertEqual('',self._body())
        with self.assertRaises(Denied):self.gate.issue(rid)
        cmd=self.rotate()
        self.gate.complete_fence(self.sink.fence(cmd))
        self.assertEqual('NO_EFFECT',self.gate.finish(rid,self.sink.no_effect_after_fence(p)))

    def test_expired_permit_can_reconcile_prior_success_without_retry(self):
        rid,p=self.prepare()
        receipt=self.sink.deliver(p)
        self.now=301
        with self.assertRaises(Denied):self.gate.issue(rid)
        self.assertEqual('APPLIED',self.gate.finish(rid,self.sink.receipt_if_applied(rid)))
        self.assertEqual('ONE',self._body())

    def test_provider_clock_rollback_denies_new_effect(self):
        rid,p=self.prepare()
        self.sink.deliver(p)
        newer=self._proposal(rid='different')
        self.gate.reserve(*newer)
        permit=self.gate.issue('different')
        self.now=199
        with self.assertRaises(Denied):self.sink.deliver(permit)
        self.assertEqual('ONE',self._body())

    def audited(self,head=None):
        from research.effect_finality_v2.independent_audit import audit
        return audit(self.gate.path,self.sink.path,root_public=self.pub['root'],
            reviewer_public=self.pub['reviewer'],gateway_public=self.pub['gateway'],
            sink_public=self.pub['sink'],expected_gate_head=head)

    def test_independent_cross_ledger_audit_reconciles_lost_ack(self):
        rid,p=self.prepare()
        self.assertEqual(0,self.audited()['provider_effects_verified'])
        with self.assertRaises(TimeoutError):self.sink.deliver(p,simulate_response_loss=True)
        mid=self.audited()
        self.assertEqual(1,mid['provider_effects_verified'])
        self.assertEqual(1,mid['unresolved_requests'])
        self.gate.finish(rid,self.sink.receipt_if_applied(rid))
        self.assertEqual(0,self.audited(self.gate.status()['head'])['unresolved_requests'])

    def test_independent_cross_ledger_replays_fenced_absence(self):
        rid,p=self.prepare()
        cmd=self.rotate()
        self.audited()
        self.gate.complete_fence(self.sink.fence(cmd))
        self.gate.finish(rid,self.sink.no_effect_after_fence(p))
        checked=self.audited()
        self.assertEqual(1,checked['provider_fences_verified'])
        self.assertEqual(0,checked['provider_effects_verified'])

    def test_independent_cross_ledger_verifies_successor(self):
        rid,p=self.prepare(rid='a',intent='sameGoal')
        cmd=self.rotate()
        self.gate.complete_fence(self.sink.fence(cmd))
        self.gate.finish(rid,self.sink.no_effect_after_fence(p))
        new,permit=self.prepare(rid='b',intent='sameGoal',epoch=1)
        self.gate.finish(new,self.sink.deliver(permit))
        self.assertEqual(1,self.audited()['provider_effects_verified'])
        self.assertEqual('ONE',self._body())

    def test_independent_cross_ledger_detects_provider_forgery(self):
        from research.effect_finality_v2.independent_audit import AuditFailure
        rid,p=self.prepare()
        self.sink.deliver(p)
        with sqlite3.connect(self.sink.path) as c:
            c.execute("UPDATE state SET body='FORGED' WHERE one=1")
        with self.assertRaises(AuditFailure):self.audited()

    def test_independent_cross_ledger_detects_gateway_index_forgery(self):
        from research.effect_finality_v2.independent_audit import AuditFailure
        rid,p=self.prepare()
        with sqlite3.connect(self.gate.path) as c:
            c.execute("UPDATE reservations SET intent='imposter' WHERE rid=?",(rid,))
        with self.assertRaises(AuditFailure):self.audited()

    def test_independent_cross_ledger_detects_wrong_pinned_root(self):
        from research.effect_finality_v2.independent_audit import AuditFailure, audit
        self.prepare()
        with self.assertRaises(AuditFailure):audit(self.gate.path,self.sink.path,
           root_public=public_hex(Ed25519PrivateKey.generate()),
           reviewer_public=self.pub['reviewer'],gateway_public=self.pub['gateway'],sink_public=self.pub['sink'])

    def test_randomized_permit_mutation_fails_closed(self):
        rid,permit=self.prepare()
        original=canonical(permit)
        rng=random.Random(2077)
        for _ in range(400):
            pos=rng.randrange(len(original))
            mutated=bytearray(original)
            mutated[pos]^=1 << rng.randrange(8)
            try:
                altered=__import__('research.delegated_action_gate_v1.gate',fromlist=['loads']).loads(bytes(mutated))
            except Denied:
                continue
            if altered == permit:
                continue  # harmless wire-only mutation normalizes to the same signed object
            with self.assertRaises(Denied):
                self.sink.deliver(altered)
        self.assertEqual('',self._body())

    def test_roundtrip_replay_after_restart(self):
        rid,p=self.prepare()
        rec=self.sink.deliver(p)
        self.gate.finish(rid,rec)
        restored=EffectGate(self.gate.path,root_public=self.pub['root'],reviewer_public=self.pub['reviewer'],
                sink_public=self.pub['sink'],dispatch_private=self.keys['gateway'],clock=lambda:self.now)
        self.assertEqual(3,restored.replay()['events_verified'])
        self.assertEqual('APPLIED',restored.reservation(rid)['status'])


if __name__ == '__main__':
    unittest.main()
