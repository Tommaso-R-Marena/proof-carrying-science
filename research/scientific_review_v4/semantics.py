"""Additive v4 scientific interpretation; declarations never certify truth.

The v3 parsers remain unchanged. This sidecar normalizes exposed schema gaps,
adds bounded, qualified source reports, and inventories all admitted bytes.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import os
from pathlib import Path
import re
import xml.etree.ElementTree as ET

from research.scientific_intake_v1 import intake
from research.scientific_semantics_v3 import semantics as parent

VERSION = "scientific-review/v4.0"
MAX_FILE = parent.MAX_FILE  # interpretation budget, not intake inventory budget
MAX_FILES = intake.MAX_FILES
MAX_TOTAL = intake.MAX_TOTAL
canonical_bytes = parent.canonical_bytes
digest = parent.digest
exact_number = parent.exact_number
parse_statistical_expression = parent.parse_statistical_expression
compare_expressions = parent.compare_expressions
CATEGORIES = ("artifacts", "claims", "symbols", "dependencies", "obligations", "unresolved")
XHTML = "http://www.w3.org/1999/xhtml"
JATS_NAMESPACES = {"", "http://jats.nlm.nih.gov", "http://www.ncbi.nlm.nih.gov/JATS1"}


class _Project(parent._Project):
    def claim(self, source, **values):
        if not source.get("quote") or source.get("byte_start", 0) >= source.get("byte_end", 0):
            raise ValueError("claims require nonempty original source evidence")
        return super().claim(source, **values)


def _span(source, start, end, *, transformation=None):
    """A subspan of an already byte-bound original quote (character indices)."""
    out = deepcopy(source)
    quote = source["quote"]
    out["byte_start"] += len(quote[:start].encode("utf-8"))
    out["byte_end"] = out["byte_start"] + len(quote[start:end].encode("utf-8"))
    out["quote"] = quote[start:end]
    if transformation:
        out["transformation"] = transformation
    return out


def _attribute(source, name):
    match = re.search(r"\b" + re.escape(name) + r"\s*=\s*(['\"])(.*?)\1", source["quote"], re.S)
    return _span(source, match.start(), match.end()) if match else deepcopy(source)


def _normalize_claim(claim):
    """Source-backed field placement; no source or parent record is rewritten."""
    evidence = claim.setdefault("field_evidence", {})
    source = claim["source"]
    for field in ("kind", "entity", "subject", "relation", "quantity_role", "value", "unit", "conditions", "rhs", "lhs", "scope", "assumptions"):
        if field in claim:
            evidence.setdefault(field, deepcopy(source))
    conditions = claim.get("conditions")
    if not isinstance(conditions, dict):
        return
    declarations = claim.get("declarations", {})
    if "hasOnlySubstanceUnits" in declarations:
        literal = declarations["hasOnlySubstanceUnits"]
        conditions["hasOnlySubstanceUnits"] = literal in {"true", "1"}
        evidence["conditions.hasOnlySubstanceUnits"] = _attribute(source, "hasOnlySubstanceUnits")
    role_to_tag = {"assignment_rule": "assignmentRule", "rate_rule": "rateRule", "initial_assignment": "initialAssignment", "algebraic_rule": "algebraicRule"}
    if claim.get("quantity_role") in role_to_tag:
        tag = role_to_tag[claim["quantity_role"]]
        conditions["rule_type"] = tag
        evidence["conditions.rule_type"] = deepcopy(source)
    terms = claim.get("terms", claim.get("unit_resolution", {}).get("terms", []))
    if claim.get("kind") == "unit_definition" and len(terms) == 1:
        for field in ("multiplier", "scale", "exponent"):
            conditions[field] = str(terms[0][field])
            ev = _attribute(source, field)
            if ev["quote"] == source["quote"]:
                ev["transformation"] = "SBML specification default retained from v3 unit term; not an explicit attribute"
            evidence["conditions." + field] = ev


# Closed active-voice report fragment. Larger noun phrases are deliberately
# bounded, and no relation is inferred from role names such as 'inhibitor'.
_RELATION = re.compile(
    r"^(?P<subject>[A-Za-z][A-Za-z0-9_+() /\-]{0,119}?)\s+"
    r"(?:(?P<modal>may|might|can|could|would|should)\s+)?"
    r"(?:(?P<aux>does|do|did)\s+)?(?P<neg>not\s+|never\s+)?"
    r"(?P<verb>inhibits?|repress(?:es)?|activates?|stimulates?)\s+"
    r"(?P<object>[A-Za-z][A-Za-z0-9_+() /\-]{0,159}?)"
    r"(?:\s+(?P<condition>when\b.{1,180}|under\b.{1,180}|if\b.{1,180}|in\s+the\s+presence\s+of\b.{1,180}))?[.!;]?$",
    re.I,
)
_INSTRUCTION = re.compile(r"\b(ignore (?:all |the )?(?:previous|prior) instructions?|system prompt|developer message|you are (?:an? |the )?(?:assistant|reviewer)|(?:set|grant|return) authority\s*(?:=|to)?\s*true)\b", re.I)
_VERBS = {"inhibit": "inhibits", "inhibits": "inhibits", "repress": "represses", "represses": "represses", "activate": "activates", "activates": "activates", "stimulate": "stimulates", "stimulates": "stimulates"}
_ROLE_MAPPED = re.compile(
    r"^(?:In this system,\s*)?(?P<protein>[A-Za-z][A-Za-z0-9_-]*)\s+"
    r"\(variable\s+(?P<mrna>[A-Za-z][A-Za-z0-9_]*)\s+is the mRNA,\s*"
    r"variable\s+(?P<protein_var>[A-Za-z][A-Za-z0-9_]*)\s+is the protein\)\s+"
    r"(?:(?P<modal>may|might|can|could|would|should)\s+)?"
    r"(?:(?:does|do|did)\s+)?(?P<neg>not\s+|never\s+)?"
    r"(?P<verb>inhibits?|repress(?:es)?|activates?|stimulates?)\s+"
    r"(?:the\s+)?(?:[A-Za-z][A-Za-z0-9_-]*\s+){0,5}"
    r"(?P<gene>[A-Za-z][A-Za-z0-9_-]*)\s+"
    r"\((?P<target_mrna>[A-Za-z][A-Za-z0-9_]*),\s*"
    r"(?P<target_protein>[A-Za-z][A-Za-z0-9_]*)\s+describe mRNA and protein\)"
    r"(?:\s+(?P<condition>when\b.{1,180}|under\b.{1,180}|if\b.{1,180}))?[.!;]?$",
    re.I,
)
_PASSIVE = re.compile(
    r"^(?:(?P<attribution>We conclude that|We report that|The authors conclude that)\s+)?"
    r"(?P<target>[A-Za-z][A-Za-z0-9_+() /\-]{0,119}?)\s+"
    r"(?:(?P<modal>may|might|can|could|would|should)\s+(?P<modal_neg>not\s+)?be|is|are|was|were)\s+"
    r"(?P<neg>not\s+|never\s+)?(?P<verb>inhibited|repressed|activated|stimulated)\s+by\s+"
    r"(?P<agent>[A-Za-z][A-Za-z0-9_+() /\-]{0,119}?)"
    r"(?:\s+(?P<condition>during\b.{1,180}|when\b.{1,180}|under\b.{1,180}|if\b.{1,180}|in\s+the\s+presence\s+of\b.{1,180}))?[.!;]?$",
    re.I,
)
_PASSIVE_VERBS = {"inhibited": "inhibits", "repressed": "represses", "activated": "activates", "stimulated": "stimulates"}
_AUTHOR_ASSUMPTION = re.compile(
    r"^(?P<preamble>For [A-Za-z][A-Za-z -]{0,79},\s*|Here,\s*)?"
    r"(?P<speaker>we|the authors)\s+"
    r"(?:(?P<modal>may|might|can|could|would|should)\s+)?"
    r"(?:(?:do|did)\s+)?(?P<neg>not\s+|never\s+)?assume\s+"
    r"(?:that\s+)?(?P<proposition>[^;!?]{1,450}?)[.]?$", re.I,
)
_CONDITIONAL_ASSUMPTION = re.compile(
    r"^(?P<marker>Assuming(?:\s+that)?|Under (?:the )?assumption that)\s+"
    r"(?P<proposition>[^,;.!?]{1,300}),\s*(?P<consequence>[^;!?]{1,450}?)[.]?$", re.I,
)


def _explicit_assumption(project, source, sentence, scope):
    """Retain explicitly adopted/declined premises without asserting validity."""
    match = _AUTHOR_ASSUMPTION.fullmatch(sentence)
    conditions = {"negated": False, "modality": "asserted"}
    if match:
        proposition = match["proposition"].strip()
        conditions.update(attribution=match["speaker"], negated=bool(match["neg"]),
                          modality=(match["modal"] or "asserted").lower(),
                          source_form="explicit_author_assumption")
        if match["preamble"]:
            conditions["context"] = match["preamble"].strip().rstrip(",")
    else:
        match = _CONDITIONAL_ASSUMPTION.fullmatch(sentence)
        if not match:
            return False
        proposition = match["proposition"].strip()
        # A comma inside a noun list or an open parenthesis does not provide an
        # unambiguous assumption/consequence boundary for this small grammar.
        if (proposition.count("(") != proposition.count(")")
                or proposition.count("[") != proposition.count("]")
                or re.match(r"(?:and|or|but)\b", match["consequence"], re.I)):
            return False
        conditions.update(source_form=match["marker"], consequence_context=match["consequence"].strip())
    if not proposition or re.search(r"\b(?:assume|assuming)\b", proposition, re.I):
        return False
    # These are lexical disclosures, not a logical analysis of proposition
    # scope. The full proposition is always retained verbatim after whitespace
    # normalization, so nested modality and negation are never discarded.
    conditions["proposition_has_explicit_negation"] = bool(re.search(r"\b(?:not|never|no|without)\b", proposition, re.I))
    conditions["proposition_modal_terms"] = sorted(set(re.findall(r"\b(?:may|might|can|could|would|should|must)\b", proposition.lower())))
    claim = project.claim(source, kind="scientific_claim", entity="source_assumption",
                          relation="assumes", value=proposition, quantity_role="scientific_assumption",
                          conditions=conditions, scope=scope, assumption_status="OPEN",
                          evidence_kind="explicit_author_assumption", source_statement=sentence,
                          assumptions=["Explicit source assumption only; its adoption, applicability and scientific validity require review"])
    project.add("obligations", {"kind": "scientific_assumption_review", "claim_id": claim["id"],
                               "status": "OPEN", "source": source,
                               "reason": "Source wording does not establish that this premise holds in the intended application"})
    return True


def _prose(project, source, plain, *, scope="source_report"):
    """Interpret exact explicit reports while retaining all relevant qualifiers."""
    if _INSTRUCTION.search(plain):
        project.unresolved(source, "Instruction-like source prose remains untrusted data; no biological relation interpreted")
        return
    # Each sentence is a complete bounded fragment. Quotes and colon-prefixed
    # purported instructions cannot authorize a scientific relation.
    sentences = re.split(r"(?<=[.!?;])\s+|\n+", plain.strip())
    for sentence in sentences:
        clean = " ".join(sentence.split())
        if len(clean) > 500:
            continue
        if _explicit_assumption(project, source, clean, scope):
            continue
        passive = _PASSIVE.fullmatch(clean)
        if passive:
            if re.search(r"\b(?:not|never|that|probably|likely|possibly|claim|report|reviewer|instruction)\b", passive["target"], re.I):
                continue
            if re.search(r"\b(?:but|nor|neither|or|not|never)\b", passive["agent"], re.I):
                continue
            conditions = {"negated": bool(passive["neg"] or passive["modal_neg"]),
                          "modality": (passive["modal"] or "asserted").lower(),
                          "source_voice": "passive"}
            if passive["condition"]:
                conditions["qualifier"] = passive["condition"].strip()
            if passive["attribution"]:
                conditions["attribution"] = passive["attribution"]
            project.claim(source, kind="scientific_claim", entity=passive["agent"].strip(),
                          relation=_PASSIVE_VERBS[passive["verb"].lower()], value=passive["target"].strip(),
                          object=passive["target"].strip(), quantity_role="biological_relation",
                          conditions=conditions, scope=scope, evidence_kind="author_inference" if passive["attribution"] else "author_report",
                          source_statement=clean,
                          assumptions=["Passive source report normalized to agent and target; author inference does not establish causal truth or experimental validity"])
            continue
        mapped = _ROLE_MAPPED.fullmatch(clean)
        if mapped:
            relation = _VERBS[mapped["verb"].lower()]
            conditions = {"source_protein": mapped["protein"], "target_gene": mapped["gene"],
                          "negated": bool(mapped["neg"]), "modality": (mapped["modal"] or "asserted").lower()}
            if mapped["condition"]:
                conditions["qualifier"] = mapped["condition"].strip()
            project.claim(source, kind="interaction", entity=mapped["protein_var"],
                          relation=relation, value=mapped["target_mrna"], object=mapped["target_mrna"],
                          quantity_role="transcriptional_repression" if relation in {"inhibits", "represses"} else "transcriptional_activation",
                          conditions=conditions, scope="biological_model", evidence_kind="author_report",
                          source_statement=clean,
                          explicit_role_bindings={"source_mrna": mapped["mrna"], "source_protein": mapped["protein_var"],
                                                  "target_mrna": mapped["target_mrna"], "target_protein": mapped["target_protein"]},
                          assumptions=["Source explicitly identifies the protein and mRNA variables; relation is an author report, not measured causal truth"])
            continue
        match = _RELATION.fullmatch(clean)
        if not match:
            continue
        subject, target = match["subject"].strip(), match["object"].strip()
        if re.search(r"\b(?:report|claim|instruction|assistant|reviewer|sentence|statement|not|never|that|is|probably|likely|possibly)\b", subject, re.I):
            continue
        if re.search(r"\b(?:but|nor|neither|or|not|never)\b", target, re.I):
            continue
        conditions = {"negated": bool(match["neg"]), "modality": (match["modal"] or "asserted").lower()}
        if match["condition"]:
            conditions["qualifier"] = match["condition"].strip()
        project.claim(source, kind="scientific_claim", entity=subject, subject=subject,
                      relation=_VERBS[match["verb"].lower()], value=target, object=target,
                      quantity_role="biological_relation", conditions=conditions,
                      scope=scope, evidence_kind="author_report", source_statement=clean,
                      assumptions=["Explicit source report only; causal truth, experimental validity, mechanism and generality are not established"])


def _text(project, artifact, text):
    parent._text(project, artifact, text)
    nist = bool(re.search(r"NIST|Statistical Reference Datasets|Certified Values", text, re.I))
    offset = 0
    for line in text.splitlines(keepends=True):
        source = project.evidence(artifact, text, offset, offset + len(line))
        offset += len(line)
        if nist:
            variable = re.search(r"\b(?P<role>Predictor|Response)\s+Variable\s*\(\s*(?P<symbol>[A-Za-z][A-Za-z0-9_]*)\s*=\s*(?P<name>[A-Za-z ]+?)(?:,\s*(?P<unit>degrees kelvin|kelvin|degrees Celsius|degree Celsius))?\s*\)", line, re.I)
            if variable:
                literal = variable["unit"]
                unit = {"degrees kelvin": "K", "kelvin": "K", "degrees celsius": "degC", "degree celsius": "degC"}.get(literal.lower()) if literal else None
                project.claim(source, entity=variable["symbol"], kind="variable_definition", relation="defined_as", value=variable["name"].strip(), quantity_role=variable["role"].lower(), unit=unit, source_unit_literal=literal, unit_resolution=parent._unit_record(unit, {}), scope="model")
        elif line.strip():
            _prose(project, source, line)


def _xml(project, artifact, text):
    source = project.evidence(artifact, text, 0, min(len(text), 8192))
    try:
        if re.search(r"<!\s*(?:DOCTYPE|ENTITY)\b", text, re.I):
            raise ValueError("XML DTDs/entities are forbidden")
        spans = parent.previous._xml_spans(text)
        root = ET.fromstring(text)
        elements = list(root.iter())
        if len(spans) != len(elements):
            raise ValueError("XML lexical binding mismatch")
        local, namespace = parent._local(root), parent._namespace(root)
        sbml = local == "sbml"
        if sbml:
            before = {key: len(project.result[key]) for key in CATEGORIES if key != "artifacts"}
            parent._sbml(project, artifact, text)
            rejected = any(row["reason"].startswith("SBML interpretation rejected:") for row in project.result["unresolved"][before["unresolved"]:])
            if rejected:
                # An invalid structural source cannot retain claims emitted
                # before a later model-closure defect was detected.
                for key in ("claims", "symbols", "dependencies", "obligations"):
                    del project.result[key][before[key]:]
                return
        elif local != "article" or namespace not in JATS_NAMESPACES:
            raise ValueError("No semantic adapter for this XML root/namespace")
        for node, (start, end) in zip(elements, spans):
            if parent._local(node) != "p":
                continue
            if sbml and parent._namespace(node) != XHTML:
                continue
            if not sbml and parent._namespace(node) != namespace:
                continue
            original = project.evidence(artifact, text, start, end, xml_element="p")
            plain = "".join(node.itertext())
            original["transformation"] = "XML paragraph itertext; markup stripped and XML character references decoded for matching; quote and offsets remain original bytes"
            _prose(project, original, plain, scope="publication_report" if not sbml else "model_notes")
    except (ValueError, parent.previous.Unsupported, ET.ParseError, RecursionError, MemoryError) as exc:
        project.unresolved(source, "XML interpretation rejected: " + str(exc)[:240])


def _new_ids(result):
    """Preserve origin IDs and change every internal reference consistently."""
    mapping = {}
    for category in CATEGORIES:
        for row in result[category]:
            old = row["id"]
            row["origin_id"] = old
            row["id"] = category.rstrip("s") + "-v4-" + digest([VERSION, category, row])[:24]
            mapping[old] = row["id"]
    def remap(value, key=None):
        if isinstance(value, dict):
            return {k: v if k == "origin_id" else remap(v, k) for k, v in value.items()}
        if isinstance(value, list):
            return [remap(v, key) for v in value]
        if isinstance(value, str) and (key in {"artifact_id", "claim_id", "from_claim", "to_symbol", "symbol_id", "interpretation_id"}):
            return mapping.get(value, value)
        return value
    return remap(result)


def interpret_artifacts(artifacts):
    """Interpret a bounded ``dict[relative_path, bytes]`` without reopening it."""
    if not isinstance(artifacts, dict):
        raise TypeError("artifacts must be a path-to-bytes dictionary")
    if len(artifacts) > MAX_FILES:
        raise ValueError("project file-count bound")
    seen, total = set(), 0
    for path, raw in artifacts.items():
        name = intake.safe_name(path)
        if name in seen:
            raise ValueError("duplicate normalized source path")
        seen.add(name)
        if type(raw) is not bytes:
            raise TypeError("artifact content must be bytes")
        total += len(raw)
        if len(raw) > intake.MAX_FILE or total > MAX_TOTAL:
            raise ValueError("intake artifact resource bound")
    project = _Project()
    project.result["schema_version"] = VERSION
    project.result["parent_schema_version"] = parent.VERSION
    for path, raw in sorted(artifacts.items()):
        sha = hashlib.sha256(raw).hexdigest()
        artifact = {"path": path, "sha256": sha, "size": len(raw), "id": "artifact-" + digest([path, sha])[:24]}
        project.raw[path] = raw
        project.result["artifacts"].append(artifact)
        empty = {"path": path, "sha256": sha, "artifact_id": artifact["id"], "quote": "", "byte_start": 0, "byte_end": 0, "locator": {}}
        if len(raw) > MAX_FILE:
            project.unresolved(empty, "Artifact inventoried but exceeds the 1000000-byte semantic interpretation budget", size=len(raw), interpretation_limit=MAX_FILE)
            continue
        try:
            text = raw.decode("utf-8", errors="strict")
            if "\x00" in text:
                raise UnicodeError("NUL byte")
        except UnicodeError:
            project.unresolved(empty, "Artifact inventoried without a supported strict-UTF8 textual semantic interpretation")
            continue
        suffix = Path(path).suffix.lower()
        if suffix in {".xml", ".sbml", ".nxml"}:
            _xml(project, artifact, text)
        elif suffix in parent.TEXT_SUFFIXES:
            _text(project, artifact, text)
        elif suffix == ".py":
            parent._python(project, artifact, text)
        else:
            project.unresolved(project.evidence(artifact, text, 0, min(len(text), 8192)), "No semantic adapter for this file format")
    for claim in project.result["claims"]:
        _normalize_claim(claim)
    result = _new_ids(project.result)
    result["summary"] = {key: len(result[key]) for key in CATEGORIES}
    result["context_sha256"] = digest({"version": VERSION, "source": Path(__file__).read_text(), "parent_source": Path(parent.__file__).read_text()})
    return result


def _safe_walk(root):
    """Reuse v1 intake's descriptor-relative no-follow snapshot reader."""
    fd = os.open(Path(root), os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        files, total = {}, 0
        for path, raw, _ in intake._walk(fd):
            if len(files) >= MAX_FILES:
                raise ValueError("project file-count bound")
            total += len(raw)
            if total > MAX_TOTAL:
                raise ValueError("project total-byte bound")
            files[path] = raw
        return files
    finally:
        os.close(fd)


def interpret_project(root):
    """Snapshot via the v1 safe reader, then interpret the exact admitted bytes."""
    return interpret_artifacts(_safe_walk(root))


def verify_grounding(claim, project_dir):
    source = claim.get("source", {})
    files = _safe_walk(project_dir)
    raw = files.get(source.get("path"))
    if raw is None or hashlib.sha256(raw).hexdigest() != source.get("sha256"):
        return False
    start, end = source.get("byte_start"), source.get("byte_end")
    return type(start) is int and type(end) is int and 0 <= start < end <= len(raw) and raw[start:end] == source.get("quote", "").encode("utf-8")
