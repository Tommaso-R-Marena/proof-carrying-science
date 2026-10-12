import base64,gzip,json
import pytest
from pcs.experimental.prover.memory_wire import intern,expand,MAX_EXPANDED_BYTES
from pcs.experimental.prover.induction_ir import digest
from pcs.experimental.prover.public_transport import serialize_result

def test_lossless_catalog_interning_and_bound_before_allocation():
    catalog=[{'name':'PCSKnownL0','expression':{'kind':'constant','value':'Nat','children':[]}}]
    original={'states':[{'available_lemmas':catalog,'proof':'immutable'}]*1000}
    packet=intern(original)
    assert len(packet['catalogs'])==1
    assert expand(packet)==original
    key=next(iter(packet['catalogs']))
    packet['catalogs'][key][0]['name']='forged'
    with pytest.raises(ValueError,match='digest'):expand(packet)
    huge=['x'*100000]
    bomb={'format':'pcs-interned-public-lean-v1','expanded_limit_bytes':MAX_EXPANDED_BYTES,
          'catalogs':{digest(huge):huge},'payload':[{'pcs_catalog_ref':digest(huge)}]*1000}
    with pytest.raises(ValueError,match='expanded'):expand(bomb)

def test_transport_exhaustion_retains_original_request_binding():
    bound={'format':'pcs-public-lean-result-v1','request_id':'a'*32,'source_sha256':'b'*64,
           'core_sha':'c'*40,'model_family':'verified-memory-v1','result':{'pcs_authority':False}}
    packed=intern({**bound,'extra':'x'*1000001})
    line=serialize_result(packed,binding=bound)
    result=json.loads(gzip.decompress(base64.b64decode(line.split(':',1)[1])))
    assert result['request_id']==bound['request_id']
    assert result['model_family']=='verified-memory-v1'
    assert result['result']['status']=='resource_exhaustion'

def test_anti_unification_fresh_names_terminate_with_occupied_hole_names():
    from pcs.experimental.prover.memory_discovery import anti_unify
    left={'format':'pcs-math-ir-v1','binders':[{'name':'w0','type':'Nat'},{'name':'w2','type':'Nat'}],
          'body':{'op':'eq','left':{'op':'var','name':'w0'},'right':{'op':'var','name':'w2'}}}
    right={**left,'body':{'op':'eq','left':{'op':'number','value':0,'type':'Nat'},'right':{'op':'var','name':'w2'}}}
    unified=anti_unify(left,right)
    assert unified['body']['left']=={'op':'var','name':'w1'}
