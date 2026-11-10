"""Independent Writ/13 source-commitment reference, intentionally outside Writ runtime.

This reference recomputes a bounded *explicit* root/concat dataflow manifest
from trusted byte inputs. It can check the algorithm against a runtime-produced
receipt, but cannot establish provenance/authenticity of the root inputs.
"""
from __future__ import annotations
import hashlib
import json

class SourceWitnessError(ValueError):
    pass

def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=True,
                      allow_nan=False).encode()

def sha256(raw):
    return hashlib.sha256(raw).hexdigest()

def reconstruct(policy_hash, specs, roots, recipes):
    """specs[name]=(declared_label,parent_tuple); roots[name]=(bytes,actual_label)
    recipes[name]=(ordered_parent_tuple,separator_bytes).
    """
    if len(specs)>2048 or not specs or set(roots)|set(recipes)!=set(specs):
        raise SourceWitnessError("bad resource set")
    known={}
    def visit(name,visiting=frozenset()):
        if name in visiting or len(visiting)>64 or name not in specs:
            raise SourceWitnessError("cycle/unknown/overdeep source")
        if name in known:return known[name]
        label,parents=specs[name]
        if not 0<=label<=2:raise SourceWitnessError("bad classification")
        if not parents:
            if name not in roots or name in recipes:raise SourceWitnessError("root absent")
            data,extra=roots[name]
            if not isinstance(data,bytes) or not 0<=extra<=2:raise SourceWitnessError("bad root")
            effective=max(label,extra)
            row={"name":name,"digest":sha256(data),"bytes":len(data),
                 "label":effective,"lineage":[name],
                 "root_pin":{"digest":sha256(data),"label":effective}}
        else:
            if name in roots or name not in recipes:raise SourceWitnessError("derived input missing")
            order,sep=recipes[name]
            if not isinstance(sep,bytes) or tuple(order)!=tuple(parents):
                raise SourceWitnessError("recipe changed or unordered")
            ancestors=[visit(parent,visiting|{name}) for parent in order]
            data=sep.join(x[0] for x in ancestors)
            effective=max([label]+[x[1]["label"] for x in ancestors])
            lineage={name}
            for x in ancestors:lineage.update(x[1]["lineage"])
            row={"name":name,"digest":sha256(data),"bytes":len(data),
                 "label":effective,"lineage":sorted(lineage),
                 "recipe":{"parents":list(order),"separator_digest":sha256(sep),
                           "separator_bytes":len(sep)}}
        known[name]=(data,row)
        return known[name]
    rows=[visit(name)[1] for name in sorted(specs)]
    return {"format":"writ/source-manifest/1","policy":policy_hash,"resources":rows}

def commitment(policy_hash,specs,roots,recipes):
    return sha256(canonical(reconstruct(policy_hash,specs,roots,recipes)))

def same_witness(expected_commitment,policy_hash,specs,roots,recipes):
    """Reference for restart identity comparison; monotonic witness is assumed."""
    return commitment(policy_hash,specs,roots,recipes)==expected_commitment
