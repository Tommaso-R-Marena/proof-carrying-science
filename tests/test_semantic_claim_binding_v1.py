from __future__ import annotations
import pytest
from pcs.canonical_json import canonicalize_jcs_bytes
from pcs.semantic_kernel_bridge_v1 import digest,canonical_bytes
from pcs.semantic_claim_binding_v1 import verify_binding,FORMAT

def fixture():
    selected={"params":[],"assumptions":[],"conclusion":{"op":"true"}}
    request={"schema":"pcs-semantic-translation-v1","interpretation":{"source_text":"Explicit claim","selected":selected}}
    ir={"format":"pcs-claim-ir-v1","claims":[{"claim_id":"c1","statement":"Explicit claim"}],
        "relations":[],"roots":[],"summary":{"claims":1}}
    ir["claim_ir_sha256"]=digest(canonicalize_jcs_bytes(ir))
    authority_sha="a"*64
    request_sha=digest(canonical_bytes(request))
    binding={"format":FORMAT,"claim_ir_sha256":ir["claim_ir_sha256"],"claim_id":"c1",
             "request_sha256":request_sha,"source_statement":"Explicit claim",
             "selected_semantic_claim_sha256":digest(canonical_bytes(selected)),
             "registry_sha256":authority_sha}
    args=dict(authority_sha256=authority_sha,request_sha256=request_sha,
              binding=binding,approved_binding_sha256=digest(canonical_bytes(binding)))
    return ir,request,args

def test_exact_binding_passes_without_claiming_proof():
    ir,req,args=fixture()
    decision=verify_binding(ir,req,**args)
    assert decision["claim_id"]=="c1"
    assert "pcs_scientific_authority" not in decision

@pytest.mark.parametrize("change",[
 lambda i,r,a: i["claims"][0].__setitem__("statement","Altered"),
 lambda i,r,a: r["interpretation"].__setitem__("source_text","Altered"),
 lambda i,r,a: r["interpretation"]["selected"]["conclusion"].__setitem__("op","false"),
 lambda i,r,a: a.__setitem__("authority_sha256","b"*64),
 lambda i,r,a: a["binding"].__setitem__("claim_id","wrong"),
 lambda i,r,a: i["claims"].append(dict(i["claims"][0])),
 lambda i,r,a: a.__setitem__("approved_binding_sha256","0"*64),
])
def test_changed_context_rejected(change):
    ir,req,args=fixture();change(ir,req,args)
    with pytest.raises(ValueError):
        verify_binding(ir,req,**args)
