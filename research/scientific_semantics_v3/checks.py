"""Independent byte-bound declaration and scoped equation checks.

This checker reparses source XML, not interpreter symbol tables. Its result is
about the source encoding, never empirical correctness or trusted PCS authority.
Unsupported constructs remain UNKNOWN. Numerical reconstruction is separate.
"""
from __future__ import annotations

from fractions import Fraction
import hashlib
import re
import time
import xml.etree.ElementTree as ET
from xml.parsers import expat

from research.scientific_understanding_v2.rational_equivalence import compare, direct_ir
from research.scientific_understanding_v2.model_checks import safe_xml
from .evaluation import bound_source
from .numerical import parse as parse_nist, rational, reproduce


def _tag(node):return node.tag.rsplit("}",1)[-1]
def _ns(node):return node.tag[1:].split("}",1)[0] if node.tag.startswith("{") else ""


def _children(node,kind,namespace):
    return [n for n in node if _tag(n)==kind and _ns(n)==namespace]


def _one(items):
    if len(items)!=1:raise ValueError("missing or ambiguous declaration")
    return items[0]


def _group(model,container,element,ns):
    groups=_children(model,container,ns)
    if not groups:return []
    return _children(_one(groups),element,ns)


def _symbols(ir):
    if not isinstance(ir,dict):return set()
    out={ir["name"]} if ir.get("op")=="symbol" else set()
    for value in ir.values():
        if isinstance(value,dict):out|=_symbols(value)
        elif isinstance(value,list):
            for item in value:out|=_symbols(item)
    return out


def _source_spans(raw,root):
    """Independent Expat byte positions, not interpreter lexical span metadata."""
    parser=expat.ParserCreate(namespace_separator="}");stack=[];spans=[];empty=[]
    def start(name,attrs):
        if len(stack)>=64 or len(spans)>=50000:raise ValueError("XML checker resource bound")
        position=parser.CurrentByteIndex;end=position;quote=None
        while end<len(raw):
            char=raw[end]
            if quote is not None:
                if char==quote:quote=None
            elif char in (34,39):quote=char
            elif char==62:break
            end+=1
        if end>=len(raw):raise ValueError("unterminated XML start tag")
        index=len(spans);spans.append([name,position,None]);empty.append(raw[position:end].rstrip().endswith(b"/"));stack.append(index)
    def end(name):
        index=stack.pop();position=parser.CurrentByteIndex
        if not empty[index] and raw[position:position+2]==b"</":position=raw.index(b">",position)+1
        spans[index][2]=position
    parser.StartElementHandler=start;parser.EndElementHandler=end
    parser.ExternalEntityRefHandler=lambda *args:0
    parser.Parse(raw,True)
    nodes=list(root.iter())
    if len(nodes)!=len(spans):raise ValueError("XML independent span mismatch")
    out={}
    for node,(name,start,end) in zip(nodes,spans):
        expected=node.tag[1:] if node.tag.startswith("{") else node.tag
        if name!=expected:raise ValueError("XML namespace/span mismatch")
        out[id(node)]=(start,end)
    return out


def _xml_claim(claim,raw):
    root=safe_xml(raw);ns=_ns(root)
    if _tag(root)!="sbml" or not ns.startswith("http://www.sbml.org/sbml/level"):
        raise ValueError("not a supported model source")
    model=_one(_children(root,"model",ns))
    spans=_source_spans(raw,root)
    def bind_node(node):
        if spans[id(node)]!=(claim["source"]["byte_start"],claim["source"]["byte_end"]):
            raise ValueError("source quote does not identify checked declaration")
    globals_=[]
    for group,tag in [("listOfCompartments","compartment"),("listOfSpecies","species"),("listOfParameters","parameter")]:
        globals_+=_group(model,group,tag,ns)
    names=[n.get("id") for n in globals_]
    if None in names or len(names)!=len(set(names)):raise ValueError("ambiguous global symbol table")
    entity=claim["entity"];role=claim["quantity_role"];nodes=globals_
    reaction_id=claim.get("reaction_scope")
    expected_scope=model.get("id","model")+("/reaction/"+reaction_id if reaction_id else "")
    if claim.get("scope")!=expected_scope or claim.get("model_id",model.get("id","model"))!=model.get("id","model"):
        raise ValueError("forged declaration scope")
    if role=="local_parameter" and not reaction_id:raise ValueError("local declaration requires reaction scope")
    local=[];reaction=None
    if reaction_id:
        reaction=_one([n for n in _group(model,"listOfReactions","reaction",ns) if n.get("id")==reaction_id])
        law=_one(_children(reaction,"kineticLaw",ns))
        local=_group(law,"listOfParameters","parameter",ns)+_group(law,"listOfLocalParameters","localParameter",ns)
        ids=[n.get("id") for n in local]
        if None in ids or len(ids)!=len(set(ids)):raise ValueError("ambiguous local symbol table")
        nodes=local if role in {"parameter","local_parameter"} else globals_
    if claim["kind"]=="quantity" and role in {"parameter","local_parameter","compartment_size","initial_amount","initial_concentration"}:
        if claim.get("relation")!="declared_value":raise ValueError("declaration relation mismatch")
        node=_one([n for n in nodes if n.get("id")==entity])
        bind_node(node)
        required_tag={"parameter":"parameter","local_parameter":_tag(node) if _tag(node) in {"parameter","localParameter"} else "INVALID",
                      "compartment_size":"compartment","initial_amount":"species","initial_concentration":"species"}[role]
        if _tag(node)!=required_tag:raise ValueError("quantity role/node kind mismatch")
        attr={"parameter":"value","local_parameter":"value","compartment_size":"size","initial_amount":"initialAmount","initial_concentration":"initialConcentration"}[role]
        if attr not in node.attrib:raise ValueError("wrong quantity role")
        if role.startswith("initial_") and "initialAmount" in node.attrib and "initialConcentration" in node.attrib:raise ValueError("conflicting initial declaration")
        same=Fraction(node.get(attr))==Fraction(str(claim["value"]))
        return {"status":"SOURCE_DECLARATION_CHECKED" if same else "REFUTED","actual":node.get(attr),
                "checked_fields":["exact_numeric_value","declaration_role","identifier","scope","byte_source"],
                "unchecked_fields":["physical_unit_interpretation","empirical_validity"]}
    if claim["kind"]=="variable_definition" and claim["relation"]=="named_as":
        node=_one([n for n in globals_ if n.get("id")==entity])
        bind_node(node)
        return {"status":"SOURCE_DECLARATION_CHECKED" if node.get("name")==claim["value"] else "REFUTED",
                "checked_fields":["source_identifier","literal_name"],"unchecked_fields":["biological_synonym_equivalence"]}
    if claim["kind"]=="unit_definition" and role=="unit_scale":
        node=_one([n for n in _group(model,"listOfUnitDefinitions","unitDefinition",ns) if n.get("id")==entity])
        bind_node(node)
        unit=_one(_group(node,"listOfUnits","unit",ns))
        exponent=int(unit.get("exponent","1"));scale=int(unit.get("scale","0"))
        if not -8<=exponent<=8 or not -32<=scale<=32:raise ValueError("unit bound")
        actual=(Fraction(unit.get("multiplier","1"))*Fraction(10)**scale)**exponent
        equal=actual==Fraction(claim["value"]) and unit.get("kind")==claim.get("unit")
        return {"status":"SOURCE_DECLARATION_CHECKED" if equal else "REFUTED","relative_factor":str(actual),
                "checked_fields":["literal_unit_kind","relative_declared_factor"],"unchecked_fields":["scientific_quantity_applicability"]}
    if claim["kind"]=="equation" and role in {"kinetic_law","assignment_rule"}:
        if claim.get("relation")!="equation":raise ValueError("mathematical relation mismatch")
        if role=="kinetic_law":
            if reaction is None:raise ValueError("missing exact reaction scope")
            bind_node(law)
            if claim.get("lhs")!={"op":"reaction_rate","reaction":reaction_id}:raise ValueError("kinetic equation lhs mismatch")
            math_nodes=[n for n in law if n.tag=="{http://www.w3.org/1998/Math/MathML}math"]
            expression=direct_ir(_one(math_nodes))
        else:
            rules=_group(model,"listOfRules","assignmentRule",ns)
            if len({r.get('variable') for r in rules})!=len(rules):raise ValueError("conflicting assignment targets")
            rule=_one([n for n in rules if n.get("variable")==entity])
            bind_node(rule)
            if claim.get("lhs")!={"op":"symbol","name":entity}:raise ValueError("assignment equation lhs mismatch")
            expression=direct_ir(_one([n for n in rule if n.tag=="{http://www.w3.org/1998/Math/MathML}math"]))
        if any(_ns(n)!="http://www.w3.org/1998/Math/MathML" for n in (_one(math_nodes).iter() if role=="kinetic_law" else _one([n for n in rule if _tag(n)=="math"]).iter())):
            raise ValueError("foreign MathML namespace")
        independent_symbols=_symbols(expression)
        if independent_symbols!=set(claim.get("symbols",[])):raise ValueError("symbol dependency mismatch")
        defined=set(names)|{n.get("id") for n in local}
        if not independent_symbols<=defined:raise ValueError("unresolved equation symbols")
        comparison=compare(expression,claim["rhs"])
        return {"status":"SCOPED_EQUATION_CHECKED" if comparison["status"]=="EQUAL_ON_COMMON_DEFINED_DOMAIN" else "REFUTED",
                "rational_comparison":comparison,"symbol_dependencies":sorted(independent_symbols),
                "unchecked_fields":["domain_preservation","scientific_meaning","Python_Lean_refinement"]}
    return {"status":"UNKNOWN","reason":"Outside independent source declaration/equation checker subset"}


def _nist_claim(claim,raw):
    parsed=parse_nist(raw);role=claim["quantity_role"];entity=claim["entity"];actual=None
    if role=="certified_parameter":actual=parsed["parameters"].get(entity)
    elif role=="parameter_std":actual=parsed["parameter_std"].get(entity)
    else:
        key={"residual_sum_squares":"rss","residual_std":"residual_std","degrees_of_freedom":"df","observation_count":"n"}.get(role)
        if key:actual=parsed["statistics"][key]
    if actual is None:return {"status":"UNKNOWN","reason":"Statistical meaning/definition/equation needs separate review"}
    if claim.get("scope")!="model" or claim.get("kind")!="quantity" or claim.get("relation")!="reported_value":
        raise ValueError("wrong reported statistic type/scope")
    if role in {"certified_parameter","parameter_std"}:
        pattern=r"^\s*"+re.escape(entity)+r"\s*="
    else:
        label={"residual_sum_squares":"Residual Sum of Squares","residual_std":"Residual Standard Deviation",
               "degrees_of_freedom":"Degrees of Freedom","observation_count":"Number of Observations"}[role]
        pattern=r"^"+re.escape(label)+":"
    offset=0;sites=[]
    for line in raw.splitlines(keepends=True):
        if re.match(pattern,line.decode("ascii")):sites.append((offset,offset+len(line)))
        offset+=len(line)
    if sites!=[(claim["source"]["byte_start"],claim["source"]["byte_end"])]:
        raise ValueError("reported value source is not its exact table cell line")
    return {"status":"SOURCE_REPORT_CHECKED" if Fraction(actual)==Fraction(str(claim["value"])) else "REFUTED",
            "checked_fields":["printed_table_cell","reported_statistic_role"],
            "unchecked_fields":["confidence_interpretation","statistical_assumptions","optimality"]}


def check_claim(claim,artifacts):
    started=time.monotonic()
    result={"id":"check-"+claim["id"],"claim_id":claim["id"],"status":"UNKNOWN","authority":False,
            "scientific_meaning":"OPEN","source_sha256":claim["source"]["sha256"]}
    try:
        if claim.get("authority") is not False:raise ValueError("model interpretation cannot grant authority")
        if not bound_source(claim["source"],artifacts):raise ValueError("invalid exact source span")
        raw=artifacts[claim["source"]["path"]]
        if raw.lstrip().startswith(b"<?xml") or b"<sbml" in raw[:1000]:result.update(_xml_claim(claim,raw))
        elif raw.startswith(b"NIST/ITL StRD"):result.update(_nist_claim(claim,raw))
        else:result["reason"]="No independent checker for source construct"
    except (ValueError,KeyError,TypeError,ZeroDivisionError,OverflowError,ET.ParseError,expat.ExpatError) as exc:
        result.update(status="UNKNOWN",reason=type(exc).__name__+": "+str(exc)[:180])
    result["seconds"]=time.monotonic()-started
    return result


def execute(interpretation,artifacts):
    results=[check_claim(c,artifacts) for c in interpretation["claims"]]
    for path,raw in sorted(artifacts.items()):
        if raw.startswith(b"NIST/ITL StRD"):
            r=reproduce(raw);r.update(id="numerical-"+hashlib.sha256(path.encode()+raw).hexdigest()[:24],
                                    artifact_path=path,source_sha256=hashlib.sha256(raw).hexdigest())
            results.append(r)
    return results
