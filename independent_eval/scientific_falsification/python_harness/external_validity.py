"""External-validity protocol templates and scoring software (Task 11).

No invented participants or results. Scoring operates only on protocol
structure / declared fields supplied by a future study operator.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REQUIRED_PROTOCOL_FIELDS = (
    "protocol_id",
    "title",
    "purpose",
    "pcs_claims_in_scope",
    "pcs_claims_out_of_scope",
    "population_definition",
    "inclusion_criteria",
    "exclusion_criteria",
    "endpoints",
    "adequacy_criteria",
    "negative_controls",
    "data_management",
    "ethics_status",
    "license",
)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def score_protocol(protocol: dict[str, Any], rubric: dict[str, Any]) -> dict[str, Any]:
    """Score a filled (or blank) protocol against a rubric.

    Missing empirical results are scored as NOT_PROVIDED rather than fabricated.
    """
    weights: dict[str, float] = rubric.get("field_weights", {})
    notes: list[str] = []
    earned = 0.0
    possible = 0.0

    for field in rubric.get("required_fields", list(REQUIRED_PROTOCOL_FIELDS)):
        w = float(weights.get(field, 1.0))
        possible += w
        value = protocol.get(field)
        if value is None or value == "" or value == [] or value == {}:
            notes.append(f"missing:{field}")
            continue
        earned += w

    # Explicit ban on hallucinated results sections.
    results = protocol.get("results")
    results_status = "NOT_PROVIDED"
    if results is None:
        results_status = "NOT_PROVIDED"
        notes.append("results:NOT_PROVIDED (expected for templates / unevaluated studies)")
    elif isinstance(results, dict) and results.get("status") == "NOT_COLLECTED":
        results_status = "NOT_COLLECTED"
    elif results:
        results_status = "PROVIDED"
        notes.append(
            "results:PROVIDED — scoring does not validate empirical truth; "
            "external review required"
        )

    participants = protocol.get("participants")
    if participants not in (None, [], {}, {"status": "NOT_ENROLLED"}):
        notes.append(
            "participants field is present; this scorer does not invent or "
            "authenticate participant records"
        )

    ratio = earned / possible if possible else 0.0
    return {
        "format": "pcs-independent-eval-external-validity-score-v1",
        "protocol_id": protocol.get("protocol_id"),
        "completeness_score": round(ratio, 4),
        "earned_weight": earned,
        "possible_weight": possible,
        "results_status": results_status,
        "empirical_adequacy_established": False,
        "pcs_verification_equivalence": False,
        "notes": notes,
        "rubric_id": rubric.get("rubric_id"),
    }


def score_protocol_file(protocol_path: Path, rubric_path: Path) -> dict[str, Any]:
    return score_protocol(load_json(protocol_path), load_json(rubric_path))


def write_default_templates(external_root: Path) -> None:
    templates = external_root / "templates"
    rubrics = external_root / "rubrics"
    templates.mkdir(parents=True, exist_ok=True)
    rubrics.mkdir(parents=True, exist_ok=True)

    blank = {
        "format": "pcs-independent-eval-external-validity-protocol-v1",
        "protocol_id": "EV-TEMPLATE-001",
        "title": "External validity assessment for a PCS-certified computational claim",
        "purpose": (
            "Separate computational PCS verification from empirical external validity. "
            "This template records planned study design only."
        ),
        "pcs_claims_in_scope": [
            "Declared computational claims verified by PCS for a fixed artifact snapshot"
        ],
        "pcs_claims_out_of_scope": [
            "Biological adequacy",
            "Clinical effectiveness",
            "Population transport",
            "Causal identification",
        ],
        "population_definition": "",
        "inclusion_criteria": [],
        "exclusion_criteria": [],
        "endpoints": [],
        "adequacy_criteria": [
            {
                "id": "AC1",
                "statement": "Pre-specify what would count as empirical adequacy independently of PCS verify PASS.",
            }
        ],
        "negative_controls": [
            {
                "id": "NC1",
                "statement": "A computation that verifies but uses an intentionally inadequate model class.",
            }
        ],
        "data_management": {
            "participant_data": "NONE_IN_TEMPLATE",
            "retention": "NOT_APPLICABLE_UNTIL_STUDY_ACTIVATED",
        },
        "ethics_status": "NOT_SUBMITTED",
        "participants": {"status": "NOT_ENROLLED"},
        "results": {"status": "NOT_COLLECTED"},
        "license": {
            "spdx": "CC0-1.0",
            "statement": "Template only; no participant data; no study results.",
        },
    }
    (templates / "external_validity_protocol_blank.json").write_text(
        json.dumps(blank, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    transport = {
        **blank,
        "protocol_id": "EV-TEMPLATE-002",
        "title": "Population transport / external validity protocol (template)",
        "purpose": (
            "Plan assessment of whether a computationally verified model remains "
            "adequate under a target population shift. No results included."
        ),
        "population_definition": "TARGET_POPULATION_TO_BE_SPECIFIED",
        "endpoints": [
            {
                "id": "EP_TRANSPORT",
                "statement": "Pre-specify transport metric; do not equate with PCS certificate validity.",
            }
        ],
    }
    (templates / "population_transport_protocol_blank.json").write_text(
        json.dumps(transport, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    reviewer = {
        **blank,
        "protocol_id": "EV-TEMPLATE-003",
        "title": "Reviewer checklist: computational verification vs scientific adequacy",
        "purpose": "Structured reviewer prompts. Contains no participant results.",
        "adequacy_criteria": [
            {
                "id": "R1",
                "statement": "Did PCS verify only the declared computational claim?",
            },
            {
                "id": "R2",
                "statement": "Were empirical adequacy claims left OPEN / out of scope?",
            },
            {
                "id": "R3",
                "statement": "Are negative controls documented for model-class inadequacy?",
            },
        ],
    }
    (templates / "reviewer_adequacy_checklist_blank.json").write_text(
        json.dumps(reviewer, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    rubric = {
        "rubric_id": "EV-RUBRIC-001",
        "format": "pcs-independent-eval-external-validity-rubric-v1",
        "required_fields": list(REQUIRED_PROTOCOL_FIELDS),
        "field_weights": {f: 1.0 for f in REQUIRED_PROTOCOL_FIELDS},
        "scoring_rules": [
            "Completeness only; no inference of empirical truth.",
            "results=NOT_COLLECTED or absent is acceptable for templates.",
            "PCS verify PASS never awards empirical_adequacy_established.",
        ],
        "license": {"spdx": "CC0-1.0"},
    }
    (rubrics / "completeness_rubric.json").write_text(
        json.dumps(rubric, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    (external_root / "README.md").write_text(
        "# External-validity protocols (Task 11)\n\n"
        "Templates and scoring software only. **No invented participants or results.**\n\n"
        "Score a filled protocol:\n\n"
        "```bash\n"
        "PYTHONPATH=independent_eval/scientific_falsification python3 -c\n"
        "from pathlib import Path\n"
        "from python_harness.external_validity import score_protocol_file\n"
        "print(score_protocol_file(\n"
        "  Path('independent_eval/scientific_falsification/external_validity/templates/"
        "external_validity_protocol_blank.json'),\n"
        "  Path('independent_eval/scientific_falsification/external_validity/rubrics/"
        "completeness_rubric.json')))\n"
        "```\n",
        encoding="utf-8",
    )
