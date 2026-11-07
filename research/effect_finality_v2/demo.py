"""Offline demonstration with ephemeral keys and two disposable SQLite files."""
import json
import tempfile
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from research.delegated_action_gate_v1.gate import Denied, sign, public_hex, digest
from research.effect_finality_v2.protocol import EffectGate, SignedSink, CAP, PROVIDER


def run_demo():
    keys={k:Ed25519PrivateKey.generate() for k in ('root','reviewer','agent','sink','gateway')}
    pubs={k:public_hex(v) for k,v in keys.items()}
    now=200
    with tempfile.TemporaryDirectory(prefix='pcs-v2-offline-') as tmp:
        gate=EffectGate(Path(tmp)/'gate.db',root_public=pubs['root'],reviewer_public=pubs['reviewer'],
                        sink_public=pubs['sink'],dispatch_private=keys['gateway'],clock=lambda:now)
        sink=SignedSink(Path(tmp)/'sink.db',sink_private=keys['sink'],gateway_public=pubs['gateway'],
                        root_public=pubs['root'],clock=lambda:now)
        def make(rid,intent):
            v=gate.status()
            snapshot=sink.snapshot()
            chain=[sign(keys['root'],'grant',{
                'id':'g'+str(v['epoch']),'issuer':pubs['root'],'subject':pubs['agent'],
                'parent':None,'caps':[CAP],'delegate':False,'epoch':v['epoch'],
                'not_before':100,'expires':1000})]
            action={'id':rid,'intent':intent,'agent':pubs['agent'],'cap':CAP,'payload':'HELLO',
                    'epoch':v['epoch'],'gate_version':v['version'],'provider':PROVIDER,
                    'sink_version':snapshot['body']['version'],'sink_preimage':snapshot['body']['preimage']}
            request=sign(keys['agent'],'effect-v2-action',action)
            review=sign(keys['reviewer'],'effect-v2-review',{
                'id':'review'+rid,'action_sha256':digest(action),'chain_sha256':digest(chain),
                'expires':300,'epoch':v['epoch']})
            return request,chain,review,snapshot
        gate.reserve(*make('attemptA','oneTask'))
        permit=gate.issue('attemptA')
        results=[]
        try:
            sink.deliver(permit,simulate_response_loss=True)
        except TimeoutError:
            results.append('provider committed but response lost: gateway remains IN_FLIGHT')
        try:
            gate.reserve(*make('attemptB','oneTask'))
        except Denied:
            results.append('fresh signed reviewer approval with new ID blocked: intent unresolved')
        receipt=sink.deliver(permit)
        results.append('same permit retried: provider version is '+str(sink.state()['version']))
        results.append('signed receipt resolves original: '+gate.finish('attemptA',receipt))
        cut=sign(keys['root'],'effect-v2-rotate',{
            'id':'revoke0','epoch':0,'new_epoch':1,'expected_gate_version':gate.status()['version']})
        gate.revoke(cut)
        results.append('local revocation: cut_pending='+str(gate.status()['cut_pending']))
        gate.complete_fence(sink.fence(cut))
        results.append('signed sink fence received: cut_pending='+str(gate.status()['cut_pending']))
        try:
            gate.reserve(*make('attemptC','oneTask'))
        except Denied:
            results.append('applied task cannot be automatically repeated under new epoch')
        return {'cases':results,'replayed_gateway_history':gate.replay()['events_verified'],
                'provider_effects':sink.state()['version'],'actual_external_tools_used':0}


if __name__=='__main__':
    print(json.dumps(run_demo(),indent=2))
