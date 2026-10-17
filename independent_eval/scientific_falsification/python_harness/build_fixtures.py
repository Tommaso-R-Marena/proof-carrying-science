#!/usr/bin/env python3
"""Build immutable casebook / inadequacy / discovery fixtures and hash manifest.

Exact command (from repository root):

  PYTHONPATH=. python3 independent_eval/scientific_falsification/python_harness/build_fixtures.py
"""

from __future__ import annotations

import csv
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(REPO))

from python_harness.external_validity import write_default_templates  # noqa: E402
from python_harness.hashing import collect_file_hashes, write_json  # noqa: E402
from python_harness.paths import (  # noqa: E402
    CASEBOOK,
    DISCOVERY,
    EXTERNAL,
    FIXTURES,
    HASH_MANIFEST,
    INADEQUACY,
    METAMORPHIC,
)
from python_harness.pkpd_tables import (  # noqa: E402
    default_pkpd_model,
    write_json as write_model_json,
    write_predictions_via_pcs_adapter,
)


LICENSE = {
    "spdx": "CC0-1.0",
    "statement": "All authored fixtures under independent_eval/scientific_falsification are dedicated to the public domain under CC0-1.0. No human participants; no private data.",
}


def _case_dir(name: str) -> Path:
    d = CASEBOOK / "cases" / name
    d.mkdir(parents=True, exist_ok=True)
    return d


def _write_case_md(path: Path, **fields: str) -> None:
    lines = [
        f"# {fields['title']}",
        "",
        f"**Case ID:** `{fields['case_id']}`",
        f"**PCS checks:** {fields['checks']}",
        f"**License:** {LICENSE['spdx']}",
        "",
        "## Assumptions",
        "",
        fields["assumptions"],
        "",
        "## Expected results",
        "",
        fields["expected"],
        "",
        "## Negative controls",
        "",
        fields["negatives"],
        "",
        "## Reproduction instructions",
        "",
        fields["repro"],
        "",
        "## License metadata",
        "",
        "```json",
        json.dumps(LICENSE, indent=2),
        "```",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def build_pkpd_case(case_id: str, title: str, model: dict, times: list) -> Path:
    d = _case_dir(case_id)
    write_model_json(d / "model.json", model)
    write_predictions_via_pcs_adapter(model, d / "predictions.csv", times)
    # Negative control artifacts (not referenced by the positive manifest).
    bad_model = json.loads(json.dumps(model))
    bad_model["clearance"] = {"value": 1.0, "unit": "mg/h"}  # wrong dimension
    write_model_json(d / "negative_controls" / "bad_clearance_unit_model.json", bad_model)
    tampered = (d / "predictions.csv").read_text(encoding="utf-8").splitlines()
    # Bump a concentration cell.
    parts = tampered[2].split(",")
    parts[1] = str(float(parts[1]) + 1.0)
    tampered[2] = ",".join(parts)
    neg = d / "negative_controls"
    neg.mkdir(exist_ok=True)
    (neg / "tampered_predictions.csv").write_text("\n".join(tampered) + "\n", encoding="utf-8")

    manifest = {
        "subject": f"independent-eval-{case_id}",
        "assumptions": [
            {
                "id": "A_PK_MODEL",
                "statement": "The restricted one-compartment IV-bolus equation is the declared computational model; no claim of biological adequacy is made.",
                "rationale": "Separates computational verification from empirical PK model validation.",
                "scope": ["C_PK_CONTRACT", "C_PK_REPLAY"],
            }
        ],
        "claims": [
            {
                "id": "C_PK_CONTRACT",
                "statement": "The PK model artifact satisfies the restricted positivity and dimensional contract.",
                "kind": "computational",
                "required_evidence": ["E_PK_CONTRACT"],
                "assumptions": ["A_PK_MODEL"],
                "predicate": {"type": "pkpd_contract", "model_artifact": "pk_model"},
            },
            {
                "id": "C_PK_REPLAY",
                "statement": "The prediction artifact matches the declared analytic one-compartment IV-bolus PK and direct Emax PD model within the stated numeric tolerance.",
                "kind": "computational",
                "required_evidence": ["E_PK_REPLAY"],
                "assumptions": ["A_PK_MODEL"],
                "predicate": {
                    "type": "pkpd_reference_match",
                    "model_artifact": "pk_model",
                    "output_artifact": "pk_predictions",
                    "time_column": "time",
                    "concentration_column": "concentration",
                    "effect_column": "effect",
                    "rel_tol": 1e-09,
                    "abs_tol": 1e-12,
                },
            },
        ],
        "artifacts": [
            {
                "id": "pk_model",
                "path": "model.json",
                "role": "restricted-pk-model",
                "media_type": "application/json",
            },
            {
                "id": "pk_predictions",
                "path": "predictions.csv",
                "role": "pk-predictions",
                "media_type": "text/csv",
            },
        ],
        "checks": [
            {
                "id": "E_PK_CONTRACT",
                "type": "pkpd_contract",
                "claim_ids": ["C_PK_CONTRACT"],
                "model_artifact": "pk_model",
            },
            {
                "id": "E_PK_REPLAY",
                "type": "pkpd_reference_match",
                "claim_ids": ["C_PK_REPLAY"],
                "model_artifact": "pk_model",
                "output_artifact": "pk_predictions",
                "time_column": "time",
                "concentration_column": "concentration",
                "effect_column": "effect",
                "rel_tol": 1e-09,
                "abs_tol": 1e-12,
            },
        ],
        "workflow": {
            "nodes": [
                {
                    "id": "N_PK",
                    "operation": "restricted_one_compartment_iv_bolus",
                    "inputs": ["pk_model"],
                    "outputs": ["pk_predictions"],
                    "contract": {
                        "equation": "C(t)=(Dose/V)*exp(-(CL/V)*t); E(C)=E0+Emax*C/(EC50+C)",
                        "validation_scope": "computational replay only",
                    },
                }
            ]
        },
    }
    write_json(d / "manifest.json", manifest)
    write_json(d / "license.json", LICENSE)
    _write_case_md(
        d / "CASE.md",
        case_id=case_id,
        title=title,
        checks="`pkpd_contract`, `pkpd_reference_match`",
        assumptions=(
            "- Declared model is restricted one-compartment IV bolus + direct Emax.\n"
            "- Computational replay only; no empirical adequacy claim."
        ),
        expected=(
            "- `pcs certify` emits PASS evidence for both claims "
            "(`COMPUTATIONALLY_SUPPORTED`).\n"
            "- `pcs verify` on the certificate returns valid."
        ),
        negatives=(
            "- `negative_controls/bad_clearance_unit_model.json` fails `pkpd_contract` "
            "(clearance has mass/time dimensions).\n"
            "- `negative_controls/tampered_predictions.csv` fails `pkpd_reference_match`."
        ),
        repro=(
            "```bash\n"
            f"pcs certify independent_eval/scientific_falsification/casebook/cases/{case_id}/manifest.json "
            f"-o /tmp/pcs-sf-{case_id}\n"
            f"pcs verify /tmp/pcs-sf-{case_id}/certificate.json\n"
            "```"
        ),
    )
    return d


def build_reaction_case() -> Path:
    case_id = "03_mass_action_reaction_balance"
    d = _case_dir(case_id)
    # Element-balanced glucose cleavage C6H12O6 -> 2 C3H6O3 (from scientific_mass_action).
    reaction = {
        "id": "cleavage",
        "reactants": [{"formula": "C6H12O6", "coefficient": 1}],
        "products": [{"formula": "C3H6O3", "coefficient": 2}],
        "note": "Synthetic stoichiometry aligned with examples/scientific_mass_action; not validated biology.",
    }
    write_json(d / "reaction.json", reaction)
    # Unbalanced negative: missing product coefficient.
    write_json(
        d / "negative_controls" / "unbalanced_reaction.json",
        {
            "reactants": [{"formula": "C6H12O6", "coefficient": 1}],
            "products": [{"formula": "C3H6O3", "coefficient": 1}],
        },
    )
    manifest = {
        "subject": "independent-eval-mass-action-balance",
        "assumptions": [
            {
                "id": "A_STOICH",
                "statement": "Only elemental stoichiometry of the declared reaction is claimed; kinetics and biology are out of scope.",
            }
        ],
        "claims": [
            {
                "id": "C_BALANCE",
                "statement": "The declared cleavage reaction is element-balanced under the PCS formula parser.",
                "kind": "computational",
                "required_evidence": ["E_BALANCE"],
                "assumptions": ["A_STOICH"],
                "predicate": {
                    "type": "reaction_balance",
                    "reactants": reaction["reactants"],
                    "products": reaction["products"],
                },
            }
        ],
        "artifacts": [
            {
                "id": "rxn",
                "path": "reaction.json",
                "role": "reaction-specification",
                "media_type": "application/json",
            }
        ],
        "checks": [
            {
                "id": "E_BALANCE",
                "type": "reaction_balance",
                "claim_ids": ["C_BALANCE"],
                "reactants": reaction["reactants"],
                "products": reaction["products"],
            }
        ],
        "workflow": {"nodes": []},
    }
    write_json(d / "manifest.json", manifest)
    write_json(d / "license.json", LICENSE)
    _write_case_md(
        d / "CASE.md",
        case_id=case_id,
        title="Mass-action stoichiometry via reaction_balance",
        checks="`reaction_balance`",
        assumptions="- Element balance of authored synthetic cleavage only; no kinetic validation.",
        expected="- Certify/verify PASS for balanced C6H12O6 -> 2 C3H6O3.",
        negatives="- Unbalanced 1:1 cleavage fails reaction_balance.",
        repro=(
            "```bash\n"
            "pcs certify independent_eval/scientific_falsification/casebook/cases/"
            f"{case_id}/manifest.json -o /tmp/pcs-sf-{case_id}\n"
            f"pcs verify /tmp/pcs-sf-{case_id}/certificate.json\n"
            "```"
        ),
    )
    return d


def build_units_case() -> Path:
    case_id = "04_unit_compatible_concentration"
    d = _case_dir(case_id)
    manifest = {
        "subject": "independent-eval-unit-compatible",
        "assumptions": [
            {
                "id": "A_UNITS",
                "statement": "Unit compatibility is a dimensional claim only; quantity identity and clinical meaning are not claimed.",
            }
        ],
        "claims": [
            {
                "id": "C_UNITS",
                "statement": "mg/L and ug/mL are dimensionally compatible concentration units.",
                "kind": "computational",
                "required_evidence": ["E_UNITS"],
                "assumptions": ["A_UNITS"],
                "predicate": {
                    "type": "unit_compatible",
                    "left_unit": "mg/L",
                    "right_unit": "ug/mL",
                },
            }
        ],
        "artifacts": [],
        "checks": [
            {
                "id": "E_UNITS",
                "type": "unit_compatible",
                "claim_ids": ["C_UNITS"],
                "left_unit": "mg/L",
                "right_unit": "ug/mL",
            }
        ],
        "workflow": {"nodes": []},
    }
    write_json(d / "manifest.json", manifest)
    write_json(
        d / "negative_controls" / "incompatible_units_check.json",
        {"left_unit": "mg/L", "right_unit": "L/h"},
    )
    write_json(d / "license.json", LICENSE)
    _write_case_md(
        d / "CASE.md",
        case_id=case_id,
        title="Unit compatibility for concentration spellings",
        checks="`unit_compatible`",
        assumptions="- Dimensional compatibility only.",
        expected="- mg/L vs ug/mL PASS.",
        negatives="- mg/L vs L/h FAIL.",
        repro=(
            "```bash\n"
            f"pcs certify independent_eval/scientific_falsification/casebook/cases/{case_id}/manifest.json "
            f"-o /tmp/pcs-sf-{case_id}\n"
            f"pcs verify /tmp/pcs-sf-{case_id}/certificate.json\n"
            "```"
        ),
    )
    return d


def build_csv_disjoint_case() -> Path:
    case_id = "05_csv_disjoint_cohorts"
    d = _case_dir(case_id)
    train = d / "train.csv"
    test = d / "test.csv"
    with train.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["subject_id", "cohort"])
        w.writerow(["S001", "train"])
        w.writerow(["S002", "train"])
    with test.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["subject_id", "cohort"])
        w.writerow(["S101", "test"])
        w.writerow(["S102", "test"])
    overlap = d / "negative_controls" / "overlapping_test.csv"
    overlap.parent.mkdir(parents=True, exist_ok=True)
    with overlap.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["subject_id", "cohort"])
        w.writerow(["S001", "leak"])
        w.writerow(["S103", "test"])

    manifest = {
        "subject": "independent-eval-csv-disjoint",
        "assumptions": [
            {
                "id": "A_SPLIT",
                "statement": "Subject identifiers are opaque strings; disjointness does not establish sampling validity.",
            }
        ],
        "claims": [
            {
                "id": "C_DISJOINT",
                "statement": "Train and test subject_id sets are disjoint.",
                "kind": "computational",
                "required_evidence": ["E_DISJOINT"],
                "assumptions": ["A_SPLIT"],
                "predicate": {
                    "type": "csv_disjoint",
                    "left_artifact": "train",
                    "right_artifact": "test",
                    "key": "subject_id",
                },
            }
        ],
        "artifacts": [
            {
                "id": "train",
                "path": "train.csv",
                "role": "split-table",
                "media_type": "text/csv",
            },
            {
                "id": "test",
                "path": "test.csv",
                "role": "split-table",
                "media_type": "text/csv",
            },
        ],
        "checks": [
            {
                "id": "E_DISJOINT",
                "type": "csv_disjoint",
                "claim_ids": ["C_DISJOINT"],
                "left_artifact": "train",
                "right_artifact": "test",
                "key": "subject_id",
            }
        ],
        "workflow": {"nodes": []},
    }
    write_json(d / "manifest.json", manifest)
    write_json(d / "license.json", LICENSE)
    _write_case_md(
        d / "CASE.md",
        case_id=case_id,
        title="CSV key disjointness for train/test cohorts",
        checks="`csv_disjoint`",
        assumptions="- Opaque subject IDs; no sampling validity.",
        expected="- Disjoint train/test PASS.",
        negatives="- Overlapping subject_id FAIL.",
        repro=(
            "```bash\n"
            f"pcs certify independent_eval/scientific_falsification/casebook/cases/{case_id}/manifest.json "
            f"-o /tmp/pcs-sf-{case_id}\n"
            f"pcs verify /tmp/pcs-sf-{case_id}/certificate.json\n"
            "```"
        ),
    )
    return d


def build_composite_workflow_case() -> Path:
    """Composite workflow mirroring scientific example concerns with built-in checks."""
    case_id = "06_scientific_workflow_composite"
    d = _case_dir(case_id)
    reaction = {
        "reactants": [{"formula": "H2", "coefficient": 2}, {"formula": "O2", "coefficient": 1}],
        "products": [{"formula": "H2O", "coefficient": 2}],
    }
    write_json(d / "reaction.json", reaction)
    write_json(d / "license.json", LICENSE)
    manifest = {
        "subject": "independent-eval-scientific-workflow-composite",
        "assumptions": [
            {
                "id": "A_COMPOSITE",
                "statement": "Composite computational checks do not jointly establish empirical scientific adequacy.",
            }
        ],
        "claims": [
            {
                "id": "C_RXN",
                "statement": "2 H2 + O2 -> 2 H2O is element-balanced.",
                "kind": "computational",
                "required_evidence": ["E_RXN"],
                "assumptions": ["A_COMPOSITE"],
                "predicate": {
                    "type": "reaction_balance",
                    "reactants": reaction["reactants"],
                    "products": reaction["products"],
                },
            },
            {
                "id": "C_UNITS",
                "statement": "mol/L and mmol/mL are dimensionally compatible.",
                "kind": "computational",
                "required_evidence": ["E_UNITS"],
                "assumptions": ["A_COMPOSITE"],
                "predicate": {
                    "type": "unit_compatible",
                    "left_unit": "mol/L",
                    "right_unit": "mmol/mL",
                },
            },
        ],
        "artifacts": [
            {
                "id": "rxn",
                "path": "reaction.json",
                "role": "reaction-specification",
                "media_type": "application/json",
            }
        ],
        "checks": [
            {
                "id": "E_RXN",
                "type": "reaction_balance",
                "claim_ids": ["C_RXN"],
                "reactants": reaction["reactants"],
                "products": reaction["products"],
            },
            {
                "id": "E_UNITS",
                "type": "unit_compatible",
                "claim_ids": ["C_UNITS"],
                "left_unit": "mol/L",
                "right_unit": "mmol/mL",
            },
        ],
        "workflow": {
            "nodes": [
                {
                    "id": "N_BALANCE",
                    "operation": "reaction_balance_check",
                    "inputs": ["rxn"],
                    "outputs": [],
                    "contract": {"validation_scope": "element balance only"},
                }
            ]
        },
    }
    write_json(d / "manifest.json", manifest)
    write_json(
        d / "negative_controls" / "broken_units.json",
        {"left_unit": "mol/L", "right_unit": "s"},
    )
    _write_case_md(
        d / "CASE.md",
        case_id=case_id,
        title="Composite scientific workflow checks (balance + units)",
        checks="`reaction_balance`, `unit_compatible`",
        assumptions="- Composite computational claims only.",
        expected="- Both claims COMPUTATIONALLY_SUPPORTED.",
        negatives="- mol/L vs s unit check fails.",
        repro=(
            "```bash\n"
            f"pcs certify independent_eval/scientific_falsification/casebook/cases/{case_id}/manifest.json "
            f"-o /tmp/pcs-sf-{case_id}\n"
            f"pcs verify /tmp/pcs-sf-{case_id}/certificate.json\n"
            "```"
        ),
    )
    return d


def build_pkpd_alt_params_case() -> Path:
    case_id = "07_pkpd_alt_parameters"
    model = default_pkpd_model(
        dose={"value": 50.0, "unit": "mg"},
        volume={"value": 5.0, "unit": "L"},
        clearance={"value": 0.5, "unit": "L/h"},
    )
    return build_pkpd_case(
        case_id,
        "Alternate PK/PD parameter set (still computational-only)",
        model,
        [0, 2, 8, 24],
    )


def build_inadequacy_examples() -> None:
    base = INADEQUACY / "examples"
    if base.exists():
        shutil.rmtree(base)
    base.mkdir(parents=True)

    # Example A: computationally correct PKPD with physiologically absurd parameters.
    # Keep magnitudes within stable Decimal/CSV replay range while remaining
    # scientifically inadequate (multi-gram IV bolus + extremely high clearance).
    absurd = default_pkpd_model(
        dose={"value": 5000.0, "unit": "mg"},
        volume={"value": 5.0, "unit": "L"},
        clearance={"value": 50.0, "unit": "L/h"},
    )
    a = base / "01_correct_but_inadequate_pkpd"
    a.mkdir(parents=True)
    write_model_json(a / "model.json", absurd)
    write_predictions_via_pcs_adapter(absurd, a / "predictions.csv", [0, 0.01, 0.1, 1.0])
    # Reuse standard PKPD manifest structure
    manifest = json.loads(
        (CASEBOOK / "cases" / "01_pkpd_one_compartment" / "manifest.json").read_text(
            encoding="utf-8"
        )
    )
    manifest["subject"] = "independent-eval-inadequate-but-correct-pkpd"
    manifest["assumptions"][0][
        "statement"
    ] = (
        "Declared computational model only. Parameters are intentionally physiologically "
        "absurd to demonstrate that PCS may still verify the declared computational claim."
    )
    write_json(a / "manifest.json", manifest)
    write_json(a / "license.json", LICENSE)
    (a / "README.md").write_text(
        "# Correct computation, inadequate model\n\n"
        "PCS `pkpd_contract` + `pkpd_reference_match` are expected to PASS.\n"
        "Empirical/clinical adequacy remains OPEN and is not established by verification.\n",
        encoding="utf-8",
    )

    # Example B: balanced reaction that is not a claimed real pathway.
    b = base / "02_balanced_but_biologically_inadequate"
    b.mkdir(parents=True)
    reaction = {
        "reactants": [{"formula": "C6H12O6", "coefficient": 1}],
        "products": [{"formula": "C3H6O3", "coefficient": 2}],
        "scientific_note": "Element balance holds; this is not a validated glycolytic mechanism claim.",
    }
    write_json(b / "reaction.json", reaction)
    write_json(
        b / "manifest.json",
        {
            "subject": "independent-eval-balanced-inadequate-biology",
            "assumptions": [
                {
                    "id": "A1",
                    "statement": "Only stoichiometry is claimed; pathway biology is inadequate/unvalidated.",
                }
            ],
            "claims": [
                {
                    "id": "C1",
                    "statement": "Reaction is element-balanced.",
                    "kind": "computational",
                    "required_evidence": ["E1"],
                    "assumptions": ["A1"],
                    "predicate": {
                        "type": "reaction_balance",
                        "reactants": reaction["reactants"],
                        "products": reaction["products"],
                    },
                }
            ],
            "artifacts": [
                {
                    "id": "rxn",
                    "path": "reaction.json",
                    "role": "reaction-specification",
                    "media_type": "application/json",
                }
            ],
            "checks": [
                {
                    "id": "E1",
                    "type": "reaction_balance",
                    "claim_ids": ["C1"],
                    "reactants": reaction["reactants"],
                    "products": reaction["products"],
                }
            ],
            "workflow": {"nodes": []},
        },
    )
    write_json(b / "license.json", LICENSE)
    (b / "README.md").write_text(
        "# Balanced stoichiometry without empirical adequacy\n\n"
        "Verification of `reaction_balance` does not establish biological pathway correctness.\n",
        encoding="utf-8",
    )

    # Example C: unit-compatible concentrations that do not mean the measured quantity is right.
    c = base / "03_units_ok_quantity_inadequate"
    c.mkdir(parents=True)
    write_json(
        c / "manifest.json",
        {
            "subject": "independent-eval-units-ok-quantity-inadequate",
            "assumptions": [
                {
                    "id": "A1",
                    "statement": "Unit compatibility is not evidence that the modeled quantity matches the scientific measurand.",
                }
            ],
            "claims": [
                {
                    "id": "C1",
                    "statement": "g/L and mg/mL are dimensionally compatible.",
                    "kind": "computational",
                    "required_evidence": ["E1"],
                    "assumptions": ["A1"],
                    "predicate": {
                        "type": "unit_compatible",
                        "left_unit": "g/L",
                        "right_unit": "mg/mL",
                    },
                }
            ],
            "artifacts": [],
            "checks": [
                {
                    "id": "E1",
                    "type": "unit_compatible",
                    "claim_ids": ["C1"],
                    "left_unit": "g/L",
                    "right_unit": "mg/mL",
                }
            ],
            "workflow": {"nodes": []},
        },
    )
    write_json(c / "license.json", LICENSE)
    (c / "README.md").write_text(
        "# Compatible units, inadequate quantity claim\n\n"
        "PCS can verify dimensional compatibility while the underlying scientific "
        "quantity (e.g., unbound vs total concentration) remains inadequate.\n",
        encoding="utf-8",
    )

    write_json(
        INADEQUACY / "INDEX.json",
        {
            "format": "pcs-independent-eval-inadequacy-index-v1",
            "examples": [
                {
                    "id": "01_correct_but_inadequate_pkpd",
                    "thesis": "Computational PASS does not imply empirical PK adequacy.",
                },
                {
                    "id": "02_balanced_but_biologically_inadequate",
                    "thesis": "Element balance does not imply biological pathway correctness.",
                },
                {
                    "id": "03_units_ok_quantity_inadequate",
                    "thesis": "Unit compatibility does not imply measurand adequacy.",
                },
            ],
            "license": LICENSE,
        },
    )


def build_discovery_projects() -> None:
    root = DISCOVERY / "projects"
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)

    # Project with clear PKPD model + predictions (expect contract + replay).
    p1 = root / "pkpd_detectable"
    p1.mkdir()
    model = default_pkpd_model()
    write_model_json(p1 / "model.json", model)
    write_predictions_via_pcs_adapter(model, p1 / "predictions.csv", [0, 1, 4])

    # Project with reaction JSON only.
    p2 = root / "reaction_detectable"
    p2.mkdir()
    write_json(
        p2 / "rxn.json",
        {
            "reactants": [{"formula": "N2", "coefficient": 1}, {"formula": "H2", "coefficient": 3}],
            "products": [{"formula": "NH3", "coefficient": 2}],
        },
    )

    # Project with ambiguous/empty JSON (expect abstention / no high-confidence scientific checks).
    p3 = root / "ambiguous_notes"
    p3.mkdir()
    write_json(p3 / "notes.json", {"title": "lab notebook", "entries": ["ran experiment"]})

    # Project with incompatible decoy that looks PK-like but missing PD.
    p4 = root / "pk_without_pd"
    p4.mkdir()
    write_json(
        p4 / "model.json",
        {
            "model_type": "one_compartment_iv_bolus",
            "dose": {"value": 10.0, "unit": "mg"},
            "volume": {"value": 1.0, "unit": "L"},
            "clearance": {"value": 0.1, "unit": "L/h"},
            "time_unit": "h",
            "concentration_unit": "mg/L",
        },
    )

    ground = {
        "format": "pcs-independent-eval-discovery-ground-truth-v1",
        "detector": "pcs discover-v06",
        "minimum_confidence": 0.95,
        "projects": {
            "pkpd_detectable": {
                "expected_check_types": ["pkpd_contract", "pkpd_reference_match"],
                "abstain": False,
            },
            "reaction_detectable": {
                "expected_check_types": ["reaction_balance"],
                "abstain": False,
            },
            "ambiguous_notes": {
                "expected_check_types": [],
                "abstain": True,
                "notes": "No PCS-supported scientific check should be auto-selected at high confidence.",
            },
            "pk_without_pd": {
                "expected_check_types": [],
                "abstain": True,
                "notes": "Restricted PKPD detector requires direct_emax PD fields; abstention expected.",
            },
        },
        "license": LICENSE,
    }
    write_json(DISCOVERY / "ground_truth.json", ground)


def build_casebook_index(case_ids: list[str]) -> None:
    write_json(
        CASEBOOK / "CASEBOOK_INDEX.json",
        {
            "format": "pcs-independent-eval-casebook-index-v1",
            "case_count": len(case_ids),
            "cases": case_ids,
            "supported_checks_used": sorted(
                {
                    "pkpd_contract",
                    "pkpd_reference_match",
                    "reaction_balance",
                    "unit_compatible",
                    "csv_disjoint",
                }
            ),
            "upstream_examples_referenced": [
                "examples/pkpd_one_compartment",
                "examples/scientific_mass_action",
                "examples/scientific_workflow_v2",
                "examples/scientific_workflow_v3",
            ],
            "license": LICENSE,
        },
    )
    (CASEBOOK / "README.md").write_text(
        "# Scientific casebook (Task 7)\n\n"
        "Self-contained computational workflows for independent evaluation.\n"
        "Each case documents assumptions, expected results, negative controls,\n"
        "reproduction commands, and CC0-1.0 license metadata.\n\n"
        "Rebuild fixtures:\n\n"
        "```bash\n"
        "PYTHONPATH=. python3 independent_eval/scientific_falsification/"
        "python_harness/build_fixtures.py\n"
        "```\n",
        encoding="utf-8",
    )


def main() -> int:
    FIXTURES.mkdir(parents=True, exist_ok=True)
    case_ids: list[str] = []

    build_pkpd_case(
        "01_pkpd_one_compartment",
        "One-compartment IV bolus PK/PD computational workflow",
        default_pkpd_model(),
        [0, 1, 4, 12],
    )
    case_ids.append("01_pkpd_one_compartment")

    # Peak-threshold oriented case: classic certify uses contract+match;
    # peak threshold is documented as v0.6-certified check with CLI note.
    peak_dir = _case_dir("02_pkpd_with_peak_threshold_note")
    model = default_pkpd_model()
    write_model_json(peak_dir / "model.json", model)
    write_predictions_via_pcs_adapter(model, peak_dir / "predictions.csv", [0, 1, 2, 4])
    # Positive classic manifest (contract+match) so the workflow still certifies.
    shutil.copy(
        CASEBOOK / "cases" / "01_pkpd_one_compartment" / "manifest.json",
        peak_dir / "manifest.json",
    )
    manifest = json.loads((peak_dir / "manifest.json").read_text(encoding="utf-8"))
    manifest["subject"] = "independent-eval-pkpd-peak-note"
    write_json(peak_dir / "manifest.json", manifest)
    write_json(
        peak_dir / "peak_threshold_declaration.json",
        {
            "check_type": "pkpd_peak_concentration_threshold",
            "upper_bound": "20",
            "unit": "mg/L",
            "concentration_column": "concentration",
            "scope": "v0.6 certified built-in; classic `pcs certify` kernel does not execute this check type",
            "note": "Included to document the supported check surface for scientific workflows.",
        },
    )
    write_json(peak_dir / "license.json", LICENSE)
    _write_case_md(
        peak_dir / "CASE.md",
        case_id="02_pkpd_with_peak_threshold_note",
        title="PK/PD workflow with peak-threshold declaration (v0.6 note)",
        checks="`pkpd_contract`, `pkpd_reference_match` (classic); `pkpd_peak_concentration_threshold` (v0.6 declaration)",
        assumptions="- Computational model only; peak bound is a table property, not clinical safety.",
        expected="- Classic certify/verify PASS for contract+match. Peak check is declared for v0.6 path.",
        negatives="- Tampered predictions fail reference match (see case 01 negatives pattern).",
        repro=(
            "```bash\n"
            "pcs certify independent_eval/scientific_falsification/casebook/cases/"
            "02_pkpd_with_peak_threshold_note/manifest.json -o /tmp/pcs-sf-02\n"
            "pcs verify /tmp/pcs-sf-02/certificate.json\n"
            "```"
        ),
    )
    case_ids.append("02_pkpd_with_peak_threshold_note")

    build_reaction_case()
    case_ids.append("03_mass_action_reaction_balance")
    build_units_case()
    case_ids.append("04_unit_compatible_concentration")
    build_csv_disjoint_case()
    case_ids.append("05_csv_disjoint_cohorts")
    build_composite_workflow_case()
    case_ids.append("06_scientific_workflow_composite")
    build_pkpd_alt_params_case()
    case_ids.append("07_pkpd_alt_parameters")

    build_casebook_index(case_ids)
    build_inadequacy_examples()
    build_discovery_projects()
    write_default_templates(EXTERNAL)
    METAMORPHIC.mkdir(parents=True, exist_ok=True)
    (METAMORPHIC / "README.md").write_text(
        "# Metamorphic scientific testing (Task 9)\n\n"
        "Harness: `python_harness/metamorphic.py`\n\n"
        "Black-box oracle: `pcs certify` / `pcs verify` via subprocess.\n",
        encoding="utf-8",
    )
    (DISCOVERY / "README.md").write_text(
        "# Discovery evaluation benchmark (Task 10)\n\n"
        "Synthetic projects under `projects/` with `ground_truth.json`.\n"
        "Read-only evaluation against `pcs discover-v06`.\n",
        encoding="utf-8",
    )
    (INADEQUACY / "README.md").write_text(
        "# Formal correctness vs scientific inadequacy (Task 8)\n\n"
        "Synthetic examples where PCS computational checks PASS while empirical "
        "adequacy remains unestablished.\n",
        encoding="utf-8",
    )

    # Hash all frozen fixtures under scientific_falsification except tests/results/pyc.
    hashes = collect_file_hashes(ROOT, relative_to=ROOT)
    # Drop volatile/generated docs that tests rewrite? Keep hashes for fixtures only.
    fixture_keys = {
        k: v
        for k, v in hashes.items()
        if k.startswith(
            (
                "casebook/",
                "inadequacy/",
                "discovery_benchmark/projects/",
                "discovery_benchmark/ground_truth.json",
                "external_validity/",
                "metamorphic/fixtures/",
            )
        )
        and "/__pycache__/" not in k
    }
    write_json(
        HASH_MANIFEST,
        {
            "format": "pcs-independent-eval-fixture-hashes-v1",
            "algorithm": "sha256",
            "root": "independent_eval/scientific_falsification",
            "files": fixture_keys,
            "file_count": len(fixture_keys),
        },
    )
    print(f"Wrote {len(case_ids)} cases; hashed {len(fixture_keys)} fixture files -> {HASH_MANIFEST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
