"""Reproduce, then diagnose every supported PR #202 primary reference probe.

This is post-hoc diagnostic tooling, not an extractor, a replacement grader or
a new evaluation. It reads only the exposed v2 corpus and frozen predictions.
Manual adjudications are AI-assisted internal review, not expert validation.
No new prospective source, model, annotation, or output is consulted.
"""
from __future__ import annotations

import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import tempfile
import zipfile

from research.scientific_understanding_v2 import evaluation as frozen
from research.scientific_understanding_v2.interpretation import parse_expression
from research.scientific_understanding_v2.rational_equivalence import compare


ROOT = Path(__file__).resolve().parents[2]
OLD = ROOT / "research/scientific_understanding_v2"
HERE = Path(__file__).resolve().parent
OLD_HEAD = "b612d3d174793ac046b5c93282b24995acadffdb"
PRIMARY_SOURCE_COMMIT = "9e8a8f0"
FROZEN_INPUT_SHA256 = {
    "evaluation.py": "c1b4b51d3ddcdb4ab0127288fa640c1f00177a28f310b223661c57d1540e8597",
    "evidence/development-primary-packages.zip": "89f1efed04e8a5c198dd07f6ad137e0f3ab90932d73481a9761d246df010bf7e",
    "evidence/development-primary.json.gz": "2641b946b89783cfe71482cfe4df6f6365794df6fd2c97152d538a08c35d9a1b",
    "evidence/final-primary-packages.zip": "9e597cf308b9536aca2a5d48ff959666a36ec21e25305784be10b64d6102c30c",
    "evidence/final-primary.json.gz": "533582727df4340a850b367cd5593c8d789ca9df06c781c22e04d9a60a78387a",
    "reference/annotation_freeze.json": "b1806c9337e4882a40789faec817961d09c795cc99276e283f7735ac7d80ff8e",
    "reference/development.json": "4935b61a546ecdcd0fc13fe89e17cfde8cdaaffde79ce4d9eac9d681fb48c087",
    "reference/final.json": "3ef3eb8b6e557dc8a888329440289f4e47ffdc2ef4d28a6e9554fa1dc16f3773",
}


def _note(primary, tags, finding, next_check, abstention="avoidable_missing_capability"):
    return {"primary_failure_class": primary, "error_tags": tags.split(","),
            "internal_adjudication": finding, "next_required_check": next_check,
            "abstention_assessment": abstention}


# Reviewed against original quotes and the archived typed predictions. These
# classifications deliberately do not turn a partial interpretation into a
# passing reference label. The original frozen scores below are recomputed.
ADJUDICATIONS = {
    "tyson-init-cp": _note("matched", "none", "CP initialAmount=0.75 is an exact source-declaration match; unrelated declaration metadata is also targeted by the strict grader.", "No new interpretation check needed for the literal declaration.", "not_abstained"),
    "tyson-init-pm": _note("matched", "none", "pM initialAmount=0.25 is an exact source-declaration match. Case-sensitive identifier is preserved.", "No new interpretation check needed for the literal declaration.", "not_abstained"),
    "tyson-total-cdc2-definition": _note("matched", "none", "CT assignment and all four linear terms match exactly. This definition alone is not conservation.", "Keep a distinct conservation obligation.", "not_abstained"),
    "tyson-cdc2-conservation": _note("missing_derived_claim_link", "scientific_dependency_tracking,assumptions_conditions,identifier_resolution,evaluator_schema", "The interpretation contains CT's sum, while the separate model-assurance check already contains the exact nullspace vector [1,1,1,1,0,0] and initial total 1. No typed CT conservation claim links the two. The reference is reviewer-derived and explicitly outside the frozen inference fragment; a match would additionally encounter its unsupported balance slot.", "Bind CT's definition to the complete stoichiometric matrix, fixed compartment and initial state; preserve the real-trajectory/refinement obligations.", "justified_fragment_abstention_but_linkable_scoped_result"),
    "tyson-total-cyclin-definition": _note("matched", "none", "YT's four-term source definition matches. The model does not thereby conserve YT.", "Do not promote the sum definition to a conservation law.", "not_abstained"),
    "tyson-association-rate": _note("matched", "none", "Reaction4 expression and k3=200 are recovered. Parameter-only candidates are also targeted, inflating mismatching pair counts without representing distinct false scientific claims.", "Keep reaction-local parameter scope explicit.", "not_abstained"),
    "tyson-activation-rate": _note("matched", "none", "Reaction9 rational expression and both local parameters match; CT!=0 remains a separate condition.", "Do not infer nonzero CT solely from algebraic matching.", "not_abstained"),
    "tyson-zero-deactivation": _note("missing_derived_assertion", "numerical_relationship,scientific_dependency_tracking,assumptions_conditions,evaluator_schema", "The complete rate and k5notP=0 are present, but neither is typed as a derived flux=0 claim. The quantity name flux is absent; the reviewer-derived label would still require assumptions outside this grader's supported fragment.", "Perform exact scoped substitution and retain finite operands and model-closure assumptions.", "justified_fragment_abstention_but_simple_derivation_possible"),
    "tyson-biosynthesis-rate": _note("missing_dependency_assertion", "scientific_dependency_tracking,evaluator_schema", "The correct Reaction6 expression cell*k1aa and parameter0.015 are already extracted. Missing depends_on_Y=false blocks the conjunction; syntactic free-symbol absence must be distinguished from transitive model dependency.", "Resolve k1aa and cell definitions before certifying no transitive Y dependency.", "not_abstained_partial_proposal"),
    "tyson-dimension-feedback-ratio": _note("assumption_sensitive_missing_derivation", "units_dimensions,assumptions_conditions,missing_extraction", "M/CT exists as a subexpression in the rate, but there is no standalone conditional dimensional conclusion. Concentration dimensions are reviewer assumptions rather than source-declared physical units.", "Represent a conditional dimension theorem with explicit M and CT dimensions and CT!=0; do not infer physical units.", "correct_conservative_abstention_without_assumptions"),
    "tyson-dimension-feedback-coefficients": _note("assumption_sensitive_missing_derivation", "units_dimensions,assumptions_conditions,missing_extraction", "Numeric k4 and k4prime are present with unspecified units. No conditional inverse-time dimension inference is proposed; the reference has no explicit target entity or expression accepted by the frozen target matcher.", "Solve dimensional constraints conditional on a concentration-rate law and shared concentration dimensions, retaining the assumptions.", "correct_conservative_abstention_without_assumptions"),
    "tyson-dimension-association-coefficient": _note("assumption_sensitive_missing_derivation", "units_dimensions,assumptions_conditions", "k3=200 is correctly source-bound but has no declared physical unit; expected C^-1*T^-1 is a reviewer-derived consistency condition.", "Emit a conditional dimensional constraint, separate from declared units and empirical validity.", "correct_conservative_abstention_without_assumptions"),
    "dev-scipy-001": _note("mixed_relation_and_unit_gap", "evaluator_schema,units_dimensions,assumptions_conditions", "minimum_objective=0 is correctly recovered as reported_value. The frozen equality grader rejects that relation; the candidate also lacks the reference's dimensionless typing and a resolved definition of this function.", "Keep reported versus proved truth separate; bind the function definition and explicitly justify dimensionless coordinates/objective.", "correct_unit_abstention_with_avoidable_relation_mismatch"),
    "dev-scipy-002": _note("missing_extraction", "missing_extraction,numerical_relationship,source_grounding,assumptions_conditions", "The printed five-component res.x vector has no overlapping valid candidate; vectors printed after doctest expressions are not extracted. Printed ones are not an exact theorem about the floating-point optimizer.", "Link the output vector to its adjacent call and inputs, preserve printed precision and report status."),
    "dev-scipy-003": _note("reported_relation_grading_mismatch", "evaluator_schema", "339 iterations, count units, adjacent Nelder-Mead call and local solver arguments are already correct. reported_value is rejected as equality. A duplicated claim record yields another mismatching pair, not another scientific failure.", "Use separate relation and epistemic-status fields in a successor contract; retain reported-only status.", "not_abstained_correct_reported_literal"),
    "dev-scipy-004": _note("reported_relation_grading_mismatch", "evaluator_schema", "571 function evaluations and count units are already correct with the local solver call. The reported_value relation is not accepted as equals by the frozen grader.", "Separate literal equality from reported evidence status, without changing this frozen score.", "not_abstained_correct_reported_literal"),
    "dev-scipy-005": _note("missing_extraction", "missing_extraction,scientific_dependency_tracking,identifier_resolution", "The solver_context includes the complete options expression with xatol=1e-8, but no independent typed xatol quantity overlaps the probe. This is a missing extracted option, not an incorrect literal.", "Parse bounded literal option maps and link option meaning to the declared solver call; do not confuse local stopping tolerance with achieved global error."),
    "dev-scipy-006": _note("mixed_relation_and_unit_gap", "evaluator_schema,units_dimensions,assumptions_conditions", "reported_objective=1 and the adjacent rosen_with_args call including args=(.5,1.) are present. reported_value first fails equality; dimensionless unit semantics remain missing after that mismatch is removed.", "Bind objective definition and argument substitutions; retain six-decimal reporting tolerance and numerical reproduction status.", "correct_unit_abstention_with_avoidable_relation_mismatch"),
    "dev-scipy-007": _note("reported_relation_grading_mismatch", "evaluator_schema,uncertainty_scope", "25 iterations and count units with BFGS call, jac=rosen_der, may_vary=true and value_semantics=REPORTED are preserved in the quantity record. The grader rejects reported_value; its duplicate claim also omits value_semantics, causing a separate scope mismatch.", "Preserve epistemic/scope metadata across duplicate record projections; treat reported variability separately from numerical equality.", "not_abstained_correct_reported_literal"),
    "dev-scipy-010": _note("missing_extraction", "missing_extraction,identifier_resolution,equivalent_forms,scientific_dependency_tracking", "No candidate overlaps the der[-1] assignment. Return-expression extraction does not recover component assignments; mapping Python negative indices to N-1/N-2 requires an explicit N>=2 sequence context.", "Extract typed indexed assignments and independently establish index/domain correspondence before matching the mathematical gradient."),
    "dev-scipy-011": _note("missing_conditional_scientific_claim", "missing_extraction,assumptions_conditions,scientific_reference_resolution", "The positive-definite-Hessian conditional prose is not represented. No incorrect unconditional minimum claim was proposed.", "Extract the conditional statement and resolve this function to the local quadratic model; retain that local versus global scope."),
    "final-goldbeter-001": _note("identifier_and_model_unit_representation_mismatch", "identifier_resolution,evaluator_schema,units_dimensions", "C initialConcentration=0.01 and symbolic (substance)/(volume) units are present. Reference quantity initial_C has no shared typed slot with name C/role sbml_initialConcentration; encoded_concentration is a role label, not a physical unit synonym.", "Represent entity C, quantity-kind initial_concentration and declared versus inferred unit roles separately. Do not blindly alias scientific unit expressions.", "partial_representation_not_wrong_initial_value"),
    "final-goldbeter-002": _note("undeclared_unit_reference_mismatch", "units_dimensions,evaluator_schema", "VM1=3 is recovered exactly. Source declares no physical units and the candidate keeps unit=null; reference encoded_model_unit is an unspecified-role placeholder, not a source-declared unit.", "Use an explicit unspecified model-unit role in a successor contract while retaining unknown physical dimensions.", "correct_abstention_on_undeclared_physical_unit"),
    "final-goldbeter-003": _note("equivalent_form_grading_mismatch", "equivalent_forms,evaluator_schema,assumptions_conditions", "The exact source expression C*VM1*(C+Kc)^(-1) is recovered. The frozen matcher compares canonical syntax and does not reduce inverse powers to division. Independent rational normalization confirms equality on the common defined domain, retaining C+Kc!=0.", "Keep the same lhs/symbol identities and explicit nonzero-domain obligation; algebraic equality alone does not establish scientific meaning.", "not_abstained_correct_equivalent_expression"),
    "final-goldbeter-004": _note("matched", "none", "V3=M*VM3 matches the commutatively reordered reference VM3*M exactly under the frozen expression canon.", "Keep symbol scope and source identity unchanged.", "not_abstained"),
    "final-goldbeter-005": _note("assumed_unit_role_missing", "units_dimensions,assumptions_conditions,evaluator_schema", "vi=.025 is recovered exactly but units are unspecified. The reference's encoded_concentration_per_time is an inferred dynamical role and explicitly has no physical clock scale.", "Trace vi through the source reaction and fixed compartment into the concentration derivative; emit conditional role typing without inventing seconds.", "correct_conservative_abstention_on_inferred_unit_role"),
    "final-goldbeter-006": _note("missing_source_to_model_derivation", "missing_extraction,scientific_dependency_tracking,source_to_code,assumptions_conditions", "No candidate overlaps the Octave xdot(1) assignment. The requested expanded balance needs reaction substitution, species-index mapping, local parameter resolution and fixed nonzero volume; no wrong expanded balance was proposed.", "Build independently checked source-to-model dependency closure and prove exact rational correspondence, retaining denominator conditions."),
    "final-goldbeter-007": _note("missing_derived_numerical_claim", "missing_extraction,numerical_relationship,scientific_dependency_tracking,source_to_code,assumptions_conditions", "No typed initial dC/dt claim is emitted. Its value requires the complete balance, initial-state and scoped parameter substitutions; the primary model-assurance composite was UNKNOWN rather than a positive semantic verdict.", "Evaluate the grounded derivative exactly at the fully bound initial state and attach each source assumption; keep numerical and biological claims separate."),
    "final-goldbeter-009": _note("missing_conditional_scientific_claim", "missing_extraction,assumptions_conditions,scientific_synonyms,scientific_reference_resolution", "No valid bounded candidate covers the abstract's conditional limit-cycle sentence. Source-model parsing largely ignores notes/prose. The reference also uses a conditions slot not supported by the frozen semantic matcher, so extraction alone would not suffice.", "Extract attributed author-claim scope and both thresholds. A conditional abstract report is not an independent oscillation proof."),
    "final-goldbeter-011": _note("assumption_sensitive_missing_derivation", "units_dimensions,assumptions_conditions,evaluator_schema", "C+Kc is represented inside the V1 expression, but no same-dimension relation is generated. The reference uses quantities plus relation same_dimension, which the frozen target matcher cannot identify or grade.", "Generate a conditional homogeneity obligation for each addition and distinguish consistency requirements from measured/declared dimensions.", "justified_abstention_without_dimensional_constraint_language"),
    "final-goldbeter-012": _note("assumption_sensitive_missing_derivation", "units_dimensions,assumptions_conditions,evaluator_schema", "The 1-M subexpression is present. No dimensionless-M conclusion is emitted because the literal one's normalized-total meaning is an explicit scientific assumption. The reference's conditional_on field is outside the frozen matcher.", "Represent a conditional theorem with the normalized-total interpretation visible; never infer a physical fraction from encoded substanceUnits alone.", "correct_conservative_abstention_without_normalization_assumption"),
    "final-scipy-001": _note("missing_ode_semantic_link", "identifier_resolution,scientific_dependency_tracking,evaluator_schema,source_to_code", "func(t,y) returning [t*y[1],y[0]] is correctly extracted from the exact source span. The reference asks for component time derivatives, not a generic function return. No checked solve_ivp call-site, y-component convention or ODE-system interpretation connects them; list lhs/equivalent_system is also outside the frozen scalar matcher.", "Bind the function to the actual supported ODE call contract and component index map; do not equate arbitrary function outputs to derivatives.", "partial_expression_correct_but_scientific_role_unresolved"),
    "final-scipy-002": _note("missing_extraction", "missing_extraction,identifier_resolution,equivalent_forms,scientific_dependency_tracking", "The scalar y1_0 assignment is not extracted, and gamma is outside the small arithmetic callable fragment. y1_0 to y1(0) and Gamma/gamma spelling require imported-function and initialization-context resolution.", "Add safe symbolic special-function nodes and exact source binding; preserve fractional-power domains and do not execute uploaded callables."),
    "final-scipy-003": _note("missing_extraction", "missing_extraction,identifier_resolution,equivalent_forms,scientific_dependency_tracking", "The signed scalar y0_0 expression is not extracted. The missing semantic links mirror y1_0, with an additional explicit leading minus sign that must be preserved.", "Resolve the initial-state mapping and whitelisted gamma identity; compare the signed expression without floating-point-only equality."),
    "final-scipy-004": _note("missing_extraction", "missing_extraction,numerical_relationship,scientific_dependency_tracking", "t_span=[0,4] is not emitted as a typed interval quantity. No unsupported physical seconds were inferred, which is correct.", "Extract bounded literal lists with their call-site role and retain unspecified independent-variable units."),
    "final-scipy-005": _note("missing_extraction", "missing_extraction,scientific_dependency_tracking,evaluator_schema", "Tuple assignment rtol,atol=(1e-8,1e-8) and its call use are not represented as a mapping claim. The frozen matcher also lacks equals_mapping/dictionary numeric support.", "Track tuple destructuring and keyword dependencies; configured tolerances are not a global numerical-error certificate."),
    "final-scipy-006": _note("missing_extraction", "missing_extraction,numerical_relationship,scientific_dependency_tracking,source_grounding", "No source-bound result-array candidate covers sol1.y[1]'s printed endpoint. Mapping the last component to t=4 requires a time-grid/solution linkage, not selecting the last number from an arbitrary array.", "Parse printed bounded arrays and match the exact run/time grid, with printed precision and version context."),
    "final-scipy-007": _note("missing_extraction", "missing_extraction,numerical_relationship,scientific_dependency_tracking,source_grounding", "The printed airy(sol.t)[0] array is absent. Its final0.00095156 is a special-function reference on a linked grid, distinct from the numerical ODE output0.00405982.", "Resolve airy component, time-grid endpoint and reference/run identities; do not conflate approximate solver output with the analytic reference."),
    "final-scipy-009": _note("missing_negated_applicability_claim", "missing_extraction,assumptions_conditions,scientific_reference_resolution", "The source's RK45 Jacobian non-support statement is not extracted. No false support=true claim is proposed; absent extraction does not demonstrate correct understanding of the negation.", "Represent supported-operation capabilities with explicit polarity, method and version scope."),
    "final-scipy-011": _note("missing_extraction", "missing_extraction,numerical_relationship,scientific_dependency_tracking,source_grounding", "No candidate covers the Bessel quadrature result tuple. Its first component is an integral estimate and the second a reported error estimate, not another measurement or a formal global error bound.", "Bind the special.jv order, integration limits and result-tuple roles to an approved independent numerical reconstruction."),
    "final-scipy-013": _note("missing_conditional_scientific_claim", "missing_extraction,assumptions_conditions,scientific_reference_resolution", "The noncommutation prose is absent from typed candidates. Interpreting its condition requires resolving A(t) and its time integral in the nearby Airy system, not merely matching the word commute.", "Represent the exact matrix/time assumptions and independently compute a nonzero commutator witness where supported."),
}


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _candidate(record):
    keys = ("lhs", "rhs", "expression", "name", "role", "symbol", "scope", "relation", "value", "unit",
            "unit_status", "units_declared", "declared_unit", "value_semantics", "origin", "parse_status",
            "conditions", "solver_context", "reported_variability", "function", "arguments", "conditional",
            "unresolved_reason", "declarations", "kind", "meaning_status", "authority")
    return {"candidate_id": record["_id"], "category": record["_category"],
            "typed": {key: record[key] for key in keys if key in record}, "source": record.get("source")}


def _reference_spans(annotation, sources, inventory):
    """Exact normalized-whitespace source spans, never a semantic similarity."""
    import re
    source = annotation["source"]
    peers = [a for a in inventory["artifacts"] if a.get("sha256") == source["sha256"]
             and Path(a["path"]).name == Path(source["path"]).name]
    if not peers:
        return []
    text = sources.text({"path": peers[0]["path"], "sha256": source["sha256"], "artifact_id": peers[0]["id"]})
    if text is None:
        return []
    pattern = r"\s+".join(re.escape(part) for part in source["quote"].split())
    return [[m.start(), m.end()] for m in re.finditer(pattern, text)]


def _load_case(z, case_id, tmp):
    interpretation = json.loads(z.read(case_id + "/interpretations.json"))
    checks = json.loads(z.read(case_id + "/checks.json"))
    inventory = json.loads(z.read(case_id + "/intake/inventory.json"))
    for artifact in inventory["artifacts"]:
        digest = artifact["sha256"]
        if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise ValueError("invalid archived object digest")
        if artifact.get("object") != "objects/" + digest:
            raise ValueError("archived object identity differs")
        info = z.getinfo(case_id + "/intake/objects/" + digest)
        if info.file_size > 10 * 1024 * 1024:
            raise ValueError("archived object exceeds diagnostic bound")
        raw = z.read(info)
        if _sha(raw) != digest:
            raise ValueError("archived original digest differs")
        path = tmp / digest
        path.write_bytes(raw)
        artifact["snapshot_path"] = str(path)
    return interpretation, checks, inventory


def _diagnose_case(case, annotations, interpretation, checks, inventory):
    regenerated = frozen.grade_reference(annotations, interpretation, inventory, checks)
    if regenerated != case["reference"]:
        raise ValueError("archived primary grade did not reproduce exactly: " + case["id"])
    records = frozen._records(interpretation)
    byid = {r["_id"]: r for r in records}
    sources = frozen._Sources(inventory)
    supported, counterclaims = [], []
    for annotation, outcome in zip(annotations, regenerated["outcomes"]):
        if annotation["id"] != outcome["annotation_id"]:
            raise ValueError("reference ordering changed")
        if annotation["expected_status"] != "supported":
            counterclaims.append({"id": annotation["id"], "statement": annotation["statement"],
                                  "expected_status": annotation["expected_status"], "frozen_outcome": outcome,
                                  "assessment": "No promotion/proposal observed. This does not establish detection, refutation or general adversarial robustness."})
            continue
        ident = annotation["id"]
        note = ADJUDICATIONS[ident]
        entry = {"annotation_id": ident, "project_id": case["id"], "split": annotation["split"],
                 "statement": annotation["statement"], "reference": annotation,
                 "frozen_outcome": outcome, **note,
                 "source_reference_spans": _reference_spans(annotation, sources, inventory),
                 "source_overlapping_candidates": [_candidate(byid[i]) for i in outcome["source_candidate_ids"]],
                 "strict_candidate_diagnostics": []}
        for candidate_id in outcome["source_candidate_ids"]:
            candidate = byid[candidate_id]
            match, target, reason = frozen._semantic(candidate, frozen._expectation(annotation), records, annotation, sources)
            entry["strict_candidate_diagnostics"].append({"candidate_id": candidate_id,
                "semantic_match": match, "target_identified": target, "first_rejection_or_match_reason": reason})
        # A distinct diagnostic calculation, not a retroactive change to a label.
        if ident == "final-goldbeter-003":
            exact = compare(byid[outcome["targeted_candidate_ids"][0]]["rhs"],
                            parse_expression(annotation["typed_expectation"]["rhs"]))
            if exact["status"] != "EQUAL_ON_COMMON_DEFINED_DOMAIN":
                raise ValueError("independent rational adjudication changed")
            entry["independent_diagnostic_equivalence"] = exact
        if ident == "tyson-cdc2-conservation":
            entry["unlinked_existing_scoped_check"] = [
                {"id": c["id"], "checker": c["checker"], "status": c["status"],
                 "conservation": c.get("evidence", {}).get("conservation"),
                 "kernel_certificate_statuses": [k["status"] for k in c.get("evidence", {}).get("kernel_certificates", [])]}
                for c in checks if c.get("checker") == "model_assurance"]
        supported.append(entry)
    # Retain an observed error outside the incomplete reference probe set. This
    # prevents the absence of wrong literals in targeted pairs from being read
    # as an overall semantic-precision result.
    extra = []
    if case["id"] == "scipy_integrate":
        for record in records:
            if record["_category"] == "quantities" and "system of :math:`2N`" in record.get("source", {}).get("quote", ""):
                extra.append({"candidate": _candidate(record),
                    "internal_adjudication": "The source counts 2*N differential equations; the heuristic instead emits a measurement value2 with unitN (newton). This is a genuine unannotated semantic parsing error, not a grading mismatch.",
                    "scoring_scope": "Outside the 53 frozen probes; not included in a retrospectively altered precision denominator.",
                    "error_tags": ["incorrect_quantity_interpretation", "units_dimensions", "mathematical_interpretation"]})
    return {"id": case["id"], "frozen_metrics": regenerated["metrics"],
            "grade_reproduced_byte_equivalent_json": True, "supported_claims": supported,
            "counterclaim_probes": counterclaims, "unannotated_diagnostic_counterexamples": extra}


def build_atlas():
    """Return a deterministic full atlas; fail if old scores or bytes change."""
    inputs, splits = {}, []
    for relative, digest in FROZEN_INPUT_SHA256.items():
        if _sha((OLD / relative).read_bytes()) != digest:
            raise ValueError("frozen historical input changed: " + relative)
    for split in ("development", "final"):
        files = {"results": OLD / "evidence" / f"{split}-primary.json.gz",
                 "archive": OLD / "evidence" / f"{split}-primary-packages.zip",
                 "references": OLD / "reference" / f"{split}.json"}
        for path in files.values():
            inputs[str(path.relative_to(ROOT))] = _sha(path.read_bytes())
        results = json.loads(gzip.decompress(files["results"].read_bytes()))
        labels = _read(files["references"])["annotations"]
        with tempfile.TemporaryDirectory(prefix="pcs-v2-atlas-") as temporary, zipfile.ZipFile(files["archive"]) as z:
            cases = []
            for case in results["cases"]:
                annotations = [a for a in labels if a["project_id"] == case["id"]]
                interpretation, checks, inventory = _load_case(z, case["id"], Path(temporary))
                cases.append(_diagnose_case(case, annotations, interpretation, checks, inventory))
        entries = [a for c in cases for a in c["supported_claims"]]
        missed = [a for a in entries if not a["frozen_outcome"]["semantic_match_ids"]]
        splits.append({"split": split, "cases": cases,
                       "summary": {"supported": len(entries), "matched": len(entries)-len(missed), "missed": len(missed),
                                   "primary_failure_counts": dict(sorted(Counter(a["primary_failure_class"] for a in missed).items())),
                                   "overlapping_error_tag_counts": dict(sorted(Counter(t for a in missed for t in a["error_tags"]).items())),
                                   "failed_claim_ids": [a["annotation_id"] for a in missed]}})
    for path in (OLD / "evaluation.py", OLD / "reference/annotation_freeze.json"):
        inputs[str(path.relative_to(ROOT))] = _sha(path.read_bytes())
    observed = [(s["summary"]["matched"], s["summary"]["supported"]) for s in splits]
    if observed != [(6, 21), (1, 20)]:
        raise ValueError("frozen supported metrics changed")
    actual_ids = {a["annotation_id"] for s in splits for c in s["cases"] for a in c["supported_claims"]}
    if actual_ids != set(ADJUDICATIONS):
        raise ValueError("manual atlas is not exhaustive")
    return {"format": "pcs-v2-primary-error-atlas-v1", "diagnostic_only": True,
            "historical_stack_head": OLD_HEAD, "primary_source_commit": PRIMARY_SOURCE_COMMIT,
            "original_protocol_sha256": frozen.protocol_sha256(), "input_sha256": inputs,
            "adjudication_provenance": {"method": "AI-assisted internal review of original sources, frozen reference annotations and exact archived output",
                "human_domain_expert_review": False, "external_validation": False,
                "new_prospective_sources_consulted": False, "old_results_modified": False},
            "scoring_warning": "No revised recall, semantic score or held-out improvement is inferred from diagnostic classifications. All source meaning remains untrusted.",
            "taxonomy_note": "Primary classes partition the 34 misses; error tags overlap. Missing extraction means no valid bounded overlapping candidate, not absence of the source file.",
            "unsupported_promotion_total": sum(c["frozen_metrics"]["unsupported_promotion_count"] for s in splits for c in s["cases"]),
            "splits": splits, "authority": False}


def markdown(atlas):
    lines = ["# PR #202 exhaustive primary error atlas", "",
             "This is a post-hoc diagnostic review of the exposed v2 evaluation. It reproduces the frozen grader exactly and preserves development **6/21** and old-final **1/20** supported-claim recall. It is not a new held-out experiment or revised semantic score.", "",
             "All 41 supported probes are inspected below, including all 34 misses and all 19 old-final misses. The 12 counterclaim/insufficient-evidence probes are retained in JSON. Internal adjudication is AI-assisted and requires domain-expert review; there is no independent external validation.", "",
             "## What failed", "",
             "The failures are not 34 demonstrated incorrect scientific assertions. They combine absent extraction/derived claims, unresolved scientific roles and assumptions, and strict representation/grading mismatches. Three correctly recovered reported iteration/evaluation counts are rejected solely by the frozen relation schema. The Goldbeter V1 inverse-power expression is independently equal to the division expression on the common defined domain, but syntax matching misses it. This diagnostic does not establish full scientific equivalence or alter the original result.", "",
             "Other apparently simple mismatches need care. Unspecified units cannot be changed into physical units to make a label pass. `encoded_model_unit` and `encoded_concentration` are reference role labels, not SI units. Extracting a return vector does not establish an ODE derivative role. A source sum is not a conservation law without a complete model/dependency argument. Conditional dimensional consequences must retain their assumptions.", "",
             "No targeted mismatch in this set demonstrates an incorrect numeric literal replacing an already correctly grounded reference value. This does not measure overall extraction precision: most generated candidates are unannotated. A retained **genuine semantic counterexample outside the probes** is the integration tutorial's `2N` differential-equation count: the heuristic emits value2 with unitN (newton). That confuses a symbolic equation count with a force measurement. Duplicate quantity/claim projections and parameter-only targets also inflate pair mismatches relative to scientific claim counts.", "",
             "## Reproduction", "", "```bash", "python -m research.scientific_semantics_v3.error_atlas --check", "```", "",
             "The command checks original archive/object hashes, source spans and the full frozen grading output for every case. It independently computes the V1 rational diagnostic with the v2 bounded normalizer. It does not run uploaded code, alter old artifacts or consult the new prospective corpus.", ""]
    for split in atlas["splits"]:
        summary = split["summary"]
        lines += ["## " + split["split"], "", f"Frozen matched/supported: {summary['matched']}/{summary['supported']}. Misses: {summary['missed']}.", "",
                  "| Primary diagnosis | Missed claims |", "| --- | ---: |"]
        lines += [f"| {key} | {count} |" for key, count in summary["primary_failure_counts"].items()]
        lines.append("")
        for case in split["cases"]:
            lines += ["### " + case["id"], ""]
            for item in case["supported_claims"]:
                outcome = item["frozen_outcome"]
                state = "MATCH" if outcome["semantic_match_ids"] else "MISS"
                lines += [f"**{item['annotation_id']} — {state}: {item['primary_failure_class']}**", "",
                          item["statement"], "", item["internal_adjudication"], "",
                          "Required next check: " + item["next_required_check"], "",
                          "Abstention assessment: `" + item["abstention_assessment"] + "`. Error tags: " + ", ".join(f"`{t}`" for t in item["error_tags"]) + ".", "",
                          "Source: `" + item["reference"]["source"]["path"] + "` (SHA256 `" + item["reference"]["source"]["sha256"] + "`). "
                          + ("Overlapping candidate IDs: " + ", ".join(f"`{i}`" for i in outcome["source_candidate_ids"]) + "." if outcome["source_candidate_ids"] else "No valid overlapping candidate under the frozen bounded source policy."), ""]
                if outcome["semantic_mismatches"]:
                    lines += ["Frozen first rejection reasons: " + "; ".join(sorted(set(m["reason"] for m in outcome["semantic_mismatches"]))) + ".", ""]
    lines += ["## Scope and unresolved adjudication", "",
              "The JSON retains each full source/reference interpretation, exact overlapping candidate quotations and typed fields, every first frozen rejection reason, per-case unchanged metrics and input hashes. Source-grounding failures in this atlas mean no qualifying overlapping candidate; original files remain preserved. Scientific synonym/reference resolution, variable aliases, assumptions, units, numerical relationships, equivalent forms and schema limitations are classified separately. Statistical generalization and biological adequacy remain unestablished.", "",
              "Conditional scientific prose and dimensional constraints cannot be certified by a broader spelling alias. A successor system needs explicit entity/quantity-kind/evidence-status fields, definition closure and domain-aware checks. It must be evaluated on new projects; this exposed set can now support development only.", ""]
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="regenerate and compare committed atlas/report")
    args = parser.parse_args(argv)
    atlas = build_atlas()
    raw = (json.dumps(atlas, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n").encode()
    report = markdown(atlas)
    output = HERE / "evidence/error-atlas.json"
    document = HERE / "ERROR_ATLAS.md"
    if args.check:
        if output.read_bytes() != raw or document.read_text(encoding="utf-8") != report:
            raise SystemExit("diagnostic atlas/report differs; inspect before changing historical diagnostic evidence")
    else:
        # A successor diagnostic uses a new path rather than silently replacing
        # an established report. Re-running identical bytes is harmless.
        if output.exists() and output.read_bytes() != raw:
            raise SystemExit("refusing to overwrite a different diagnostic atlas")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(raw)
        document.write_text(report, encoding="utf-8")
    print(json.dumps({"status": "REPRODUCED", "supported": 41, "misses": 34,
                      "development": "6/21", "exposed_final": "1/20",
                      "atlas_sha256": _sha(raw), "unsupported_promotions": atlas["unsupported_promotion_total"]}))


if __name__ == "__main__":
    main()
