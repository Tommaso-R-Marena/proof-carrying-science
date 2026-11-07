"""Reference-only scoring; this module never supplies labels to interpretation.

The v3 protocol is new. Both old and new interpreters are scored by it, on the
same fresh cases, without replacing any old v2 grade. These are targeted probe
metrics against internal AI-assisted annotations, not exhaustive precision.
"""
from __future__ import annotations

from fractions import Fraction
import hashlib
import re

from research.scientific_understanding_v2.evaluation import canonical_expression
from research.scientific_understanding_v2.interpretation import parse_expression
from research.scientific_understanding_v2.rational_equivalence import compare


def _q(value):
    text=str(value)
    if type(value) is bool or len(text)>256 or not re.fullmatch(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?(?:/[1-9][0-9]*)?", text):
        raise ValueError("not a bounded number")
    if "e" in text.lower() and abs(int(text.lower().split("e")[1].split("/")[0]))>1000:
        raise ValueError("numeric exponent bound")
    return Fraction(text)


def value_equal(a,b,tolerance=0):
    if type(b) is bool:
        return type(a) is bool and a==b
    if isinstance(b,list):
        return isinstance(a,list) and len(a)==len(b) and all(value_equal(x,y,tolerance) for x,y in zip(a,b))
    try:
        return abs(_q(a)-_q(b))<=_q(tolerance)
    except (ValueError,TypeError,ZeroDivisionError):
        return type(a) is str and type(b) is str and a==b


def source_key(source,artifacts):
    path=source.get("path")
    if path in artifacts:return path
    # References are repository-relative, runtime paths project-relative. Resolve
    # only an unambiguous literal path suffix; no content/fuzzy path matching.
    if not isinstance(path,str):raise KeyError("source path")
    candidates=[p for p in artifacts if path.endswith("/"+p)]
    if len(candidates)!=1:raise KeyError("ambiguous project-relative source")
    return candidates[0]


def bound_source(source,artifacts):
    """Validate evidence against bytes, not a candidate's asserted digest/quote."""
    try:
        raw=artifacts[source_key(source,artifacts)]
        if hashlib.sha256(raw).hexdigest()!=source["sha256"]:
            return False
        start,end=source["byte_start"],source["byte_end"]
        if type(start) is not int or type(end) is not int or not 0<=start<end<=len(raw):
            return False
        return raw[start:end].decode("utf-8")==source["quote"]
    except (KeyError,TypeError,UnicodeError):
        return False


def same_source(a,b,artifacts):
    return (bound_source(a,artifacts) and bound_source(b,artifacts) and a["sha256"]==b["sha256"]
            and source_key(a,artifacts)==source_key(b,artifacts) and max(a["byte_start"],b["byte_start"])<min(a["byte_end"],b["byte_end"]))


def scope(row):
    if row.get("reaction_scope"):
        return row["reaction_scope"]
    if row.get("scope")==row.get("model_id") and row.get("scope"):
        return "model"
    return row.get("scope", "model")


def equation_match(actual,expected):
    try:
        a=actual if isinstance(actual,dict) else parse_expression(actual)
        b=expected if isinstance(expected,dict) else parse_expression(expected)
        if canonical_expression(a)==canonical_expression(b):
            return {"matches":True,"method":"bounded_canonical_syntax","domain_preservation":"NOT_INFERRED"}
        result=compare(a,b)
        return {"matches":result["status"]=="EQUAL_ON_COMMON_DEFINED_DOMAIN","method":"rational_common_domain",
                "domain_preservation":"OPEN","nonzero_obligations":result["nonzero_denominator_obligations"]}
    except (ValueError,KeyError,TypeError,RecursionError,SyntaxError):
        return {"matches":False,"method":"unsupported_or_different","domain_preservation":"OPEN"}


def compare_candidate(candidate,reference,artifacts):
    expected=reference["typed_expectation"]; missing=[]; reasons=[]
    grounding=same_source(candidate.get("source",{}),reference["source"],artifacts)
    if not grounding:reasons.append("source_binding_or_overlap")
    for field in ["kind","entity","relation"]:
        if candidate.get(field)!=expected.get(field):reasons.append(field)
    if scope(candidate)!=expected.get("scope","model"):reasons.append("scope")
    equation=None
    if "rhs" in expected:
        equation=equation_match(candidate.get("rhs"),expected["rhs"])
        if not equation["matches"]:reasons.append("equation_rhs")
        # LHS identity is already case-sensitive entity/scope; require it too
        # where the candidate represents a scalar symbol. Reaction IR uses its
        # explicit reaction name, not an invented mathematical variable.
        lhs=candidate.get("lhs",{})
        actual_lhs=lhs.get("name",lhs.get("reaction")) if isinstance(lhs,dict) else lhs
        if actual_lhs!=expected.get("lhs",expected.get("entity")):reasons.append("equation_lhs")
    elif not value_equal(candidate.get("value"),expected.get("value"),expected.get("tolerance",0)):
        reasons.append("value")
    role=candidate.get("quantity_role")
    # Scope-local parameter is a declaration-site distinction. The reference
    # specifies that site separately in its exact reaction scope.
    if role=="local_parameter" and scope(candidate)!="model":role="parameter"
    if role!=expected.get("quantity_role"):missing.append("quantity_role")
    if candidate.get("unit")!=expected.get("unit"):missing.append("explicit_unit")
    expected_conditions=expected.get("conditions",{})
    actual_conditions=candidate.get("conditions",{})
    if isinstance(expected_conditions,dict):
        for key,value in expected_conditions.items():
            if not isinstance(actual_conditions,dict) or actual_conditions.get(key)!=value:
                missing.append("condition:"+key)
    elif expected_conditions!=actual_conditions:missing.append("conditions")
    if "symbols" in expected and set(candidate.get("symbols",[]))!=set(expected["symbols"]):missing.append("symbols")
    if expected.get("domain") and candidate.get("domain")!=expected["domain"]:missing.append("domain")
    # Independent reference review confirmed these include reviewer caveats,
    # not just scientific premises. Exact prose identity is measured separately;
    # it cannot prove assumptions or determine semantic context accuracy.
    assumptions=reference.get("assumptions",[])
    missing_assumptions=[a for a in assumptions if a not in candidate.get("assumptions",[])]
    return {"candidate_id":candidate.get("id"),"grounded":grounding,"core_match":not reasons,
            "typed_context_match":not reasons and not missing,"core_mismatches":reasons,
            "missing_context":missing,"equation":equation,
            "assumption_literal_total":len(assumptions),"assumption_literals_present":len(assumptions)-len(missing_assumptions),
            "missing_assumption_literals":missing_assumptions,"assumptions_status":"OPEN; wording overlap is not semantic completeness or proof",
            "aliases_applied":["local_parameter→parameter within exact reaction scope"] if candidate.get("quantity_role")=="local_parameter" else []}


def grade(references,interpretation,artifacts,checks=()):
    claims=interpretation["claims"]; results=[]; pairs=[]
    for ref in references:
        # Probe precision counts candidates at the annotated source/entity/role
        # site. Other generated candidates remain unadjudicated, never correct
        # by default. A wrong numeric value at this site is a false pair.
        candidates=[c for c in claims if same_source(c.get("source",{}),ref["source"],artifacts)
                    and c.get("entity")==ref["typed_expectation"].get("entity")
                    and c.get("kind")==ref["typed_expectation"].get("kind")]
        comparisons=[compare_candidate(c,ref,artifacts) for c in candidates]
        core=any(x["core_match"] for x in comparisons);full=any(x["typed_context_match"] for x in comparisons)
        unit_expected=ref["typed_expectation"].get("unit") is not None
        rows={"reference_id":ref["id"],"expected_status":ref["expected_status"],
              "core_found":core,"typed_context_found":full,"comparisons":comparisons,
              "explicit_unit_annotated":unit_expected,
              "explicit_unit_core_correct":unit_expected and any(c["core_match"] and "explicit_unit" not in c["missing_context"] for c in comparisons),
              "scientific_authority_granted":False}
        if ref["expected_status"]=="supported":
            role=ref["typed_expectation"].get("quantity_role")
            pairs.extend(x["typed_context_match"] for c,x in zip(candidates,comparisons)
                         if ("parameter" if c.get("quantity_role")=="local_parameter" and scope(c)!="model" else c.get("quantity_role"))==role)
        results.append(rows)
    supported=[x for x in results if x["expected_status"]=="supported"]
    counter=[x for x in results if x["expected_status"]!="supported"]
    unsupported_promotions=sum(c.get("authority") is not False or c.get("meaning_status") in {"CERTIFIED","VERIFIED_SCIENTIFIC_MEANING"} for c in claims)
    unsupported_promotions+=sum(c.get("authority") is not False or c.get("scientific_meaning","OPEN")!="OPEN" for c in checks)
    return {"protocol":"scientific-reference-protocol-v3","supported_total":len(supported),
            "core_found":sum(x["core_found"] for x in supported),
            "typed_context_found":sum(x["typed_context_found"] for x in supported),
            "annotated_probe_pairs":len(pairs),"typed_correct_probe_pairs":sum(pairs),
            "annotated_probe_precision":sum(pairs)/len(pairs) if pairs else None,
            "correct_counterprobe_abstentions":sum(not x["core_found"] for x in counter),
            "counterprobe_core_proposals":sum(x["core_found"] for x in counter),
            "counterprobe_full_context_proposals":sum(x["typed_context_found"] for x in counter),
            "counterprobes":len(counter),"unsupported_promotions":unsupported_promotions,
            "claims_generated":len(claims),"unannotated_candidates_are_not_scored":True,
            "explicit_unit_supported_probes":sum(x["explicit_unit_annotated"] for x in supported),
            "explicit_unit_core_correct_probes":sum(x["explicit_unit_core_correct"] for x in supported),
            "assumption_measure":"Literal wording only, separately retained per candidate; scientific assumptions remain OPEN",
            "source_binding_failures":sum(not bound_source(c.get("source",{}),artifacts) for c in claims),
            "scientific_meaning_certified":0,"authority":False,"outcomes":results}


def adapt_v2(interpretation,inventory):
    """Documented schema projection, not extra extraction for the old baseline."""
    arts={a["id"]:a for a in inventory["artifacts"]}; claims=[]
    for category in ["quantities","equations"]:
        for item in interpretation.get(category,[]):
            source=item.get("source",{});art=arts.get(source.get("artifact_id"))
            if not art:continue
            raw=__import__("pathlib").Path(art["snapshot_path"]).read_bytes()
            quote=source.get("quote","");text=raw.decode("utf-8",errors="replace")
            start=text.find(quote)
            if start<0 or not quote:continue
            byte_start=len(text[:start].encode("utf-8"));byte_end=byte_start+len(quote.encode("utf-8"))
            src={"path":art["path"],"sha256":art["sha256"],"quote":quote,"byte_start":byte_start,"byte_end":byte_end}
            role=item.get("role","");relation="declared_value" if role.startswith("sbml_") else "reported_value"
            rolemap={"sbml_value":"parameter","sbml_local_parameter":"parameter","sbml_initialAmount":"initial_amount","sbml_initialConcentration":"initial_concentration","sbml_size":"compartment_size"}
            row={"id":"baseline-"+item["id"],"kind":"quantity" if category=="quantities" else "equation",
                 "entity":item.get("symbol",item.get("name")),"value":item.get("value"),
                 "relation":relation,"quantity_role":rolemap.get(role,role),"unit":item.get("unit"),
                 "scope":item.get("scope","model"),"conditions":{},"source":src,
                 "authority":False,"meaning_status":"OPEN"}
            if category=="equations":
                origin=item.get("origin","");lhs=item.get("lhs",{})
                entity=lhs.get("reaction",lhs.get("name")) if isinstance(lhs,dict) else None
                row.update(lhs=lhs,rhs=item.get("rhs"),entity=entity,relation="equation",symbols=item.get("symbols",[]),
                           quantity_role="kinetic_law" if origin=="sbml_kinetic_law" else "assignment_rule" if origin=="sbml_assignmentRule" else origin)
                if origin=="sbml_kinetic_law":row["scope"]=entity
            claims.append(row)
    return {"claims":claims,"authority":False,"projection":"schema fields only; no added source interpretation or conditions"}
