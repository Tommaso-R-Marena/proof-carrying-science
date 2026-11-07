"""Separate read-only cross-ledger checker for the synthetic v2 protocol.

Intentionally does NOT import the effect gateway, the v1 gate, or their codec.
It checks concrete signed records and two SQLite stores against a separately
implemented state machine. It does NOT prove the provider's actual IO semantics.
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from collections import defaultdict
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

PREFIX=b"PCS-DELEGATED-ACTION-v1\x00"
SIG=re.compile(r"[0-9a-f]{128}\Z")
CAP="append:private/notes"
ALL_CAPS={"append:public/report","append:private/notes","delete:private/notes"}
PROVIDER="local-private-note-v2"
ZERO="0"*64


class AuditFailure(ValueError):pass


def must(condition,reason):
    if not condition:raise AuditFailure(reason)


def _pairs(items):
    d={}
    for k,v in items:
        must(k not in d,"duplicate JSON key")
        d[k]=v
    return d


def _no_float(_):raise AuditFailure("fractional/NaN JSON")


def encode(obj):
    return json.dumps(obj,sort_keys=True,ensure_ascii=True,separators=(',',':'),allow_nan=False).encode('ascii')


def decode(b):
    must(type(b) is bytes and len(b)<1000000,'invalid serialized record')
    try:return json.loads(b.decode('utf8'),object_pairs_hook=_pairs,parse_float=_no_float,parse_constant=_no_float)
    except (UnicodeError,ValueError,TypeError) as ex:raise AuditFailure('invalid audit JSON') from ex


def sha(obj):return hashlib.sha256(encode(obj)).hexdigest()


def signed(pub,kind,pkt):
    must(type(pkt) is dict and set(pkt)=={'body','signature'},'invalid packet structure')
    s=pkt['signature']
    must(type(s) is str and SIG.fullmatch(s) is not None,'noncanonical signature')
    must(type(pub) is str and len(pub)==64,'untrusted key')
    try:
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(pub)).verify(
            bytes.fromhex(s),PREFIX+kind.encode('ascii')+b'\x00'+encode(pkt['body']))
    except (ValueError,TypeError,InvalidSignature) as ex:raise AuditFailure('signature mismatch') from ex
    return pkt['body']


def fields(body,keys):must(type(body) is dict and set(body)==set(keys),'unexpected record fields')


def grant_chain(chain,root,epoch,now):
    must(type(chain) is list and 1<=len(chain)<=6,'delegation depth')
    parent=None
    ids=set()
    for pkt in chain:
        b=signed(root if parent is None else parent['subject'],'grant',pkt)
        fields(b,{'id','issuer','subject','parent','caps','delegate','epoch','not_before','expires'})
        must(type(b['id']) is str and b['id'] not in ids,'duplicate grant')
        ids.add(b['id'])
        must(b['epoch']==epoch and type(b['not_before']) is int and type(b['expires']) is int
             and b['not_before']<=now<b['expires'],'expired grant')
        must(type(b['caps']) is list and CAP in b['caps'] and len(set(b['caps']))==len(b['caps'])
             and set(b['caps'])<=ALL_CAPS,'missing or unsupported cap')
        must(b['issuer']==(root if parent is None else parent['subject'])
             and b['parent']==(None if parent is None else parent['id']),'lineage mismatch')
        if parent:
            must(parent['delegate'] is True and set(b['caps'])<=set(parent['caps'])
                 and b['not_before']>=parent['not_before'] and b['expires']<=parent['expires'],
                 'delegation amplified')
        parent=b
    return parent['subject']


def readonly(dbfile):
    return sqlite3.connect(f'file:{dbfile}?mode=ro',uri=True)


def audit(gate_path,sink_path,*,root_public,reviewer_public,gateway_public,sink_public,expected_gate_head=None):
    """Reconstruct two ledgers from pinned public keys, not gate replay code."""
    gate=readonly(gate_path)
    sink=readonly(sink_path)
    try:
        cfg={'root':root_public,'reviewer':reviewer_public,'gateway':gateway_public,
             'sink':sink_public,'provider':PROVIDER}
        must(gate.execute('SELECT config FROM trust WHERE one=1').fetchone()==(encode(cfg).decode('ascii'),),
             'gate root not pinned')
        expected_sink_cfg={k:cfg[k] for k in ('root','gateway','sink','provider')}
        must(sink.execute('SELECT config FROM trust WHERE one=1').fetchone()==(encode(expected_sink_cfg).decode('ascii'),),
             'sink root not pinned')
        rows=gate.execute('SELECT version,record,hash FROM events ORDER BY version').fetchall()
        meta=gate.execute('SELECT version,epoch,pending,rotation,head FROM meta WHERE one=1').fetchone()
        must(len(rows)<=4096 and len(rows)==meta[0],'gate length mismatch')
        state={}
        used=set()
        intent_last={}
        head=ZERO
        epoch=0
        pending=False
        rotation=None
        recent_time=-1
        for i,(v,raw,h) in enumerate(rows,1):
            must(type(raw) is str and len(raw)<1000000,'bad event source')
            r=decode(raw.encode('ascii'))
            fields(r,{'version','prior','kind','detail','observed_at'})
            must(type(r['observed_at']) is int and r['observed_at']>=recent_time,'nonmonotonic observation')
            recent_time=r['observed_at']
            must(v==i and r['version']==i and r['prior']==head and sha(r)==h,'event hash/link mismatch')
            d=r['detail']
            if r['kind']=='RESERVE':
                must(not pending,'reserve during cut')
                fields(d,{'rid','action','chain','review','review_id','observed_at','sink_snapshot'})
                a=d['action']['body']
                fields(a,{'id','intent','agent','cap','payload','epoch','gate_version','sink_version','sink_preimage','provider'})
                must(d['rid']==a['id'] and a['epoch']==epoch and a['gate_version']==i-1
                     and a['cap']==CAP and a['provider']==PROVIDER and type(a['payload']) is str
                     and a['payload'] and len(a['payload'])<=512
                     and all(32<=ord(c)<=126 for c in a['payload']),'action scope/version mismatch')
                must(d['observed_at']==r['observed_at'],'changed admission time')
                must(grant_chain(d['chain'],root_public,epoch,recent_time)==a['agent'],'agent not delegated')
                signed(a['agent'],'effect-v2-action',d['action'])
                review=signed(reviewer_public,'effect-v2-review',d['review'])
                fields(review,{'id','action_sha256','chain_sha256','expires','epoch'})
                must(review['id']==d['review_id'] and review['id'] not in used
                     and type(review['expires']) is int and recent_time<review['expires']
                     and review['epoch']==epoch and review['action_sha256']==sha(a)
                     and review['chain_sha256']==sha(d['chain']),'review replay/binding failure')
                used.add(review['id'])
                snap=signed(sink_public,'effect-v2-snapshot',d['sink_snapshot'])
                fields(snap,{'provider','version','epoch','preimage'})
                must(snap=={'provider':PROVIDER,'version':a['sink_version'],
                            'epoch':epoch,'preimage':a['sink_preimage']},'provider snapshot binding')
                must(a['id'] not in state,'reused reservation id')
                previous=intent_last.get(a['intent'])
                must(previous is None or state[previous]['status'] in ('NO_EFFECT','ABANDONED'),
                     'unresolved second reservation')
                state[a['id']]={'action':d['action'],'chain':d['chain'],'review':d['review'],
                    'review_id':review['id'],'intent':a['intent'],'epoch':epoch,
                    'status':'RESERVED','permit':None,'outcome':None}
                intent_last[a['intent']]=a['id']
            elif r['kind']=='ISSUE':
                fields(d,{'rid','permit'})
                must(d['rid'] in state,'issued unknown reservation')
                t=state[d['rid']]
                must(not pending and t['status']=='RESERVED' and t['epoch']==epoch,'invalid issuance state')
                a=t['action']['body']
                expires=min([t['review']['body']['expires']]+[g['body']['expires'] for g in t['chain']])
                must(r['observed_at']<expires,'expired gateway-issued permit')
                p=signed(gateway_public,'effect-v2-permit',d['permit'])
                fields(p,{'rid','action_sha256','chain_sha256','review_sha256','epoch',
                          'sink_version','sink_preimage','payload','provider','expires'})
                want={'rid':d['rid'],'action_sha256':sha(a),'chain_sha256':sha(t['chain']),
                      'review_sha256':sha(t['review']),'epoch':epoch,'sink_version':a['sink_version'],
                      'sink_preimage':a['sink_preimage'],'payload':a['payload'],
                      'provider':PROVIDER,'expires':expires}
                must(p==want,'dispatch permit mismatch')
                t['permit']=d['permit'];t['status']='IN_FLIGHT'
            elif r['kind']=='RESULT':
                fields(d,{'rid','receipt'})
                must(d['rid'] in state,'result without proposal')
                t=state[d['rid']]
                must(t['status']=='IN_FLIGHT','duplicate/early result')
                cert=signed(sink_public,'effect-v2-receipt',d['receipt'])
                fields(cert,{'outcome','rid','permit_sha256','epoch','sink_version','postimage'})
                must(cert['rid']==d['rid'] and cert['permit_sha256']==sha(t['permit']),
                     'unbound provider receipt')
                must(cert['outcome'] in ('APPLIED','NO_EFFECT'),'unsupported outcome')
                if cert['outcome']=='APPLIED':
                    must(cert['epoch']==t['epoch'] and type(cert['postimage']) is str
                         and len(cert['postimage'])==64,'bad applied receipt')
                else:
                    must(type(cert['epoch']) is int and t['epoch']<cert['epoch']<=epoch
                         and cert['postimage'] is None,'premature absence')
                t['status']=cert['outcome'];t['outcome']=d['receipt']
            elif r['kind']=='ABANDON':
                fields(d,{'rid'})
                must(d['rid'] in state and state[d['rid']]['status']=='RESERVED'
                     and state[d['rid']]['epoch']<epoch and not pending,'unsafe abandonment')
                state[d['rid']]['status']='ABANDONED'
            elif r['kind']=='ROTATE':
                fields(d,{'command'})
                must(not pending,'overlapping epoch cuts')
                b=signed(root_public,'effect-v2-rotate',d['command'])
                fields(b,{'id','epoch','new_epoch','expected_gate_version'})
                must(b['epoch']==epoch and b['new_epoch']==epoch+1 and b['expected_gate_version']==i-1,
                     'bad root epoch transition')
                rotation=d['command']; epoch+=1;pending=True
            elif r['kind']=='FENCE':
                fields(d,{'certificate'})
                b=signed(sink_public,'effect-v2-fence',d['certificate'])
                fields(b,{'new_epoch','rotation_sha256','sink_version','postimage'})
                must(pending and b['new_epoch']==epoch and b['rotation_sha256']==sha(rotation),
                     'non-matching provider fence')
                pending=False
            else:
                raise AuditFailure('unknown event kind')
            head=h
        must(meta==(len(rows),epoch,int(pending),
                    None if rotation is None else encode(rotation).decode('ascii'),head),'gateway metadata mismatch')
        if expected_gate_head is not None:must(head==expected_gate_head,'externally anchored head mismatch')
        index=gate.execute('SELECT rid,intent,action,chain,review,review_id,epoch,status,permit,outcome FROM reservations').fetchall()
        must(len(index)==len(state),'gateway index row count')
        for rid,intent,act,chain,rev,rev_id,e,status,permit,outcome in index:
            must(rid in state,'extra row')
            t=state[rid]
            want=(t['intent'],encode(t['action']).decode('ascii'),encode(t['chain']).decode('ascii'),
                  encode(t['review']).decode('ascii'),t['review_id'],t['epoch'],t['status'],
                  None if t['permit'] is None else encode(t['permit']).decode('ascii'),
                  None if t['outcome'] is None else encode(t['outcome']).decode('ascii'))
            must((intent,act,chain,rev,rev_id,e,status,permit,outcome)==want,'gateway index mismatch')
        # Provider-side reconciliation: every actual applied effect must correspond
        # to exactly one signed, previously issued permit in the gateway history.
        sink_version,sink_epoch,sink_body,_last=sink.execute('SELECT version,epoch,body,last_seen FROM state WHERE one=1').fetchone()
        effect_rows=sink.execute('SELECT rid,permit_hash,receipt FROM effects').fetchall()
        must(sink_version==len(effect_rows),'provider effect count inconsistent')
        by_version={}
        for rid,ph,raw_receipt in effect_rows:
            must(rid in state,'provider applied unapproved reservation')
            t=state[rid]
            must(t['permit'] is not None,'provider applied undispatched request')
            must(ph==sha(t['permit']),'provider used different permit')
            rec=decode(raw_receipt.encode('ascii'))
            body=signed(sink_public,'effect-v2-receipt',rec)
            must(body['outcome']=='APPLIED' and body['rid']==rid and body['permit_sha256']==ph
                 and body['epoch']==t['epoch'],'provider receipt mismatch')
            must(t['status']!='NO_EFFECT','provider committed supposedly absent effect')
            v=body['sink_version']
            must(type(v) is int and v not in by_version,'provider version reused')
            by_version[v]=(t['permit']['body']['payload'],body['postimage'])
            if t['status']=='APPLIED':must(t['outcome']==rec,'gateway receipt mismatch')
        body=''
        for version in range(1,sink_version+1):
            must(version in by_version,'missing committed effect')
            payload,postimage=by_version[version]
            body+=payload
            must(hashlib.sha256(body.encode('ascii')).hexdigest()==postimage,'provider postimage mismatch')
        must(body==sink_body,'provider final resource mismatch')
        for rid,t in state.items():
            if t['status']=='APPLIED':must(rid in {r[0] for r in effect_rows},'gateway falsely says applied')
            if t['status']=='NO_EFFECT':
                must(rid not in {r[0] for r in effect_rows} and t['outcome']['body']['epoch']<=sink_epoch,
                     'no-effect certificate contradicted by provider')
        fences=sink.execute('SELECT epoch,rotation_hash,certificate FROM fences ORDER BY epoch').fetchall()
        must(len(fences)==sink_epoch,'missing sink fence')
        rotations={}
        for _v,raw,_h in rows:
            r=decode(raw.encode('ascii'))
            if r['kind']=='ROTATE':
                rotations[r['detail']['command']['body']['new_epoch']]=r['detail']['command']
        for i,(e,h,certraw) in enumerate(fences,1):
            cert=signed(sink_public,'effect-v2-fence',decode(certraw.encode('ascii')))
            must(e==i and e in rotations and sha(rotations[e])==h
                 and cert['new_epoch']==e and cert['rotation_sha256']==h,'sink fence without root command')
        must(sink_epoch<=epoch and (pending or sink_epoch==epoch),'gate/sink epoch mismatch')
        return {'gateway_events_verified':len(rows),'provider_effects_verified':sink_version,
                'provider_fences_verified':len(fences),'epoch':epoch,
                'cut_pending':pending,'gateway_head':head,
                'unresolved_requests':sum(t['status']=='IN_FLIGHT' for t in state.values())}
    finally:
        gate.close();sink.close()
