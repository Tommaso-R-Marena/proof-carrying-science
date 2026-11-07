"""Bounded scientific interpretations with explicit source, scope and meaning.

This module interprets declarations, not scientific truth.  It does not execute
submitted code, use a model or import evaluation labels.  Algebraic comparison
is deliberately separate from the roles, units, domains and assumptions of a
scientific assertion.  The older parser is reused for its closed arithmetic and
XML lexical-span implementations; none of its historical outputs are rewritten.
"""
from __future__ import annotations

import ast
from collections import Counter
from copy import deepcopy
from fractions import Fraction
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import xml.etree.ElementTree as ET

from research.scientific_understanding_v2 import interpretation as previous
from research.scientific_understanding_v2 import dimensions, rational_equivalence

VERSION = "scientific-semantics/v3.0"
MAX_FILE = 1_000_000
MAX_FILES = 256
MAX_ENTRIES = 1024
MAX_TOTAL = 16_000_000
MAX_CLAIMS = 6000
MAX_DEPTH = 16
NUMBER = previous.NUMBER
NUM = re.compile(NUMBER + r"\Z")
MATH_NS = "http://www.w3.org/1998/Math/MathML"
SBML_NAMESPACES = frozenset({
    "http://www.sbml.org/sbml/level2/version4", "http://www.sbml.org/sbml/level2/version3",
    "http://www.sbml.org/sbml/level2/version2", "http://www.sbml.org/sbml/level2",
    "http://www.sbml.org/sbml/level3/version1/core", "http://www.sbml.org/sbml/level3/version2/core",
})
TEXT_SUFFIXES = frozenset({".txt", ".md", ".rst", ".tex", ".html", ".htm", ".dat", ".log"})


def canonical_bytes(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def exact_number(value):
    """A decimal source literal, represented exactly and with finite budgets."""
    if type(value) not in (str, int) or isinstance(value, bool):
        raise ValueError("exact source number must be a decimal string or integer")
    text = str(value)
    if len(text) > 128 or not NUM.fullmatch(text):
        raise ValueError("invalid bounded decimal")
    if "e" in text.lower() and abs(int(text.lower().split("e")[1])) > 1000:
        raise ValueError("decimal exponent limit")
    q = Fraction(text)
    return {"literal": text, "numerator": str(q.numerator), "denominator": str(q.denominator)}


def _local(element):
    return element.tag.rsplit("}", 1)[-1]


def _namespace(element):
    return element.tag[1:].split("}", 1)[0] if element.tag.startswith("{") else ""


def _children(element, tag):
    return [child for child in element if _local(child) == tag]


def _symbols(ir):
    if not isinstance(ir, dict):
        return []
    out = []
    if ir.get("op") == "symbol":
        out.append(ir["name"])
    for value in ir.values():
        if isinstance(value, dict):
            out.extend(_symbols(value))
        elif isinstance(value, list):
            for item in value:
                out.extend(_symbols(item))
    return sorted(set(out))


def _mathml(element):
    """Reuse the closed parser, adding exact rational MathML numbers.

    Numeric base and unit annotations cannot be silently discarded. A copy is
    transformed so all evidence still points to the original untouched bytes.
    """
    copied=deepcopy(element)
    for node in list(copied.iter()):
        if _local(node)!="cn":
            continue
        if node.attrib.get("base","10")!="10" or any(key.rsplit("}",1)[-1]=="units" for key in node.attrib):
            raise previous.Unsupported("MathML numeric base or units outside the supported fragment")
        kind=node.attrib.get("type","real")
        if kind not in {"real","integer","e-notation","rational"}:
            raise previous.Unsupported("unsupported MathML numeric type")
        if kind=="integer" and not re.fullmatch(r"[+-]?[0-9]+",(node.text or "").strip()):
            raise previous.Unsupported("invalid MathML integer literal")
        if kind=="rational":
            if len(node)!=1 or _local(node[0])!="sep":
                raise previous.Unsupported("invalid rational MathML number")
            left,right=(node.text or "").strip(),(node[0].tail or "").strip()
            if not all(re.fullmatch(r"[+-]?[0-9]+",x) for x in (left,right)) or not int(right):
                raise previous.Unsupported("invalid rational MathML numerator or denominator")
            exact_number(left);exact_number(right)
            node.clear();node.tag="{"+MATH_NS+"}apply"
            ET.SubElement(node,"{"+MATH_NS+"}divide")
            ET.SubElement(node,"{"+MATH_NS+"}cn").text=left
            ET.SubElement(node,"{"+MATH_NS+"}cn").text=right
    return previous._mathml(copied)


def _denominators(ir):
    out = []
    if not isinstance(ir, dict):
        return out
    if ir.get("op") == "div" and len(ir.get("args", [])) == 2:
        out.append({"relation": "nonzero", "expression": ir["args"][1]})
    if ir.get("op") == "pow" and len(ir.get("args", [])) == 2:
        power = ir["args"][1]
        if power.get("op") == "neg" or power.get("op") == "number" and power.get("value", "").startswith("-"):
            out.append({"relation": "nonzero", "expression": ir["args"][0]})
    for value in ir.values():
        if isinstance(value, dict):
            out.extend(_denominators(value))
        elif isinstance(value, list):
            for item in value:
                out.extend(_denominators(item))
    return [dict(v) for _, v in sorted({digest(v): v for v in out}.items())]


def _safe_name(value):
    previous._symbol(value)
    return value


def _read_project(root):
    """Read regular files once using directory descriptors and no-follow opens.

    Byte identity is what is bound here; this is not a persistent immutable
    storage boundary. No path is reopened by an interpretation operation.
    """
    root = Path(root)
    root_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    output, total, entries = [], 0, 0
    def walk(fd, prefix, depth):
        nonlocal total, entries
        if depth > MAX_DEPTH:
            raise ValueError("project directory depth limit")
        names=[]
        with os.scandir(fd) as scan:
            for item in scan:
                entries+=1
                if entries>MAX_ENTRIES:
                    raise ValueError("project total directory-entry limit")
                names.append(item.name)
        for name in sorted(names):
            if name in {".", ".."}:
                continue
            entry = os.stat(name, dir_fd=fd, follow_symlinks=False)
            rel = prefix + name
            if len(rel.encode("utf-8"))>4096:
                raise ValueError("project relative-path byte limit")
            if stat.S_ISLNK(entry.st_mode):
                raise ValueError("project symlinks are not admitted: " + rel)
            if stat.S_ISDIR(entry.st_mode):
                child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                try:
                    walk(child, rel + "/", depth + 1)
                finally:
                    os.close(child)
                continue
            if not stat.S_ISREG(entry.st_mode):
                raise ValueError("project contains a nonregular file")
            if len(output) >= MAX_FILES or entry.st_size > MAX_FILE:
                raise ValueError("project file count or size limit")
            child = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
            try:
                check = os.fstat(child)
                if not stat.S_ISREG(check.st_mode) or check.st_size > MAX_FILE:
                    raise ValueError("source changed to a nonregular or excessive file")
                chunks, n = [], 0
                while True:
                    chunk = os.read(child, min(65536, MAX_FILE + 1 - n))
                    if not chunk:
                        break
                    chunks.append(chunk)
                    n += len(chunk)
                    if n > MAX_FILE:
                        raise ValueError("source grew beyond the file bound")
                raw = b"".join(chunks)
            finally:
                os.close(child)
            total += len(raw)
            if total > MAX_TOTAL:
                raise ValueError("project total byte limit")
            output.append((rel, raw))
    try:
        walk(root_fd, "", 0)
    finally:
        os.close(root_fd)
    return output


class _Project:
    def __init__(self):
        self.result = {"schema_version": VERSION, "artifacts": [], "claims": [], "symbols": [],
                       "dependencies": [], "obligations": [], "unresolved": [],
                       "authority": False, "meaning_status": "INTERNAL_INTERPRETATION_REQUIRES_REVIEW"}
        self.raw = {}
        self.seen = set()

    def evidence(self, artifact, text, start, end, **locator):
        # Text was decoded with UTF-8, not utf-8-sig: a BOM remains a character
        # and contributes to offsets. XML parsing accepts it.
        prefix, content = text[:start].encode(), text[start:end].encode()
        if self.raw[artifact["path"]][len(prefix):len(prefix)+len(content)] != content:
            raise ValueError("UTF-8 source span does not reproduce original bytes")
        return {"path": artifact["path"], "sha256": artifact["sha256"], "artifact_id": artifact["id"],
                "byte_start": len(prefix), "byte_end": len(prefix)+len(content), "quote": text[start:end],
                "locator": {"line_start": text.count("\n", 0, start)+1,
                            "line_end": text.count("\n", 0, end)+1, **locator}}

    def add(self, category, value):
        record = dict(value)
        record.update(authority=False, meaning_status="SOURCE_INTERPRETATION_NOT_SCIENTIFIC_CERTIFICATION")
        record["id"] = category.rstrip("s") + "-" + digest([category, record])[:24]
        if record["id"] in self.seen:
            return record
        if len(self.result[category]) >= MAX_CLAIMS:
            raise ValueError("interpretation item limit")
        self.seen.add(record["id"])
        self.result[category].append(record)
        return record

    def unresolved(self, source, reason, **extra):
        return self.add("unresolved", {"source": source, "reason": reason, **extra})

    def claim(self, source, **values):
        base = {"kind": "quantity", "subject": None, "entity": None, "relation": "declared_value",
                "quantity_role": None, "unit": None, "conditions": {}, "assumptions": [],
                "domain": None, "symbols": [], "evidence_kind": "source_declaration", "source": source}
        base.update(values)
        if base["entity"] is None:
            base["entity"] = base["subject"]
        if base["subject"] is None:
            base["subject"] = base["entity"]
        if "value" in base and type(base["value"]) in (str, int):
            try:
                base["exact_value"] = exact_number(base["value"])
            except ValueError:
                pass
        claim = self.add("claims", base)
        self.add("obligations", {"kind": "scientific_meaning_review", "claim_id": claim["id"],
                                 "status": "OPEN", "source": source,
                                 "reason": "Source declaration/report is not empirical validation or mathematical proof"})
        return claim


def _unit_record(name, definitions):
    if name is None:
        return {"declared": None, "status": "UNSPECIFIED", "dimension": None, "factor": None}
    if name in definitions:
        return definitions[name]
    mapped = previous._BASE_UNITS.get(name, name)
    try:
        parsed = dimensions.parse_unit(mapped)
        return {"declared": name, "expression": mapped, "dimension": list(parsed.dimension),
                "factor": {"numerator": str(parsed.factor.numerator), "denominator": str(parsed.factor.denominator)},
                "status": "SUPPORTED_MULTIPLICATIVE_UNIT"}
    except dimensions.DimensionIssue:
        return {"declared": name, "expression": mapped, "status": "UNSUPPORTED_UNIT", "dimension": None, "factor": None}


def _quotient_unit(numerator, denominator, definitions):
    if not numerator or not denominator:
        return None, _unit_record(None,{})
    name=f"({numerator})/({denominator})"
    a,b=_unit_record(numerator,definitions),_unit_record(denominator,definitions)
    if a.get("dimension") is None or b.get("dimension") is None:
        return name,_unit_record(name,{})
    factor=Fraction(int(a["factor"]["numerator"]),int(a["factor"]["denominator"]))/Fraction(int(b["factor"]["numerator"]),int(b["factor"]["denominator"]))
    return name,{"declared":name,"dimension":[x-y for x,y in zip(a["dimension"],b["dimension"])],"factor":{"numerator":str(factor.numerator),"denominator":str(factor.denominator)},"status":"DERIVED_FROM_EXPLICIT_DECLARATIONS"}


def _sbml(project, artifact, text):
    short = project.evidence(artifact, text, 0, min(len(text), 8192))
    try:
        if re.search(r"<!\s*(?:DOCTYPE|ENTITY)\b", text, re.I):
            raise ValueError("XML DTDs/entities are forbidden")
        lexical = previous._xml_spans(text)
        root = ET.fromstring(text)
        elements = list(root.iter())
        if len(elements) != len(lexical):
            raise ValueError("XML lexical binding mismatch")
        spans = {id(node): span for node, span in zip(elements, lexical)}
        namespace = _namespace(root)
        if _local(root) != "sbml" or namespace not in SBML_NAMESPACES:
            raise ValueError("supported SBML namespace required")
        models = _children(root, "model")
        if len(models) != 1 or _namespace(models[0]) != namespace:
            raise ValueError("SBML must contain one same-namespace model")
        model = models[0]
        # A foreign namespace cannot introduce model declarations masquerading
        # under the same local XML tag. Annotation XHTML/RDF remain inert data.
        structural = {"species", "parameter", "localParameter", "compartment", "reaction", "kineticLaw", "assignmentRule",
                      "rateRule", "algebraicRule", "initialAssignment", "unit", "unitDefinition", "speciesReference",
                      "listOfCompartments", "listOfSpecies", "listOfParameters", "listOfLocalParameters", "listOfReactions",
                      "listOfRules", "listOfInitialAssignments", "listOfUnitDefinitions", "listOfUnits", "listOfReactants", "listOfProducts", "listOfModifiers", "modifierSpeciesReference"}
        if any(_local(e) in structural and _namespace(e) != namespace for e in elements):
            raise ValueError("foreign namespace in an SBML structural declaration")
        def source(node):
            a, b = spans[id(node)]
            return project.evidence(artifact, text, a, b, xml_element=_local(node), xml_id=node.attrib.get("id"))
        # A narrow linguistic pattern records an explicitly qualified model
        # prediction. It neither certifies a range nor turns a prediction into
        # a measured biological finding. Source paragraph context is retained.
        for paragraph in model.iter():
            if _local(paragraph) != "p" or _namespace(paragraph) != "http://www.w3.org/1999/xhtml":
                continue
            paragraph_text = " ".join(paragraph.itertext())
            prediction = re.search(r"\bpredict\s+that\s+the\s+period\s+of\s+oscillations\s+can\s+range\s+from\s+(seconds|minutes|hours|days)\s+to\s+(seconds|minutes|hours|days)\b", paragraph_text, re.I)
            if prediction:
                context = {}
                if re.search(r"MAPK\s+cascades",paragraph_text):
                    context["system"] = "MAPK cascades"
                if re.search(r"(?:Based on|based on)\s+recent\s+kinetic\s+data",paragraph_text):
                    context["basis"] = "recent kinetic data"
                project.claim(source(paragraph),entity="oscillation_period",kind="scientific_claim",relation="predicts_range",quantity_role="model_prediction",value=[prediction[1].lower(),prediction[2].lower()],unit="time",scope="publication_abstract",conditions=context,evidence_kind="author_prediction",assumptions=["Prediction reported by authors; biological validity and quantitative reproduction remain unresolved"])
        scope = model.attrib.get("id", "model")
        containers={"listOfSpecies":"species","listOfParameters":"parameter","listOfCompartments":"compartment",
                    "listOfReactions":"reaction","listOfUnitDefinitions":"unitDefinition","listOfInitialAssignments":"initialAssignment"}
        for container,child_tag in containers.items():
            groups=_children(model,container)
            if len(groups)>1 or any(_local(child)!=child_tag for group in groups for child in group):
                raise ValueError("duplicate or malformed SBML structural container")
        if len(_children(model,"listOfRules"))>1:
            raise ValueError("duplicate SBML rule container")
        globals_ = [node for group in model if _local(group) in {"listOfSpecies", "listOfParameters", "listOfCompartments"} for node in group]
        ids = [node.attrib.get("id") for node in globals_]
        if any(not name for name in ids) or len(set(ids)) != len(ids):
            raise ValueError("missing or duplicate global SBML identifier")
        for identifier in ids:
            _safe_name(identifier)
        # These are model-closure checks, not a complete SBML validator. A
        # malformed declaration cannot silently become a coherent modeled state.
        for node in globals_:
            tag = _local(node)
            if tag not in {"species", "parameter", "compartment"}:
                raise ValueError("unsupported global declaration kind")
            for flag in ("constant", "boundaryCondition", "hasOnlySubstanceUnits"):
                if flag in node.attrib and node.attrib[flag] not in {"true", "false", "1", "0"}:
                    raise ValueError("invalid SBML boolean declaration")
            if tag == "species" and node.attrib.get("compartment") not in {n.attrib["id"] for n in globals_ if _local(n)=="compartment"}:
                raise ValueError("species references an undeclared compartment")
        all_reactions = [node for group in _children(model,"listOfReactions") for node in group]
        reaction_ids = [node.attrib.get("id") for node in all_reactions]
        if any(not i for i in reaction_ids) or len(set(reaction_ids)) != len(reaction_ids) or set(ids) & set(reaction_ids):
            raise ValueError("duplicate or colliding global reaction identifiers")
        for reaction in all_reactions:
            for flag in ("reversible","fast"):
                if flag in reaction.attrib and reaction.attrib[flag] not in {"true","false","1","0"}:
                    raise ValueError("invalid SBML reaction boolean declaration")
        rules = [node for group in _children(model,"listOfRules") for node in group if _local(node) in {"assignmentRule","rateRule"}]
        targets = [node.attrib.get("variable") for node in rules]
        initial = [node for group in _children(model,"listOfInitialAssignments") for node in group]
        initial_targets = [node.attrib.get("symbol") for node in initial]
        if len(set(targets)) != len(targets) or len(set(initial_targets)) != len(initial_targets):
            raise ValueError("duplicate or conflicting SBML rule targets")
        assignment_targets = {node.attrib.get("variable") for node in rules if _local(node)=="assignmentRule"}
        if assignment_targets & set(initial_targets):
            raise ValueError("initial assignment conflicts with assignment rule")
        global_nodes = {node.attrib["id"]:node for node in globals_}
        for target in targets+initial_targets:
            if target not in global_nodes:
                raise ValueError("assignment targets an undeclared global symbol")
        for target in targets:
            node = global_nodes[target]
            # Parameters/compartments default constant=true; species default
            # false. This matters to the model, not to unit interpretation.
            default = "false" if _local(node)=="species" else "true"
            if node.attrib.get("constant",default) in {"true","1"}:
                raise ValueError("rule targets a constant SBML symbol")
        dependency_graph = {}
        for rule in rules:
            if _local(rule)!="assignmentRule":
                continue
            maths = _children(rule,"math")
            try:
                rhs=_mathml(maths[0]) if len(maths)==1 else None
                dependency_graph[rule.attrib["variable"]] = set(_symbols(rhs)) & assignment_targets
            except previous.Unsupported:
                pass
        # Kahn elimination avoids recursion and detects algebraic assignment
        # cycles; differential feedback through rates is intentionally allowed.
        pending={k:set(v) for k,v in dependency_graph.items()}
        while pending:
            ready={k for k,v in pending.items() if not v}
            if not ready:
                raise ValueError("cyclic SBML assignment-rule dependencies")
            pending={k:v-ready for k,v in pending.items() if k not in ready}
        unit_defs = {}
        for group in _children(model, "listOfUnitDefinitions"):
            for definition in group:
                identifier = definition.attrib.get("id")
                if not identifier or identifier in unit_defs:
                    raise ValueError("missing or duplicate SBML unit definition")
                terms, factor, dimension, supported = [], Fraction(1), [0]*7, True
                for units in _children(definition, "listOfUnits"):
                    for term in units:
                        try:
                            kind = term.attrib["kind"]
                            exponent = int(term.attrib.get("exponent", "1"))
                            scale = int(term.attrib.get("scale", "0"))
                            multiplier = Fraction(term.attrib.get("multiplier", "1"))
                            if abs(exponent) > 32 or abs(scale) > 64 or multiplier <= 0 or multiplier.numerator.bit_length() > 256 or multiplier.denominator.bit_length() > 256:
                                raise ValueError("unit arithmetic resource bound")
                            if "offset" in term.attrib and Fraction(term.attrib["offset"]) != 0:
                                raise ValueError("affine unit offsets are unsupported")
                            base = _unit_record(kind, {})
                            if base["dimension"] is None:
                                raise ValueError("unsupported SBML unit kind")
                            base_factor = Fraction(int(base["factor"]["numerator"]), int(base["factor"]["denominator"]))
                            factor *= (multiplier * 10**scale * base_factor if scale >= 0 else multiplier * Fraction(1, 10**-scale) * base_factor) ** exponent
                            dimension = [a + exponent*b for a, b in zip(dimension, base["dimension"])]
                            if max(abs(x) for x in dimension) > 1024 or factor.numerator.bit_length() > 4096 or factor.denominator.bit_length() > 4096:
                                raise ValueError("unit result resource bound")
                            terms.append({"kind": kind, "exponent": exponent, "scale": scale, "multiplier": str(multiplier)})
                        except (ValueError, KeyError, ZeroDivisionError, OverflowError):
                            supported = False
                unit_defs[identifier] = {"declared": identifier, "terms": terms, "source": source(definition),
                                         "status": "SUPPORTED_MULTIPLICATIVE_UNIT" if supported and terms else "UNSUPPORTED_UNIT",
                                         "dimension": dimension if supported and terms else None,
                                         "factor": {"numerator": str(factor.numerator), "denominator": str(factor.denominator)} if supported and terms else None}
                project.add("symbols", {"symbol": identifier, "scope": scope, "role": "unit_definition", "source": source(definition), "unit_resolution": unit_defs[identifier]})
                if len(terms) == 1 and terms[0]["exponent"] == 1 and supported:
                    term = terms[0]
                    relative = Fraction(term["multiplier"]) * (10**term["scale"] if term["scale"] >= 0 else Fraction(1,10**-term["scale"]))
                    project.claim(source(definition), entity=identifier, kind="unit_definition", relation="unit_definition", quantity_role="unit_scale", value=str(relative), unit=term["kind"], unit_resolution=unit_defs[identifier], scope=scope, model_id=scope, conditions={"source_unit":identifier,"scale":str(term["scale"])}, terms=terms,
                                  dimension="amount_of_substance" if unit_defs[identifier]["dimension"] == [0,0,0,0,0,1,0] else unit_defs[identifier]["dimension"])
                else:
                    project.claim(source(definition), entity=identifier, kind="unit_definition", relation="unit_definition", quantity_role="unit_definition", value=terms, unit=identifier, unit_resolution=unit_defs[identifier], scope=scope, model_id=scope)
        symbol_map = {}
        compartments = {node.attrib["id"]: node for node in globals_ if _local(node) == "compartment"}
        for node in globals_:
            identifier, tag = node.attrib["id"], _local(node)
            raw_unit = node.attrib.get("substanceUnits") if tag == "species" else node.attrib.get("units")
            if tag == "species" and raw_unit is None:
                raw_unit = model.attrib.get("substanceUnits")
            symbol_unit,symbol_resolution=raw_unit,_unit_record(raw_unit,unit_defs)
            if tag=="species":
                compartment=compartments.get(node.attrib.get("compartment"))
                is_amount=node.attrib.get("hasOnlySubstanceUnits") in {"true","1"} or compartment is not None and compartment.attrib.get("spatialDimensions")=="0"
                if not is_amount:
                    symbol_unit,symbol_resolution=_quotient_unit(raw_unit,compartment.attrib.get("units") if compartment is not None else None,unit_defs)
            record = project.add("symbols", {"symbol": identifier, "scope": scope, "role": tag,
                                             "name": node.attrib.get("name"), "source": source(node),
                                             "unit": symbol_unit, "unit_resolution": symbol_resolution,
                                             "source_declared_unit": raw_unit,
                                             "declarations": {key: value for key, value in node.attrib.items() if key not in {"id", "name"}}})
            symbol_map[identifier] = record
            if node.attrib.get("name"):
                project.claim(source(node), entity=identifier, kind="variable_definition", relation="named_as", quantity_role="biological_identifier" if tag == "species" else tag+"_name", value=node.attrib["name"], scope=scope, model_id=scope, conditions={"compartment":node.attrib["compartment"]} if "compartment" in node.attrib else {}, symbol_id=record["id"])
        # L2 implicit time and substance defaults are not promoted into explicit
        # scientific unit declarations. Specification defaults can be reviewed.
        for node in globals_:
            identifier, tag = node.attrib["id"], _local(node)
            record = symbol_map[identifier]
            for attr, role in (("value", "parameter"), ("size", "compartment_size"),
                               ("initialAmount", "initial_amount"), ("initialConcentration", "initial_concentration")):
                if attr not in node.attrib:
                    continue
                try:
                    exact_number(node.attrib[attr])
                    if tag == "species" and "initialAmount" in node.attrib and "initialConcentration" in node.attrib:
                        raise ValueError("species declares both initial amount and concentration")
                    conditions = {}
                    if attr.startswith("initial"):
                        conditions["state"] = "initial"
                    if tag == "species":
                        conditions["compartment"] = node.attrib.get("compartment", "UNDECLARED")
                    unit = record["source_declared_unit"]
                    resolution = _unit_record(unit,unit_defs)
                    if attr == "initialConcentration":
                        compartment = compartments.get(node.attrib.get("compartment"))
                        volume_unit = compartment.attrib.get("units") if compartment is not None else None
                        unit,resolution=_quotient_unit(unit,volume_unit,unit_defs)
                    project.claim(source(node), entity=identifier, quantity_role=role, value=node.attrib[attr],
                                  unit=unit, unit_resolution=resolution, conditions=conditions, scope=scope,
                                  symbol_id=record["id"], model_id=scope, declarations=record["declarations"],
                                  source_attribute=attr)
                except ValueError as exc:
                    project.unresolved(source(node), str(exc))
        # Structural counts are exact properties of this encoding, not counts
        # of biological entities in nature or in a paper.
        for tag, role in (("species", "species_count"), ("reaction", "reaction_count"), ("parameter", "global_parameter_count")):
            nodes = [node for group in model if _local(group) == "listOf" + {"species": "Species", "reaction": "Reactions", "parameter": "Parameters"}[tag] for node in group if _local(node) == tag]
            # Ground count in its actual container; no child-count claim if no
            # container occurs in the source.
            groups = _children(model, "listOf" + {"species": "Species", "reaction": "Reactions", "parameter": "Parameters"}[tag])
            if groups:
                project.claim(source(groups[0]), entity=scope, quantity_role=role, value=str(len(nodes)),
                              relation="structural_count", unit="count", evidence_kind="computational_structure",
                              conditions=["SBML encoding only"], scope=scope)
        def equation(node, lhs, role, entity, local_symbols=None, **extra):
            maths = _children(node, "math")
            try:
                if len(maths) != 1 or any(_namespace(e) != MATH_NS for e in maths[0].iter()):
                    raise ValueError("unique MathML namespace expression required")
                rhs = _mathml(maths[0])
                refs = _symbols(rhs)
                lookup = {**symbol_map, **(local_symbols or {})}
                resolved, unknown = [], []
                for ref in refs:
                    if ref in lookup:
                        resolved.append({"symbol": ref, "symbol_id": lookup[ref]["id"], "scope": lookup[ref]["scope"]})
                    elif ref == "time":
                        resolved.append({"symbol": ref, "role": "SBML_time", "scope": scope})
                    else:
                        unknown.append(ref)
                declared_dimensions = {ref:lookup[ref]["unit_resolution"]["dimension"] for ref in refs if ref in lookup and lookup[ref].get("unit_resolution",{}).get("dimension") is not None}
                declared_units = {ref:lookup[ref]["unit"] for ref in refs if ref in lookup and lookup[ref].get("unit")}
                claim = project.claim(source(node), entity=entity, kind="equation", relation="equation", quantity_role=role,
                                      lhs=lhs, rhs=rhs, expression=previous.render_expression(rhs), symbols=refs,
                                      symbol_bindings=resolved, symbol_units=declared_units, symbol_dimensions=declared_dimensions, unresolved_symbols=unknown, domain={"number_system": "real", "required_nonzero": _denominators(rhs)},
                                      model_id=scope, scope=extra.pop("scope", scope), conditions={"reaction":entity} if role == "kinetic_law" else {}, **extra)
                for binding in resolved:
                    if "symbol_id" in binding:
                        project.add("dependencies", {"from_claim": claim["id"], "to_symbol": binding["symbol_id"], "symbol": binding["symbol"], "source": source(node), "kind": "mathematical_symbol_reference"})
                if unknown:
                    project.unresolved(source(node), "MathML references undeclared symbols", symbols=unknown, claim_id=claim["id"])
                if _denominators(rhs):
                    project.add("obligations", {"kind": "expression_domain", "status": "OPEN", "claim_id": claim["id"], "conditions": _denominators(rhs), "source": source(node)})
                return claim
            except (ValueError, previous.Unsupported) as exc:
                project.unresolved(source(node), "Unsupported mathematical declaration: " + str(exc))
        for group in model:
            if _local(group) in {"listOfRules", "listOfInitialAssignments"}:
                for node in group:
                    tag = _local(node)
                    identifier = node.attrib.get("variable", node.attrib.get("symbol"))
                    if tag == "algebraicRule":
                        equation(node, {"op": "number", "value": "0"}, "algebraic_rule", scope)
                    elif tag in {"assignmentRule", "initialAssignment", "rateRule"} and identifier in symbol_map:
                        lhs = {"op": "derivative", "state": identifier, "variable": "time"} if tag == "rateRule" else {"op": "symbol", "name": identifier}
                        equation(node, lhs, {"assignmentRule":"assignment_rule", "initialAssignment":"initial_assignment", "rateRule":"rate_rule"}[tag], identifier)
                    else:
                        project.unresolved(source(node), "Unsupported rule or undeclared assigned symbol")
            if _local(group) != "listOfReactions":
                continue
            reaction_ids = [node.attrib.get("id") for node in group]
            if any(not name for name in reaction_ids) or len(reaction_ids) != len(set(reaction_ids)):
                project.unresolved(source(group), "Missing or duplicate reaction identifiers")
                continue
            for reaction in group:
                reaction_id = reaction.attrib["id"]
                laws = _children(reaction, "kineticLaw")
                if len(laws) != 1:
                    project.unresolved(source(reaction), "Reaction lacks unique kinetic law")
                    continue
                law, local_map = laws[0], {}
                local_nodes = [node for local_group in law if _local(local_group) in {"listOfParameters", "listOfLocalParameters"} for node in local_group]
                local_ids = [node.attrib.get("id") for node in local_nodes]
                if any(not name for name in local_ids) or len(local_ids) != len(set(local_ids)):
                    project.unresolved(source(law), "Missing or duplicate local identifiers")
                    continue
                for parameter in local_nodes:
                    name = _safe_name(parameter.attrib["id"])
                    unit = parameter.attrib.get("units")
                    local_scope = scope + "/reaction/" + reaction_id
                    record = project.add("symbols", {"symbol": name, "scope": local_scope, "role": "local_parameter",
                                                     "unit": unit, "source": source(parameter), "unit_resolution": _unit_record(unit, unit_defs)})
                    local_map[name] = record
                    if "value" in parameter.attrib:
                        try:
                            exact_number(parameter.attrib["value"])
                            project.claim(source(parameter), entity=name, quantity_role="local_parameter", relation="declared_value",
                                          scope=local_scope, reaction_scope=reaction_id, value=parameter.attrib["value"], unit=unit, unit_resolution=record["unit_resolution"],
                                          symbol_id=record["id"], conditions={"reaction":reaction_id}, model_id=scope, source_attribute="value")
                        except ValueError as exc:
                            project.unresolved(source(parameter), str(exc))
                equation(law, {"op": "reaction_rate", "reaction": reaction_id}, "kinetic_law", reaction_id, local_map, scope=scope + "/reaction/" + reaction_id, reaction_scope=reaction_id)
    except (ValueError, previous.Unsupported, ET.ParseError, RecursionError, MemoryError) as exc:
        project.unresolved(short, "SBML interpretation rejected: " + str(exc)[:240])


def _text(project, artifact, text):
    """Explicit declarations and printed quantities; no free-form conclusions."""
    lines = text.splitlines(keepends=True)
    offset = 0
    nist = bool(re.search(r"NIST|Statistical Reference Datasets|Certified Values", text, re.I))
    procedure=re.search(r"^\s*Procedure:\s*(Nonlinear Least Squares Regression|Linear Least Squares Regression)\s*$",text,re.I|re.M)
    estimation_conditions={}
    if procedure:
        estimation_conditions["estimation"]="nonlinear_least_squares" if procedure[1].lower().startswith("nonlinear") else "linear_least_squares"
    parameter_table = False
    for index, line in enumerate(lines):
        source = project.evidence(artifact, text, offset, offset + len(line))
        offset += len(line)
        clean = line.strip()
        if not clean:
            continue
        # Official StRD tables distinguish starting values, certified estimates
        # and their standard deviations. Parse columns; never use the first
        # number as the certified estimate merely because it is nearby.
        if nist and re.search(r"Certified Values", line, re.I):
            parameter_table = True
        param = re.fullmatch(r"\s*(b\d+)\s*=\s*((?:" + NUMBER + r"\s+){1,8}" + NUMBER + r")\s*", line)
        if nist and parameter_table and param:
            values = re.findall(NUMBER, param[2])
            if len(values) == 4:
                entity = param[1]
                project.claim(source, entity=entity, value=values[2], quantity_role="certified_parameter", relation="reported_value", evidence_kind="author_report", scope="model", conditions=dict(estimation_conditions), unit=None)
                project.claim(source, entity=entity, value=values[3], quantity_role="parameter_std", relation="reported_value", evidence_kind="author_report", scope="model", conditions={"parameter":entity,"statistic":"standard_deviation"}, unit=None)
            else:
                project.unresolved(source, "NIST parameter row lacks four unambiguous starting/certified/std columns")
            continue
        if nist:
            labels = [(r"Residual\s+Sum\s+of\s+Squares", "residual_sum_squares"),
                      (r"Residual\s+Standard\s+Deviation", "residual_std"),
                      (r"Degrees\s+of\s+Freedom", "degrees_of_freedom"),
                      (r"Number\s+of\s+Observations", "observation_count")]
            for label, role in labels:
                match = re.search(label + r"\s*[:=]\s*(" + NUMBER + r")\s*$", line, re.I)
                if match:
                    project.claim(source, entity=role, value=match[1], quantity_role=role, relation="reported_value", evidence_kind="author_report", unit="count" if role in {"degrees_of_freedom", "observation_count"} else None, scope="model", conditions=dict(estimation_conditions))
            variable = re.search(r"\b(?P<role>Predictor|Response)\s*\(\s*(?P<symbol>[A-Za-z][A-Za-z0-9_]*)\s*=\s*(?P<name>[A-Za-z ]+?)(?:,\s*(?P<unit>degrees kelvin|kelvin|degrees Celsius|degree Celsius))?\s*\)", line, re.I)
            if variable:
                source_unit = variable["unit"]
                unit = {"degrees kelvin":"K", "kelvin":"K", "degrees celsius":"degC", "degree celsius":"degC"}.get(source_unit.lower()) if source_unit else None
                project.claim(source, entity=variable["symbol"], kind="variable_definition", relation="defined_as", value=variable["name"].strip(), quantity_role=variable["role"].lower(), unit=unit, source_unit_literal=source_unit, unit_resolution=_unit_record(unit,{}), scope="model")
            # An equation with an explicit residual e is a statistical model,
            # not an exact deterministic relation after dropping the residual.
            match = re.search(r"^\s*y\s*=\s*(.{1,4096})", line)
            if match:
                expression = match[1].strip()
                if expression.endswith(("+", "-", "*", "/", "(")):
                    # Only bounded explicitly continued arithmetic lines enter
                    # the same source-grounded equation. Never absorb arbitrary
                    # following prose or skip the residual term.
                    joined = expression
                    end = offset
                    for continuation in lines[index+1:index+5]:
                        if not continuation.strip() or len(joined)+len(continuation)>4096:
                            break
                        joined += " " + continuation.strip()
                        end += len(continuation)
                        try:
                            previous.parse_expression(joined.replace("^", "**"))
                            expression = joined
                            source = project.evidence(artifact, text, offset-len(line), end)
                            break
                        except previous.Unsupported:
                            continue
                    else:
                        pass
                try:
                    rhs = previous.parse_expression(expression.replace("^", "**"))
                    project.claim(source, kind="equation", entity="y", relation="equation", quantity_role="statistical_model", lhs={"op": "symbol", "name": "y"}, rhs=rhs, symbols=_symbols(rhs), domain={"number_system":"real", "required_nonzero":_denominators(rhs)}, assumptions=["Residual symbol is retained; no distribution or independence assumption inferred"], evidence_kind="source_declaration", scope="model", conditions={"error_term":"additive e"} if "e" in _symbols(rhs) else {})
                except previous.Unsupported:
                    project.unresolved(source, "Unsupported NIST regression expression")
        # General source reports with clear labels, preserving reported versus
        # exact and approximate relationships instead of silently equating them.
        # Only a complete field-label line is a positive report. An embedded
        # substring in negated, quoted or qualified prose does not establish
        # what the authors assert. Such prose remains unsupported.
        report = re.fullmatch(r"\s*(?P<label>Iterations|Function evaluations|Current function value|mean|standard deviation|minimum value)\s*(?::|=|\bis\b)\s*(?P<approx>approximately\s+|about\s+|≈\s*|~\s*)?(?P<value>"+NUMBER+r")\s*[.;]?\s*", line, re.I)
        if report and not nist:
            label = re.sub(r"\s+", "_", report["label"].lower())
            unit = "count" if label in {"iterations", "function_evaluations"} else None
            project.claim(source, entity=label, value=report["value"], quantity_role=label,
                          relation="reported_approximate_value" if report["approx"] else "reported_value", unit=unit, evidence_kind="author_report",
                          conditions={"scope":"Specific quoted source report; other runs are not implied"})
        # Only explicitly delimited inline/display equations enter the arithmetic
        # parser. Ambiguous prose and malformed LaTeX remain unsupported.
        for match in re.finditer(r":math:`([^`]+)`|\$([^$\n]+)\$", line):
            expression = next(x for x in match.groups() if x is not None)
            if "=" not in expression or re.search(r"≈|<=|>=|!=|\\approx|==", expression):
                continue
            lhs_text, rhs_text = expression.split("=", 1)
            try:
                lhs = previous.parse_expression(previous._latex_arithmetic(lhs_text))
                rhs = previous.parse_expression(previous._latex_arithmetic(rhs_text))
                entity = lhs.get("name") if lhs.get("op") == "symbol" else previous.render_expression(lhs)
                project.claim(source, kind="equation", entity=entity, lhs=lhs, rhs=rhs, quantity_role="document_equation", relation="equation", symbols=sorted(set(_symbols(lhs)+_symbols(rhs))), domain={"number_system":"unspecified", "required_nonzero":_denominators(lhs)+_denominators(rhs)}, evidence_kind="source_declaration")
            except previous.Unsupported:
                project.unresolved(source, "Unsupported or ambiguous mathematical notation")


def _python(project, artifact, text):
    try:
        tree = ast.parse(text, mode="exec")
        previous._tree_bound(tree)
    except (SyntaxError, previous.Unsupported, RecursionError):
        project.unresolved(project.evidence(artifact,text,0,min(len(text),8192)), "Invalid or excessive Python syntax")
        return
    lines = text.splitlines(keepends=True)
    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1]+len(line))
    def source(node):
        return project.evidence(artifact,text,offsets[node.lineno-1],offsets[node.end_lineno],python_node=type(node).__name__)
    def scope_name(node, current="module"):
        for child in getattr(node, "body", []):
            if isinstance(child,(ast.FunctionDef, ast.AsyncFunctionDef)):
                name = current + "/" + child.name
                args = [a.arg for a in child.args.posonlyargs+child.args.args+child.args.kwonlyargs]
                for arg in args:
                    project.add("symbols", {"symbol":arg,"scope":name,"role":"function_argument","source":source(child)})
                for statement in child.body:
                    if isinstance(statement,ast.Return) and statement.value is not None:
                        try:
                            rhs = previous._ast_ir(statement.value,text)
                            project.claim(source(statement),entity=child.name,kind="equation",quantity_role="function_return",relation="equation",lhs={"op":"function","name":child.name,"args":[{"op":"symbol","name":a} for a in args]},rhs=rhs,symbols=_symbols(rhs),scope=name,conditions={"scope":"Direct unconditional source return; no implementation execution or equivalence proof"},domain={"number_system":"unspecified","required_nonzero":_denominators(rhs)})
                        except previous.Unsupported:
                            pass
                scope_name(child,name)
            elif isinstance(child,ast.Assign) and len(child.targets)==1 and isinstance(child.targets[0],ast.Name):
                try:
                    ir=previous._ast_ir(child.value,text)
                    if ir.get("op")=="number" or ir.get("op")=="neg" and ir["arg"].get("op")=="number":
                        value=ir["value"] if ir["op"]=="number" else "-"+ir["arg"]["value"]
                        project.claim(source(child),entity=child.targets[0].id,value=value,quantity_role="source_literal",relation="declared_value",scope=current,conditions={"scope":"Static source assignment; reachability and later mutation not established"})
                except previous.Unsupported:
                    pass
    scope_name(tree)


def interpret_project(project_dir):
    """Return source-bound, untrusted typed interpretations of a project directory.

    ``claims`` use case-sensitive entity identifiers, relation declared_value /
    reported_value / equation / structural_count, explicit quantity_role,
    source-literal units (null means unspecified), optional exact_value,
    rhs/lhs arithmetic IR, resolved symbol bindings, domains and review obligations.
    Paths are relative to the supplied project root. Every source quote has exact
    UTF-8 byte offsets and SHA256. Unknown binary formats remain inventoried.
    """
    project = _Project()
    for path, raw in _read_project(project_dir):
        sha = hashlib.sha256(raw).hexdigest()
        artifact = {"path":path,"sha256":sha,"size":len(raw),"id":"artifact-"+digest([path,sha])[:24]}
        project.raw[path]=raw
        project.result["artifacts"].append(artifact)
        try:
            text=raw.decode("utf-8",errors="strict")
            if "\x00" in text:
                raise UnicodeError("NUL byte")
        except UnicodeError:
            project.unresolved({"path":path,"sha256":sha,"artifact_id":artifact["id"],"quote":"","byte_start":0,"byte_end":0,"locator":{}},"No supported strict-UTF8 textual semantic interpretation")
            continue
        suffix=Path(path).suffix.lower()
        if suffix in {".xml",".sbml"}:
            _sbml(project,artifact,text)
        elif suffix in TEXT_SUFFIXES:
            _text(project,artifact,text)
        elif suffix==".py":
            _python(project,artifact,text)
        else:
            project.unresolved(project.evidence(artifact,text,0,min(len(text),8192)),"No semantic adapter for this file format")
    project.result["summary"]={key:len(project.result[key]) for key in ("artifacts","claims","symbols","dependencies","obligations","unresolved")}
    project.result["context_sha256"]=digest({"version":VERSION,"source":Path(__file__).read_text()})
    return project.result


def verify_grounding(claim, project_dir):
    """Independently re-read exact bytes for a claim's source binding."""
    source=claim["source"]
    files=dict(_read_project(project_dir))
    raw=files.get(source["path"])
    if raw is None or hashlib.sha256(raw).hexdigest()!=source["sha256"]:
        return False
    a,b=source.get("byte_start"),source.get("byte_end")
    return type(a) is int and type(b) is int and 0<=a<b<=len(raw) and raw[a:b]==source["quote"].encode("utf-8")


def compare_expressions(left,right):
    """Exact rational-function comparison only; scientific meanings stay separate."""
    result=rational_equivalence.compare(left,right)
    return {"algebra":result,"scientific_equivalence":"NOT_ESTABLISHED",
            "domain_conditions":{"left":_denominators(left),"right":_denominators(right)},
            "authority":False}
