"""Exact Claim IR to certified-request content binding, not proof of natural-language intent."""
from __future__ import annotations
from typing import Any, Mapping
from .canonical_json import canonicalize_jcs_bytes
from .semantic_kernel_bridge_v1 import canonical_bytes,digest

FORMAT="pcs-semantic-claim-ir-binding-v1"
FIELDS={"format","claim_ir_sha256","claim_id","request_sha256","source_statement","selected_semantic_claim_sha256","registry_sha256"}

def verify_binding(claim_ir:Mapping[str,Any],request:Mapping[str,Any],*,
                   authority_sha256:str,request_sha256:str,
                   binding:Mapping[str,Any],approved_binding_sha256:str)->dict[str,str]:
    if type(binding) is not dict or set(binding)!=FIELDS or binding.get("format")!=FORMAT:
        raise ValueError("CLAIM_BINDING_SCHEMA")
    if type(claim_ir) is not dict or claim_ir.get("format")!="pcs-claim-ir-v1":
        raise ValueError("CLAIM_IR_SCHEMA")
    core={k:v for k,v in claim_ir.items() if k!="claim_ir_sha256"}
    original=digest(canonicalize_jcs_bytes(core))
    if claim_ir.get("claim_ir_sha256")!=original:
        raise ValueError("CLAIM_IR_COMMITMENT_CHANGED")
    if type(approved_binding_sha256) is not str or len(approved_binding_sha256)!=64:
        raise ValueError("CLAIM_BINDING_APPROVAL_REQUIRED")
    if digest(canonical_bytes(binding))!=approved_binding_sha256:
        raise ValueError("CLAIM_BINDING_PIN_MISMATCH")
    claims=claim_ir.get("claims")
    if type(claims) is not list:
        raise ValueError("CLAIM_BINDING_CLAIMS_INVALID")
    matching=[x for x in claims if type(x) is dict and x.get("claim_id")==binding.get("claim_id")]
    if len(matching)!=1:
        raise ValueError("CLAIM_BINDING_DUPLICATE_OR_MISSING")
    interpretation=request.get("interpretation") if type(request) is dict else None
    if type(interpretation) is not dict or type(interpretation.get("selected")) is not dict:
        raise ValueError("CLAIM_BINDING_SELECTED_INTERPRETATION_MISSING")
    statement=interpretation.get("source_text")
    if type(statement) is not str or not statement.strip():
        raise ValueError("CLAIM_BINDING_STATEMENT_MISSING")
    if (matching[0].get("statement")!=statement or binding.get("source_statement")!=statement
        or binding.get("claim_ir_sha256")!=original
        or binding.get("registry_sha256")!=authority_sha256
        or binding.get("request_sha256")!=request_sha256
        or binding.get("selected_semantic_claim_sha256")!=digest(canonical_bytes(interpretation["selected"]))):
        raise ValueError("CLAIM_BINDING_CONTENT_MISMATCH")
    return {"claim_ir_sha256":original,"claim_id":binding["claim_id"],"binding_sha256":approved_binding_sha256}
