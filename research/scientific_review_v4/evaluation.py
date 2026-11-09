"""Evaluation-only conservative grading against independent frozen v4 probes.

No labels enter extraction or retrieval. Exact typed matching establishes a
selected source interpretation, never scientific truth or checker authority.
"""
from __future__ import annotations

from research.scientific_semantics_v3.evaluation import value_equal as _old_equal, adapt_v2
from research.scientific_understanding_v2.evaluation import canonical_expression
from research.scientific_understanding_v2.interpretation import parse_expression
from research.scientific_understanding_v2.rational_equivalence import compare
from .grounding import bound_source, same_source, source_key

VERSION = "scientific-review-grading-v4.0"
SUPPORTED_CHECK_STATUSES = frozenset({"SOURCE_DECLARATION_CHECKED", "SOURCE_REPORT_CHECKED", "SCOPED_EQUATION_CHECKED",
                                      "REPRODUCED_COMPUTATION", "REPRODUCED_ROUNDED_COMPUTATION", "KERNEL_CHECKED_ABSTRACT_RESIDUAL_SEMANTICS"})


def value_equal(actual, expected, tolerance=0):
    """Exact rational numbers, recursively typed containers, or literal text.

    The historical tolerance argument is accepted only at zero: rounding checks
    are separate computations and cannot silently relax source interpretation.
    """
    if tolerance != 0:
        return False
    if isinstance(expected, dict):
        return isinstance(actual, dict) and set(actual) == set(expected) and all(value_equal(actual[k], v) for k, v in expected.items())
    if expected is None:
        return actual is None
    return _old_equal(actual, expected, 0)


def scope(row):
    # Reaction scope is a distinct case-sensitive site. No identifier aliases.
    if row.get("reaction_scope"):
        return row["reaction_scope"]
    if row.get("scope") and row.get("scope") == row.get("model_id"):
        return "model"
    return row.get("scope", "model")


def equation_match(actual, expected):
    """Closed bounded AST syntax or exact rational equality on common domain.

    Calls outside the explicit arithmetic grammar, prose, matrices and implicit
    calculus remain unknown; identical unparsed strings earn no equation credit.
    """
    try:
        ca, cb = canonical_expression(actual), canonical_expression(expected)
        a = actual if isinstance(actual, dict) else parse_expression(actual.replace("^", "**"))
        b = expected if isinstance(expected, dict) else parse_expression(expected.replace("^", "**"))
        try:
            rational = compare(a, b)
        except (ValueError, KeyError, TypeError, RecursionError, OverflowError):
            rational = None
        if rational is not None:
            return {"matches": rational["status"] == "EQUAL_ON_COMMON_DEFINED_DOMAIN", "method": "rational_common_domain",
                    "domain_preservation": "OPEN", "scientific_meaning": "OPEN",
                    "nonzero_obligations": rational["nonzero_denominator_obligations"]}
        return {"matches": ca == cb, "method": "bounded_canonical_syntax", "domain_preservation": "OPEN", "scientific_meaning": "OPEN"}
    except (ValueError, KeyError, TypeError, AttributeError, RecursionError, SyntaxError, OverflowError):
        return {"matches": False, "method": "unsupported_or_different", "domain_preservation": "OPEN", "scientific_meaning": "OPEN"}


def _path_record(source, artifacts):
    try:
        key = source_key(source, artifacts)
        return {"asserted_path": source.get("path"), "canonical_path": key,
                "rule": "exact" if key == source.get("path") else "unambiguous_literal_suffix"}
    except (KeyError, TypeError):
        return {"asserted_path": source.get("path"), "canonical_path": None, "rule": "unresolved_or_ambiguous"}


def compare_candidate(candidate, reference, artifacts, inventory=None):
    expected = reference["typed_expectation"]
    reasons, missing = [], []
    grounded = same_source(candidate.get("source", {}), reference["source"], artifacts, inventory)
    if not grounded:
        reasons.append("source_binding_or_overlap")
    for field in ("kind", "entity", "relation"):
        if candidate.get(field) != expected.get(field):
            reasons.append(field)
    if scope(candidate) != expected.get("scope", "model"):
        reasons.append("scope")
    equation = None
    if "canonical_rhs" in expected or "rhs" in expected:
        equation = equation_match(candidate.get("canonical_rhs", candidate.get("rhs")), expected.get("canonical_rhs", expected.get("rhs")))
        if not equation["matches"]:
            reasons.append("equation_rhs")
        if "lhs" in expected:
            lhs = candidate.get("lhs")
            actual_lhs = lhs.get("name", lhs.get("reaction")) if isinstance(lhs, dict) else lhs
            if actual_lhs != expected["lhs"]:
                reasons.append("equation_lhs")
    elif "value" not in candidate or not value_equal(candidate["value"], expected.get("value")):
        reasons.append("value")
    if candidate.get("quantity_role") != expected.get("quantity_role"):
        missing.append("quantity_role")
    if "unit" not in candidate or candidate.get("unit") != expected.get("unit"):
        missing.append("explicit_unit")
    actual_conditions, expected_conditions = candidate.get("conditions"), expected.get("conditions", {})
    if isinstance(expected_conditions, dict):
        if not isinstance(actual_conditions, dict):
            missing.append("conditions")
        else:
            for key, value in expected_conditions.items():
                if key not in actual_conditions or not value_equal(actual_conditions[key], value):
                    missing.append("condition:" + key)
    elif not value_equal(actual_conditions, expected_conditions):
        missing.append("conditions")
    if "symbols" in expected:
        symbols = candidate.get("symbols")
        if not isinstance(symbols, list) or sorted(symbols) != sorted(expected["symbols"]):
            missing.append("symbols")
    if "domain" in expected and candidate.get("domain") != expected["domain"]:
        missing.append("domain")
    assumptions = reference.get("assumptions", [])
    absent = [a for a in assumptions if a not in candidate.get("assumptions", [])]
    return {"candidate_id": candidate.get("id"), "grounded": grounded, "core_match": not reasons,
            "typed_context_match": not reasons and not missing, "core_mismatches": reasons, "missing_context": missing,
            "equation": equation, "aliases_applied": [],
            "source_paths": {"candidate": _path_record(candidate.get("source", {}), artifacts), "reference": _path_record(reference["source"], artifacts)},
            "assumption_literal_total": len(assumptions), "assumption_literals_present": len(assumptions)-len(absent),
            "missing_assumption_literals": absent, "assumptions_status": "OPEN; wording is diagnostic, never semantic credit",
            "scientific_authority_granted": False}


def grade(references, interpretation, artifacts, checks=(), inventory=None):
    claims = interpretation.get("claims", [])
    outcomes, precision_pairs = [], []
    for ref in references:
        expected = ref["typed_expectation"]
        # Preserve negative matches at the typed entity site. Wrong roles/scopes
        # are visible but only annotated role/site pairs enter probe precision.
        candidates = [c for c in claims if c.get("entity") == expected.get("entity") and c.get("kind") == expected.get("kind")]
        comparisons = [compare_candidate(c, ref, artifacts, inventory) for c in candidates]
        core = any(x["core_match"] for x in comparisons)
        full = any(x["typed_context_match"] for x in comparisons)
        if ref["expected_status"] == "supported":
            precision_pairs.extend(x["typed_context_match"] for c, x in zip(candidates, comparisons)
                                   if x["grounded"] and scope(c) == expected.get("scope", "model") and c.get("quantity_role") == expected.get("quantity_role"))
        unit_expected = expected.get("unit") is not None
        outcomes.append({"reference_id": ref["id"], "expected_status": ref["expected_status"],
                         "verification_expectation": ref.get("verification_expectation"),
                         "core_found": core, "typed_context_found": full, "comparisons": comparisons,
                         "explicit_unit_annotated": unit_expected,
                         "explicit_unit_core_correct": unit_expected and any(x["core_match"] and "explicit_unit" not in x["missing_context"] for x in comparisons),
                         "reference_source_bound": bound_source(ref["source"], artifacts, inventory),
                         "scientific_authority_granted": False})
    supported = [x for x in outcomes if x["expected_status"] == "supported"]
    counter = [x for x in outcomes if x["expected_status"] != "supported"]
    promotions = sum(c.get("authority") is not False or c.get("meaning_status") in {"CERTIFIED", "VERIFIED_SCIENTIFIC_MEANING", "SCIENTIFICALLY_VERIFIED"}
                     or c.get("scientific_meaning", "OPEN") != "OPEN" for c in claims)
    promotions += sum(c.get("authority") is not False or c.get("scientific_meaning", "OPEN") != "OPEN" for c in checks)
    return {"protocol": VERSION, "supported_total": len(supported), "core_found": sum(x["core_found"] for x in supported),
            "typed_context_found": sum(x["typed_context_found"] for x in supported),
            "core_recall": sum(x["core_found"] for x in supported)/len(supported) if supported else None,
            "typed_context_recall": sum(x["typed_context_found"] for x in supported)/len(supported) if supported else None,
            "annotated_probe_pairs": len(precision_pairs), "typed_correct_probe_pairs": sum(precision_pairs),
            "annotated_probe_precision": sum(precision_pairs)/len(precision_pairs) if precision_pairs else None,
            "counterprobes": len(counter), "counterprobe_core_proposals": sum(x["core_found"] for x in counter),
            "counterprobe_full_context_proposals": sum(x["typed_context_found"] for x in counter),
            "correct_counterprobe_abstentions": sum(not x["core_found"] for x in counter),
            "counterprobe_abstention_interpretation": "No matching proposal only; neither demonstrated refutation nor informative workflow answer",
            "unsupported_promotions": promotions, "unsupported_authority_count": promotions,
            "claims_generated": len(claims), "unannotated_candidates_are_not_scored": True,
            "explicit_unit_supported_probes": sum(x["explicit_unit_annotated"] for x in supported),
            "explicit_unit_core_correct_probes": sum(x["explicit_unit_core_correct"] for x in supported),
            "source_binding_failures": sum(not bound_source(c.get("source", {}), artifacts, inventory) for c in claims),
            "reference_binding_failures": sum(not x["reference_source_bound"] for x in outcomes),
            "assumption_measure": "Literal wording diagnostic only; scientific assumptions remain OPEN",
            "scientific_meaning_certified": 0, "authority": False, "outcomes": outcomes}


def grade_workflow(rubric, references, grading, interpretation, checks=(), *, answers=None):
    """Score explicit task answers; absent/generic UNKNOWN never earns utility.

    An answer binds task_id, annotation_ids, answer supported|unknown, and a
    check_scopes mapping. Supported scopes name actual check_ids; unknown scopes
    give an explicit nonempty reason. Source interpretation coverage is required
    in either case. This grading operation does not manufacture task answers.
    """
    answers = interpretation.get("workflow_answers", []) if answers is None else answers
    refmap = {r["id"]: r for r in references}
    outcomes = {x["reference_id"]: x for x in grading["outcomes"]}
    checkmap = {c.get("id"): c for c in checks}
    rows = []
    for task in rubric:
        matched = [a for a in answers if a.get("task_id", a.get("id")) == task["id"]]
        evaluations = []
        for answer in matched:
            ids = set(answer.get("annotation_ids", []))
            required = task["required_annotation_ids"]
            evidence = all(rid in ids and rid in outcomes and
                           (outcomes[rid]["typed_context_found"] if refmap[rid]["expected_status"] == "supported" else
                            not outcomes[rid]["core_found"] and rid in set(answer.get("counterprobe_annotation_ids", []))) for rid in required)
            scopes = answer.get("check_scopes", {})
            scope_rows = []
            for name in task["required_check_scopes"]:
                slot = scopes.get(name, {}) if isinstance(scopes, dict) else {}
                status = str(slot.get("status", "")).lower()
                receipts = [checkmap.get(cid) for cid in slot.get("check_ids", [])]
                # A check must explicitly declare that exact scope and bind the
                # relevant task claims; its status alone cannot broaden scope.
                valid = bool(receipts) and all(c is not None and c.get("authority") is False and c.get("scientific_meaning", "OPEN") == "OPEN"
                    and name in c.get("check_scopes", []) and set(required).issubset(set(c.get("annotation_ids", [])))
                    and c.get("status") in SUPPORTED_CHECK_STATUSES for c in receipts)
                unknown = status == "unknown" and isinstance(slot.get("reason"), str) and bool(slot["reason"].strip())
                scope_rows.append({"scope": name, "supported": status == "supported" and valid, "explicit_unknown": unknown})
            answer_status = str(answer.get("answer", answer.get("status", ""))).lower()
            informative = isinstance(answer.get("reason"), str) and bool(answer["reason"].strip())
            supported = evidence and answer_status == "supported" and all(s["supported"] for s in scope_rows)
            abstention = evidence and answer_status == "unknown" and informative and all(s["supported"] or s["explicit_unknown"] for s in scope_rows) and any(s["explicit_unknown"] for s in scope_rows)
            correct = supported if task["expected_answer"] == "supported" else abstention
            evaluations.append({"evidence_coverage": evidence, "scope_outcomes": scope_rows, "answer_status": answer_status,
                                "supported_answer": supported, "informative_abstention": abstention, "correct": correct})
        rows.append({"task_id": task["id"], "question": task["question"], "expected_answer": task["expected_answer"],
                     "required_annotation_ids": task["required_annotation_ids"], "required_check_scopes": task["required_check_scopes"],
                     "matched_answers": len(matched), "correct": any(x["correct"] for x in evaluations),
                     "correct_abstention": task["expected_answer"] == "unknown" and any(x["correct"] for x in evaluations), "evaluations": evaluations})
    return {"tasks": len(rows), "correct": sum(r["correct"] for r in rows),
            "correct_informative_abstentions": sum(r["correct_abstention"] for r in rows),
            "utility": sum(r["correct"] for r in rows)/len(rows) if rows else None,
            "unmatched_unknown_is_correct": False, "authority": False, "outcomes": rows}
