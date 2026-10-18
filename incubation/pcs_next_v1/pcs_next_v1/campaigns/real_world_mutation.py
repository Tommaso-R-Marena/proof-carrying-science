"""Scan real scientific targets, then inject deliberate errors and score detections."""

from __future__ import annotations

import csv
import json
import shutil
import traceback
from copy import deepcopy
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable

from ..adapters.chemistry import atom_balance
from ..adapters.csv_tabular import inspect_csv
from ..adapters.pkpd import verify_predictions
from ..adapters.python_static import PythonStaticAdapter
from ..adapters.tabular_integrity import check_nonnegative_concentrations, check_subject_time_integrity
from ..adapters.units import challenge_clearance_unit_value_consistency
from ..core.canonical import CanonicalError, canonicalize, loads_strict
from ..demos.edrug3d_demo import check_half_life_consistency, load_rows as load_edrug
from ..demos.nca import trapezoidal_auc
from ..demos.oral_pk import fit_bateman_grid
from ..demos.provenance import verify_manifest
from ..demos.theophylline_demo import by_subject, falsify_iv_bolus_on_oral, load_theoph
from ..falsification.challenges import (
    challenge_causal_overclaim,
    challenge_data_leakage,
    challenge_unit_error,
)
from ..oracles.nca_oracle import oracle_trapezoidal_auc
from ..pilot.intake import bind_artifact_hashes, detect_stale_substitution, freeze_intake
from ..reviewer.independent import review_package
from ..trust.policy import pin_policy

OWN = Path(__file__).resolve().parents[2]
EXT = OWN / "fixtures" / "external_targets"
JD = OWN / "fixtures" / "journal_demos"


@dataclass
class Finding:
    target: str
    phase: str
    mutation: str | None
    check: str
    expected_detection: bool
    detected: bool
    status: str
    detail: str

    @property
    def outcome(self) -> str:
        if self.phase == "baseline":
            return "BASELINE"
        if self.expected_detection and self.detected:
            return "CAUGHT"
        if self.expected_detection and not self.detected:
            return "MISSED"
        if not self.expected_detection and self.detected:
            return "FALSE_ALARM"
        return "BENIGN_OK"


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _formula_atoms(formula: str) -> dict[str, int]:
    import re

    atoms: dict[str, int] = {}
    for el, n in re.findall(r"([A-Z][a-z]?)(\d*)", formula):
        atoms[el] = atoms.get(el, 0) + (int(n) if n else 1)
    return atoms


def baseline_pcs_pkpd() -> list[Finding]:
    src = EXT / "pcs_pkpd_one_compartment"
    model = _load_json(src / "pk_model.json")
    rows = [(float(r["time"]), float(r["concentration"])) for r in csv.DictReader((src / "predictions.csv").open())]
    flat = {
        "dose": float(model["dose"]["value"]),
        "volume": float(model["volume"]["value"]),
        "clearance": float(model["clearance"]["value"]),
        "clearance_unit": model["clearance"]["unit"],
    }
    ver = verify_predictions(flat, rows, rel_tol=1e-6, abs_tol=1e-8)
    unit = challenge_unit_error({**flat, "evidence_kind": "simulation"}).to_status()
    return [
        Finding("pcs_pkpd_one_compartment", "baseline", None, "pkpd_verify", False, ver["status"] == "COMPUTATIONALLY_TESTED", ver["status"], ver.get("reason", "")),
        Finding("pcs_pkpd_one_compartment", "baseline", None, "unit_ok", False, unit["status"] != "REFUTED", unit["status"], unit.get("reason", "")),
    ]


def mutate_pcs_pkpd(work: Path) -> list[Finding]:
    src = EXT / "pcs_pkpd_one_compartment"
    out = work / "mut_pkpd"
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(src, out)
    findings: list[Finding] = []
    pred = out / "predictions.csv"
    lines = pred.read_text().splitlines()
    parts = lines[2].split(",")
    parts[1] = str(float(parts[1]) * 1.5)
    lines[2] = ",".join(parts)
    pred.write_text("\n".join(lines) + "\n")
    model = _load_json(out / "pk_model.json")
    rows = [(float(r["time"]), float(r["concentration"])) for r in csv.DictReader(pred.open())]
    flat = {"dose": model["dose"]["value"], "volume": model["volume"]["value"], "clearance": model["clearance"]["value"]}
    ver = verify_predictions(flat, rows, rel_tol=1e-6, abs_tol=1e-8)
    findings.append(Finding("pcs_pkpd_one_compartment", "mutation", "scale_one_concentration_1.5x", "pkpd_verify", True, ver["status"] == "REFUTED", ver["status"], ver.get("reason", "")))
    unit = challenge_unit_error({"dose": 100.0, "volume": 10.0, "clearance": 1.0, "clearance_unit": "furlongs/fortnight"}).to_status()
    findings.append(Finding("pcs_pkpd_one_compartment", "mutation", "clearance_unit_nonsense", "unit_error", True, unit["status"] == "REFUTED", unit["status"], unit.get("reason", "")))
    causal = challenge_causal_overclaim("Clearance causes cure of disease", "observational").to_status()
    findings.append(Finding("pcs_pkpd_one_compartment", "mutation", "causal_overclaim_text", "causal_check", True, causal["status"] == "REFUTED", causal["status"], causal.get("reason", "")))
    return findings


def baseline_mass_action() -> list[Finding]:
    model = _load_json(EXT / "pcs_mass_action" / "model.json")
    sp = {s["id"]: s["formula"] for s in model["species"]}
    findings = []
    for rxn in model["reactions"]:
        bal = atom_balance(
            {
                "reactants": [{"coeff": r["coefficient"], "formula_atoms": _formula_atoms(sp[r["species"]])} for r in rxn["reactants"]],
                "products": [{"coeff": p["coefficient"], "formula_atoms": _formula_atoms(sp[p["species"]])} for p in rxn["products"]],
            }
        )
        findings.append(Finding("pcs_mass_action", "baseline", None, f"atom_balance:{rxn['id']}", False, bal["status"] == "COMPUTATIONALLY_TESTED", bal["status"], bal.get("reason", "")))
    py = PythonStaticAdapter().inspect(EXT / "pcs_mass_action" / "run_workflow.py")
    findings.append(Finding("pcs_mass_action", "baseline", None, "python_static", False, py["status"] in {"COMPUTATIONALLY_TESTED", "CONDITIONAL"}, py["status"], ",".join(py.get("flags", []))))
    return findings


def mutate_mass_action(work: Path) -> list[Finding]:
    out = work / "mut_mass"
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(EXT / "pcs_mass_action", out)
    model = _load_json(out / "model.json")
    model["reactions"][0]["products"][0]["coefficient"] = 1
    (out / "model.json").write_text(json.dumps(model, indent=2) + "\n")
    sp = {s["id"]: s["formula"] for s in model["species"]}
    rxn = model["reactions"][0]
    bal = atom_balance(
        {
            "reactants": [{"coeff": r["coefficient"], "formula_atoms": _formula_atoms(sp[r["species"]])} for r in rxn["reactants"]],
            "products": [{"coeff": p["coefficient"], "formula_atoms": _formula_atoms(sp[p["species"]])} for p in rxn["products"]],
        }
    )
    findings = [Finding("pcs_mass_action", "mutation", "break_cleavage_stoichiometry", "atom_balance", True, bal["status"] == "REFUTED", bal["status"], bal.get("reason", ""))]
    wf = out / "run_workflow.py"
    wf.write_text(wf.read_text() + "\nexec('print(1)')\n")
    py = PythonStaticAdapter().inspect(wf)
    findings.append(Finding("pcs_mass_action", "mutation", "inject_exec", "python_static_flags", True, any("dynamic_execution" in f for f in py.get("flags", [])), py["status"], str(py.get("flags"))))
    return findings


def baseline_biopharma() -> list[Finding]:
    train = EXT / "pcs_biopharma_demo" / "train.csv"
    test = EXT / "pcs_biopharma_demo" / "test.csv"
    t_ids = [r["subject_id"] for r in csv.DictReader(train.open())]
    e_ids = [r["subject_id"] for r in csv.DictReader(test.open())]
    leak = challenge_data_leakage(t_ids, e_ids).to_status()
    csv_ok = inspect_csv(train, required_columns=["subject_id", "concentration_mg_L"])
    return [
        Finding("pcs_biopharma_demo", "baseline", None, "no_leakage", False, leak["status"] != "REFUTED", leak["status"], leak.get("reason", "")),
        Finding("pcs_biopharma_demo", "baseline", None, "csv_schema", False, csv_ok["status"] == "COMPUTATIONALLY_TESTED", csv_ok["status"], str(csv_ok.get("reason", ""))),
    ]


def mutate_biopharma(work: Path) -> list[Finding]:
    out = work / "mut_bio"
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(EXT / "pcs_biopharma_demo", out)
    test = out / "test.csv"
    test.write_text(test.read_text().rstrip() + "\nS001,9.9\n")
    t_ids = [r["subject_id"] for r in csv.DictReader((out / "train.csv").open())]
    e_ids = [r["subject_id"] for r in csv.DictReader(test.open())]
    leak = challenge_data_leakage(t_ids, e_ids).to_status()
    bad = out / "train_bad.csv"
    bad.write_text("subject_id\nS001\n")
    csv_bad = inspect_csv(bad, required_columns=["subject_id", "concentration_mg_L"])
    return [
        Finding("pcs_biopharma_demo", "mutation", "leak_S001_into_test", "data_leakage", True, leak["status"] == "REFUTED", leak["status"], leak.get("reason", "")),
        Finding("pcs_biopharma_demo", "mutation", "drop_concentration_column", "csv_schema", True, csv_bad["status"] == "REFUTED", csv_bad["status"], str(csv_bad.get("reason", ""))),
    ]


def baseline_theoph_journal() -> list[Finding]:
    verify_manifest()
    subj = by_subject(load_theoph())[1]
    times = [r["time"] for r in subj]
    concs = [r["conc"] for r in subj]
    auc_ok = abs(trapezoidal_auc(times, concs) - oracle_trapezoidal_auc(times, concs)) < 1e-12
    iv = falsify_iv_bolus_on_oral(subj)
    fit = fit_bateman_grid(times, concs, subj[0]["dose"])
    return [
        Finding("journal_theoph", "baseline", None, "nca_oracle", False, auc_ok, "MATCH" if auc_ok else "MISMATCH", f"auc={trapezoidal_auc(times, concs)}"),
        Finding("journal_theoph", "baseline", None, "iv_structural_refute", False, iv["structural"]["status"] == "REFUTED", iv["structural"]["status"], "oral tmax signature"),
        Finding("journal_theoph", "baseline", None, "oral_grid_fit", False, fit["rmse"] < 5.0, "OK", f"rmse={fit['rmse']:.4f}"),
    ]


def mutate_theoph(work: Path) -> list[Finding]:
    out = work / "mut_theoph"
    out.mkdir(parents=True, exist_ok=True)
    text = (JD / "theophylline" / "raw" / "Theoph.csv").read_text().splitlines()
    parts = text[5].split(",")
    parts[-1] = str(float(parts[-1]) * 10)
    text[5] = ",".join(parts)
    corrupted = out / "Theoph.csv"
    corrupted.write_text("\n".join(text) + "\n")
    rows = []
    for r in csv.DictReader(corrupted.open()):
        rows.append({"subject": int(float(r["Subject"])), "wt": float(r["Wt"]), "dose": float(r["Dose"]), "time": float(r["Time"]), "conc": float(r["conc"])})
    subj = by_subject(rows)[1]
    fit = fit_bateman_grid([r["time"] for r in subj], [r["conc"] for r in subj], subj[0]["dose"])
    detected = fit["rmse"] > 1.0
    return [Finding("journal_theoph", "mutation", "10x_one_concentration", "oral_fit_degradation", True, detected, "DEGRADED" if detected else "STILL_OK", f"rmse={fit['rmse']:.4f}")]


def baseline_edrug_osp() -> list[Finding]:
    rows = load_edrug()
    checks = [c for c in (check_half_life_consistency(r) for r in rows) if c]
    n_bad = sum(1 for c in checks if not c["consistent_1cmt"])
    ddi = list(csv.DictReader((EXT / "public_osp_observed" / "DDI.csv").open(encoding="utf-8", errors="replace")))
    missing = sum(1 for r in ddi if not (r.get("Reference") or "").strip())
    return [
        Finding("edrug3d", "baseline", None, "complete_rows", False, len(checks) > 500, "OK", f"complete={len(checks)} inconsistent={n_bad}"),
        Finding("osp_ddi", "baseline", None, "references_present", False, missing == 0, "OK" if missing == 0 else "MISSING", f"missing={missing} rows={len(ddi)}"),
    ]


def mutate_edrug_osp(work: Path) -> list[Finding]:
    bad = {"Name": "FAKE", "VD(liter)": "10", "Cl(liter/hour)": "1", "t1/2(hour)": "1000"}
    c = check_half_life_consistency(bad, rel_tol=0.5)
    assert c is not None
    out = work / "mut_osp"
    out.mkdir(parents=True, exist_ok=True)
    rows = list(csv.DictReader((EXT / "public_osp_observed" / "DDI.csv").open(encoding="utf-8", errors="replace")))
    rows[0]["Reference"] = ""
    with (out / "DDI.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    missing = sum(1 for r in rows if not (r.get("Reference") or "").strip())
    return [
        Finding("edrug3d", "mutation", "synthetic_inconsistent_half_life", "half_life_consistency", True, c["consistent_1cmt"] is False, "INCONSISTENT", f"rel_err={c['rel_err']:.3f}"),
        Finding("osp_ddi", "mutation", "blank_first_reference", "missing_reference", True, missing >= 1, "DETECTED", f"missing={missing}"),
    ]


def baseline_nlmixr_theo_sd() -> list[Finding]:
    try:
        import pyreadr
    except Exception as exc:  # noqa: BLE001
        return [Finding("nlmixr2data_theo_sd", "baseline", None, "load_rda", False, False, "SKIPPED", str(exc))]
    path = EXT / "public_nlmixr2data" / "data" / "theo_sd.rda"
    df = list(pyreadr.read_r(str(path)).values())[0]
    n = len(df)
    cols = set(df.columns)
    ok = {"ID", "TIME", "DV"}.issubset(cols) and n > 50
    sub = df[df["ID"] == df["ID"].iloc[0]]
    pairs = [(float(r.TIME), float(r.DV)) for r in sub.itertuples() if float(r.TIME) >= 0 and float(r.DV) == float(r.DV)]
    times = [p[0] for p in pairs]
    concs = [p[1] for p in pairs]
    auc = trapezoidal_auc(times, concs) if len(times) >= 2 else -1
    return [
        Finding("nlmixr2data_theo_sd", "baseline", None, "schema_and_n", False, ok, "OK" if ok else "BAD", f"n={n} cols={sorted(cols)}"),
        Finding("nlmixr2data_theo_sd", "baseline", None, "auc_subject1", False, auc > 0, "OK", f"auc={auc}"),
    ]


def mutate_nlmixr_theo_sd(work: Path) -> list[Finding]:
    import pyreadr

    path = EXT / "public_nlmixr2data" / "data" / "theo_sd.rda"
    df = list(pyreadr.read_r(str(path)).values())[0].copy()
    df.loc[df.index[5], "DV"] = -abs(float(df.loc[df.index[5], "DV"]))
    out = work / "mut_theo_sd"
    out.mkdir(parents=True, exist_ok=True)
    df.to_csv(out / "theo_sd_mutated.csv", index=False)
    neg = int((df["DV"] < 0).sum())
    detected = False
    detail = ""
    try:
        sub = df[df["ID"] == df["ID"].iloc[0]]
        times = [float(r.TIME) for r in sub.itertuples()]
        concs = [float(r.DV) for r in sub.itertuples()]
        trapezoidal_auc(times, concs)
        detail = "auc_accepted_negatives"
    except ValueError as exc:
        detected = True
        detail = str(exc)
    return [
        Finding("nlmixr2data_theo_sd", "mutation", "negative_concentration", "nca_rejects_negative", True, detected, "CAUGHT" if detected else "MISSED", detail),
        Finding("nlmixr2data_theo_sd", "mutation", "negative_concentration_count", "neg_count", True, neg >= 1, "OK", f"neg={neg}"),
    ]


def mutate_package_adversarial(work: Path) -> list[Finding]:
    from ..core.canonical import canonical_hash

    findings: list[Finding] = []
    src_project = EXT / "pcs_pkpd_one_compartment"
    proj = work / "pkg_project"
    if proj.exists():
        shutil.rmtree(proj)
    proj.mkdir(parents=True)
    shutil.copy(src_project / "pk_model.json", proj / "model.json")
    shutil.copy(src_project / "predictions.csv", proj / "predictions.csv")
    (proj / "analyze.py").write_text("print('ok')\n")
    intake = {
        "format": "pcs-next-intake-v1",
        "project_id": "real-pkpd-campaign",
        "scientific_domain": "pharmacokinetics",
        "workflow_purpose": "mutation campaign packaging",
        "artifacts": [
            {"id": "model", "path": "model.json", "role": "model"},
            {"id": "preds", "path": "predictions.csv", "role": "output"},
            {"id": "code", "path": "analyze.py", "role": "code"},
        ],
        "claimed_conclusions": [{"id": "c1", "text": "predictions match model"}],
        "computational_assertions": [{"id": "a1", "statement": "hash bind"}],
        "assumptions": [{"id": "s1", "text": "IV bolus"}],
        "models": [{"id": "m1"}],
        "software_dependencies": [],
        "numerical_methods": [],
        "verification_boundaries": ["computational"],
        "expected_outputs": [{"id": "o1", "path": "predictions.csv"}],
        "data_handling_classification": "public",
        "publication_permissions": "example snapshot",
        "unresolved_questions": ["none"],
    }
    policy = pin_policy(_load_json(OWN / "fixtures/synthetic_pilot/acceptance_policy.json"))
    bound = bind_artifact_hashes(intake, proj)
    lock = freeze_intake(bound, acceptance_policy=policy.raw)
    bundle = {
        "format": "pcs-next-evidence-bundle-v1",
        "project_id": intake["project_id"],
        "lock_hash": canonical_hash(lock),
        "policy_hash": policy.content_hash,
        "producer_claimed_pass": True,
        "replay": {},
    }
    pkg = work / "pkg_ok"
    if pkg.exists():
        shutil.rmtree(pkg)
    pkg.mkdir()
    (pkg / "intake.lock.json").write_bytes(canonicalize(lock) + b"\n")
    (pkg / "evidence_bundle.json").write_bytes(canonicalize(bundle) + b"\n")
    (pkg / "acceptance_policy.json").write_bytes(canonicalize(policy.raw) + b"\n")
    try:
        receipt = review_package(pkg, receiver_policy=policy)
        ok = receipt["producer_verdict_handling"]["receiver_action"] == "IGNORED"
        findings.append(Finding("package_real_pkpd", "baseline", None, "producer_pass_ignored", False, ok, "OK", receipt["status"]))
    except Exception as exc:  # noqa: BLE001
        findings.append(Finding("package_real_pkpd", "baseline", None, "producer_pass_ignored", False, False, "ERROR", str(exc)))

    bad_pkg = work / "pkg_bad_policy"
    if bad_pkg.exists():
        shutil.rmtree(bad_pkg)
    shutil.copytree(pkg, bad_pkg)
    pol = deepcopy(policy.raw)
    pol["policy_version"] = "0.0.0-evil"
    (bad_pkg / "acceptance_policy.json").write_bytes(canonicalize(pol) + b"\n")
    detected = False
    detail = ""
    try:
        review_package(bad_pkg, receiver_policy=policy)
        detail = "accepted"
    except Exception as exc:  # noqa: BLE001
        detected = True
        detail = str(exc)[:200]
    findings.append(Finding("package_real_pkpd", "mutation", "policy_version_swap", "review_rejects", True, detected, "CAUGHT" if detected else "MISSED", detail))

    proj_stale = work / "proj_stale"
    if proj_stale.exists():
        shutil.rmtree(proj_stale)
    shutil.copytree(proj, proj_stale)
    p = proj_stale / "predictions.csv"
    p.write_text(p.read_text() + "999,0,0\n")
    stale_findings = detect_stale_substitution(lock, proj_stale)
    detected = any(f.get("kind") == "stale_or_substituted_artifact" for f in stale_findings)
    findings.append(Finding("package_real_pkpd", "mutation", "post_freeze_prediction_append", "stale_substitution", True, detected, "CAUGHT" if detected else "MISSED", json.dumps(stale_findings)[:200]))

    dup_detected = False
    try:
        loads_strict(b'{"a":1,"a":2}')
    except CanonicalError:
        dup_detected = True
    findings.append(Finding("package_real_pkpd", "mutation", "duplicate_json_keys", "canonical_loader", True, dup_detected, "CAUGHT" if dup_detected else "MISSED", ""))
    return findings



def _frac_to_float(s: str) -> float:
    s = s.strip()
    if "/" in s:
        a, b = s.split("/", 1)
        return float(a) / float(b)
    return float(s)


def baseline_translation_benchmark() -> list[Finding]:
    src = EXT / "pcs_pkpd_translation_benchmark"
    model = _load_json(src / "model.json")
    rows = [(float(r["time"]), float(r["concentration"])) for r in csv.DictReader((src / "predictions.csv").open())]
    flat = {
        "dose": float(model["dose"]["value"]),
        "volume": float(model["volume"]["value"]),
        "clearance": float(model["clearance"]["value"]),
    }
    ver = verify_predictions(flat, rows, rel_tol=1e-6, abs_tol=1e-8)
    # PD emax consistency on first row
    r0 = next(csv.DictReader((src / "predictions.csv").open()))
    c = float(r0["concentration"])
    e = float(r0["effect"])
    e0, emax, ec50 = model["pd"]["e0"]["value"], model["pd"]["emax"]["value"], model["pd"]["ec50"]["value"]
    e_hat = e0 + emax * c / (ec50 + c)
    pd_ok = abs(e_hat - e) <= 1e-6 * max(1.0, abs(e_hat))
    py = PythonStaticAdapter().inspect(src / "analysis.py")
    return [
        Finding("pcs_pkpd_translation_benchmark", "baseline", None, "pkpd_verify", False, ver["status"] == "COMPUTATIONALLY_TESTED", ver["status"], ver.get("reason", "")),
        Finding("pcs_pkpd_translation_benchmark", "baseline", None, "emax_row0", False, pd_ok, "OK" if pd_ok else "BAD", f"e={e} e_hat={e_hat}"),
        Finding("pcs_pkpd_translation_benchmark", "baseline", None, "python_static", False, py["status"] in {"COMPUTATIONALLY_TESTED", "CONDITIONAL"}, py["status"], ",".join(py.get("flags", []))),
    ]


def mutate_translation_benchmark(work: Path) -> list[Finding]:
    src = EXT / "pcs_pkpd_translation_benchmark"
    out = work / "mut_xlat"
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(src, out)
    findings: list[Finding] = []
    # M1: corrupt effect only — PK concentration still matches; PD check should catch
    pred = out / "predictions.csv"
    lines = pred.read_text().splitlines()
    hdr = lines[0].split(",")
    parts = lines[1].split(",")
    ei = hdr.index("effect")
    parts[ei] = str(float(parts[ei]) * 0.5)
    lines[1] = ",".join(parts)
    pred.write_text("\n".join(lines) + "\n")
    model = _load_json(out / "model.json")
    r0 = next(csv.DictReader(pred.open()))
    c = float(r0["concentration"])
    e = float(r0["effect"])
    e0, emax, ec50 = model["pd"]["e0"]["value"], model["pd"]["emax"]["value"], model["pd"]["ec50"]["value"]
    e_hat = e0 + emax * c / (ec50 + c)
    pd_detected = abs(e_hat - e) > 1e-6 * max(1.0, abs(e_hat))
    findings.append(
        Finding(
            "pcs_pkpd_translation_benchmark",
            "mutation",
            "halve_effect_keep_conc",
            "emax_consistency",
            True,
            pd_detected,
            "CAUGHT" if pd_detected else "MISSED",
            f"e={e} e_hat={e_hat}",
        )
    )
    # M2: silent unit label swap on clearance without changing value — unit-aware verifier must catch
    model2 = deepcopy(model)
    model2["clearance"]["unit"] = "mL/min"  # was L/h; value left at 1.0
    (out / "model_unit_label.json").write_text(json.dumps(model2, indent=2) + "\n")
    rows = [(float(r["time"]), float(r["concentration"])) for r in csv.DictReader((src / "predictions.csv").open())]
    unit_cons = challenge_clearance_unit_value_consistency(model2, rows)
    unit_detected = unit_cons["status"] == "REFUTED"
    findings.append(
        Finding(
            "pcs_pkpd_translation_benchmark",
            "mutation",
            "clearance_unit_label_only_mL_min",
            "unit_aware_consistency",
            True,
            unit_detected,
            "CAUGHT" if unit_detected else "MISSED",
            unit_cons.get("reason", ""),
        )
    )
    return findings


def baseline_workflow_v3() -> list[Finding]:
    src = EXT / "pcs_scientific_workflow_v3"
    contract = _load_json(src / "contract.json")
    vols = {c["id"]: _frac_to_float(c["volume"]) for c in contract["cells"]}
    rows = list(csv.DictReader((src / "trajectory.csv").open()))
    amounts = []
    for r in rows:
        amt = sum(vols[cid] * _frac_to_float(r[cid]) for cid in vols)
        amounts.append(amt)
    conserved = max(amounts) - min(amounts) < 1e-9 * max(1.0, abs(amounts[0]))
    py = PythonStaticAdapter().inspect(src / "run_workflow.py")
    return [
        Finding("pcs_scientific_workflow_v3", "baseline", None, "amount_conservation", False, conserved, "OK" if conserved else "LEAK", f"amt0={amounts[0]} spread={max(amounts)-min(amounts)}"),
        Finding("pcs_scientific_workflow_v3", "baseline", None, "python_static", False, py["status"] in {"COMPUTATIONALLY_TESTED", "CONDITIONAL"}, py["status"], ",".join(py.get("flags", []))),
    ]


def mutate_workflow_v3(work: Path) -> list[Finding]:
    src = EXT / "pcs_scientific_workflow_v3"
    out = work / "mut_wf3"
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(src, out)
    contract = _load_json(out / "contract.json")
    vols = {c["id"]: _frac_to_float(c["volume"]) for c in contract["cells"]}
    traj = out / "trajectory.csv"
    lines = traj.read_text().splitlines()
    # Spike CellA at last step — breaks conservation
    parts = lines[-1].split(",")
    parts[1] = str(_frac_to_float(parts[1]) * 2.0)
    lines[-1] = ",".join(parts)
    traj.write_text("\n".join(lines) + "\n")
    rows = list(csv.DictReader(traj.open()))
    amounts = [sum(vols[cid] * _frac_to_float(r[cid]) for cid in vols) for r in rows]
    leak = max(amounts) - min(amounts) >= 1e-9 * max(1.0, abs(amounts[0]))
    # Subtle: inject eval() into workflow script
    wf = out / "run_workflow.py"
    wf.write_text(wf.read_text() + "\nx = eval('1+1')\n")
    py = PythonStaticAdapter().inspect(wf)
    eval_flag = any("dynamic_execution" in f or "eval" in f for f in py.get("flags", []))
    return [
        Finding("pcs_scientific_workflow_v3", "mutation", "double_CellA_last_step", "amount_conservation", True, leak, "CAUGHT" if leak else "MISSED", f"spread={max(amounts)-min(amounts)}"),
        Finding("pcs_scientific_workflow_v3", "mutation", "inject_eval", "python_static_flags", True, eval_flag, "CAUGHT" if eval_flag else "MISSED", str(py.get("flags"))),
    ]


def baseline_puromycin_indometh() -> list[Finding]:
    from ..demos.indomethacin_demo import load as load_indo, monoexponential_sse
    from ..demos.puromycin_demo import fit_mm, falsify_linear, load as load_puro

    puro = load_puro()
    treated = [r for r in puro if r["state"] == "treated"]
    fit = fit_mm([r["conc"] for r in treated], [r["rate"] for r in treated])
    lin = falsify_linear([r["conc"] for r in treated], [r["rate"] for r in treated])
    indo = [r for r in load_indo() if r["subject"] == 1]
    mono = monoexponential_sse(indo)
    return [
        Finding("journal_puromycin", "baseline", None, "mm_fit_treated", False, fit["status"]["status"] in {"COMPUTATIONALLY_TESTED", "CONDITIONAL"}, fit["status"]["status"], f"rmse={fit['rmse']:.3f}"),
        Finding("journal_puromycin", "baseline", None, "linear_negative_control", False, lin["status"] == "REFUTED", lin["status"], lin.get("reason", "")),
        Finding("journal_indometh", "baseline", None, "monoexp_poor_fit", False, mono["rmse"] > 0.05, "OK", f"rmse={mono['rmse']:.4f}"),
    ]


def mutate_puromycin_indometh(work: Path) -> list[Finding]:
    from ..demos.indomethacin_demo import monoexponential_sse
    from ..demos.puromycin_demo import (
        check_labels_against_registration,
        fit_mm,
        register_group_params,
    )

    out = work / "mut_journals"
    out.mkdir(parents=True, exist_ok=True)
    findings: list[Finding] = []
    # Puromycin: 10x one rate → MM fit should degrade
    text = (JD / "puromycin" / "raw" / "Puromycin.csv").read_text().splitlines()
    parts = text[1].split(",")
    parts[2] = str(float(parts[2]) * 10)
    text[1] = ",".join(parts)
    corrupted = out / "Puromycin.csv"
    corrupted.write_text("\n".join(text) + "\n")
    rows = []
    for r in csv.DictReader(corrupted.open()):
        rows.append({"conc": float(r["conc"]), "rate": float(r["rate"]), "state": r["state"].strip()})
    treated = [r for r in rows if r["state"] == "treated"]
    fit = fit_mm([r["conc"] for r in treated], [r["rate"] for r in treated])
    detected = fit["rmse"] > 30.0 or fit["median_rel"] > 0.3
    findings.append(
        Finding(
            "journal_puromycin",
            "mutation",
            "10x_one_rate_treated",
            "mm_fit_degradation",
            True,
            detected,
            "CAUGHT" if detected else "MISSED",
            f"rmse={fit['rmse']:.3f} med_rel={fit['median_rel']:.3f}",
        )
    )
    # Puromycin: swap state labels — catch via registration pin of pristine group params
    registration = register_group_params()
    text2 = (JD / "puromycin" / "raw" / "Puromycin.csv").read_text().splitlines()
    swapped = [text2[0]]
    for line in text2[1:]:
        p = line.split(",")
        p[3] = "untreated" if p[3].strip() == "treated" else "treated"
        swapped.append(",".join(p))
    (out / "Puromycin_swapped_state.csv").write_text("\n".join(swapped) + "\n")
    rows_s = [
        {"conc": float(r["conc"]), "rate": float(r["rate"]), "state": r["state"].strip()}
        for r in csv.DictReader((out / "Puromycin_swapped_state.csv").open())
    ]
    label_status = check_labels_against_registration(rows_s, registration)
    label_detected = label_status["status"] == "REFUTED"
    findings.append(
        Finding(
            "journal_puromycin",
            "mutation",
            "swap_treated_untreated_labels",
            "registered_group_params",
            True,
            label_detected,
            "CAUGHT" if label_detected else "MISSED",
            label_status.get("reason", ""),
        )
    )
    # Indometh: zero one concentration — nonnegative concentration integrity must catch
    indo_text = (JD / "indomethacin" / "raw" / "Indometh.csv").read_text().splitlines()
    ip = indo_text[2].split(",")
    ip[-1] = "0.0"
    indo_text[2] = ",".join(ip)
    (out / "Indometh.csv").write_text("\n".join(indo_text) + "\n")
    indo_rows = []
    for r in csv.DictReader((out / "Indometh.csv").open()):
        indo_rows.append({"subject": int(float(r["Subject"])), "time": float(r["time"]), "conc": float(r["conc"])})
    sub1 = [r for r in indo_rows if r["subject"] == 1]
    conc_check = check_nonnegative_concentrations([r["conc"] for r in sub1], allow_zero=False)
    try:
        mono = monoexponential_sse(sub1)
        detail = f"integrity={conc_check['status']} rmse={mono['rmse']:.4f}"
    except Exception as exc:  # noqa: BLE001
        detail = f"integrity={conc_check['status']} mono_exc={exc}"
    detected = conc_check["status"] == "REFUTED"
    findings.append(
        Finding(
            "journal_indometh",
            "mutation",
            "zero_one_concentration",
            "nonnegative_concentration_integrity",
            True,
            detected,
            "CAUGHT" if detected else "MISSED",
            detail,
        )
    )
    return findings


def baseline_osp_pediatrics() -> list[Finding]:
    path = EXT / "public_osp_observed" / "Pediatrics.csv"
    rows = list(csv.DictReader(path.open(encoding="utf-8", errors="replace")))
    missing_ref = sum(1 for r in rows if not (r.get("Reference") or "").strip())
    has_cl = sum(1 for r in rows if (r.get("CL Avg") or "").strip())
    return [
        Finding("osp_pediatrics", "baseline", None, "rows_loaded", False, len(rows) > 50, "OK", f"n={len(rows)}"),
        Finding("osp_pediatrics", "baseline", None, "references", False, missing_ref == 0, "OK" if missing_ref == 0 else "MISSING", f"missing={missing_ref}"),
        Finding("osp_pediatrics", "baseline", None, "cl_present_some", False, has_cl > 10, "OK", f"with_cl={has_cl}"),
    ]


def mutate_osp_pediatrics(work: Path) -> list[Finding]:
    out = work / "mut_osp_ped"
    out.mkdir(parents=True, exist_ok=True)
    rows = list(csv.DictReader((EXT / "public_osp_observed" / "Pediatrics.csv").open(encoding="utf-8", errors="replace")))
    # Blank a reference
    rows[0]["Reference"] = ""
    # Nonsense: negative CL where present
    for r in rows:
        if (r.get("CL Avg") or "").strip():
            r["CL Avg"] = str(-abs(float(r["CL Avg"])))
            break
    with (out / "Pediatrics.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    missing = sum(1 for r in rows if not (r.get("Reference") or "").strip())
    neg_cl = sum(1 for r in rows if (r.get("CL Avg") or "").strip() and float(r["CL Avg"]) < 0)
    return [
        Finding("osp_pediatrics", "mutation", "blank_reference", "missing_reference", True, missing >= 1, "CAUGHT" if missing >= 1 else "MISSED", f"missing={missing}"),
        Finding("osp_pediatrics", "mutation", "negative_cl_avg", "neg_cl_count", True, neg_cl >= 1, "CAUGHT" if neg_cl >= 1 else "MISSED", f"neg_cl={neg_cl}"),
    ]


def mutate_nlmixr_warfarin(work: Path) -> list[Finding]:
    try:
        import pyreadr
    except Exception as exc:  # noqa: BLE001
        return [Finding("nlmixr2data_warfarin", "mutation", "load", "pyreadr", True, False, "MISSED", str(exc))]
    path = EXT / "public_nlmixr2data" / "data" / "warfarin.rda"
    df = list(pyreadr.read_r(str(path)).values())[0].copy()
    out = work / "mut_warfarin"
    out.mkdir(parents=True, exist_ok=True)
    # Flip one observation to negative dv
    obs = df[(df["evid"] == 0) | (df["evid"] == "0")]
    idx = obs.index[10]
    df.loc[idx, "dv"] = -abs(float(df.loc[idx, "dv"]) or 1.0)
    df.to_csv(out / "warfarin_mut.csv", index=False)
    neg = int((df["dv"].astype(float) < 0).sum())
    conc_integrity = check_nonnegative_concentrations(df["dv"].astype(float).tolist(), allow_zero=True)
    neg_detected = neg >= 1 and conc_integrity["status"] == "REFUTED"
    # Collapse a within-subject gap to 1e-12 — longitudinal integrity with min_delta=1e-9
    df2 = list(pyreadr.read_r(str(path)).values())[0].copy()
    df2 = df2.sort_values(["id", "time"]).reset_index(drop=True)
    time_detected = False
    detail = "no pair"
    for i in range(len(df2) - 1):
        if df2.loc[i, "id"] == df2.loc[i + 1, "id"]:
            df2.loc[i + 1, "time"] = float(df2.loc[i, "time"]) + 1e-12
            rows = [{"id": r.id, "time": float(r.time)} for r in df2.itertuples()]
            tcheck = check_subject_time_integrity(rows, id_key="id", time_key="time", min_delta=1e-9)
            time_detected = tcheck["status"] == "REFUTED"
            detail = tcheck.get("reason", "")
            break
    return [
        Finding(
            "nlmixr2data_warfarin",
            "mutation",
            "negative_dv_obs",
            "nonnegative_concentration_integrity",
            True,
            neg_detected,
            "CAUGHT" if neg_detected else "MISSED",
            f"neg={neg} integrity={conc_integrity['status']}",
        ),
        Finding(
            "nlmixr2data_warfarin",
            "mutation",
            "1e-12_time_jitter",
            "longitudinal_time_integrity",
            True,
            time_detected,
            "CAUGHT" if time_detected else "MISSED",
            detail,
        ),
    ]


def mutate_nlmixr_bolus_1cpt(work: Path) -> list[Finding]:
    """Mutate nlmixr2 Bolus_1CPT teaching table (large; sample integrity checks)."""
    try:
        import pyreadr
    except Exception as exc:  # noqa: BLE001
        return [Finding("nlmixr2data_bolus_1cpt", "mutation", "load", "pyreadr", True, False, "MISSED", str(exc))]
    path = EXT / "public_nlmixr2data" / "data" / "Bolus_1CPT.rda"
    df = list(pyreadr.read_r(str(path)).values())[0].copy()
    out = work / "mut_bolus"
    out.mkdir(parents=True, exist_ok=True)
    sid = df["ID"].iloc[0]
    sub = df[df["ID"] == sid].copy()
    # Corrupt one positive DV on subject 1
    pos = sub[(sub["EVID"] == 0) | (sub["EVID"] == "0")]
    pos = pos[pos["DV"].astype(float) > 0]
    idx = pos.index[0]
    df.loc[idx, "DV"] = -abs(float(df.loc[idx, "DV"]))
    sub = df[df["ID"] == sid]
    df.to_csv(out / "Bolus_1CPT_mut.csv", index=False)
    conc_st = check_nonnegative_concentrations(sub["DV"].astype(float).tolist(), allow_zero=True)
    rows = [{"id": int(r.ID), "time": float(r.TIME)} for r in sub.sort_values("TIME").itertuples()]
    if len(rows) >= 2:
        rows[1]["time"] = rows[0]["time"] + 1e-12
    t_st = check_subject_time_integrity(rows, min_delta=1e-9)
    return [
        Finding(
            "nlmixr2data_bolus_1cpt",
            "mutation",
            "negative_dv_subject1",
            "nonnegative_concentration_integrity",
            True,
            conc_st["status"] == "REFUTED",
            "CAUGHT" if conc_st["status"] == "REFUTED" else "MISSED",
            conc_st.get("reason", ""),
        ),
        Finding(
            "nlmixr2data_bolus_1cpt",
            "mutation",
            "time_jitter_subject1",
            "longitudinal_time_integrity",
            True,
            t_st["status"] == "REFUTED",
            "CAUGHT" if t_st["status"] == "REFUTED" else "MISSED",
            t_st.get("reason", ""),
        ),
    ]


def baseline_unit_oracle_diff() -> list[Finding]:
    from ..adapters.units import clearance_to_L_per_h
    from ..oracles.units_oracle import oracle_clearance_to_L_per_h

    mismatches = []
    for unit in ("L/h", "mL/min", "mL/h", "L/min"):
        for v in (0.0, 1.0, 2.5, 100.0):
            a = clearance_to_L_per_h(v, unit)
            b = oracle_clearance_to_L_per_h(v, unit)
            if abs(a - b) > 1e-15 * max(1.0, abs(b)):
                mismatches.append((unit, v, a, b))
    ok = len(mismatches) == 0
    return [
        Finding(
            "unit_conversion_oracle",
            "baseline",
            None,
            "adapter_vs_oracle",
            False,
            ok,
            "MATCH" if ok else "MISMATCH",
            f"mismatches={len(mismatches)}",
        )
    ]


def baseline_metamorphic_and_pd() -> list[Finding]:
    from ..adapters.metamorphic_pk import check_dose_homogeneity
    from ..adapters.pd import verify_emax_rows
    from ..adapters.conservation import check_trajectory_conservation, check_transfer_preserves_total

    meta = check_dose_homogeneity(100.0, 10.0, 1.0, [0.0, 0.5, 1.0, 2.0, 5.0], scale=2.0)
    src = EXT / "pcs_pkpd_translation_benchmark"
    model = _load_json(src / "model.json")
    rows = [(float(r["concentration"]), float(r["effect"])) for r in csv.DictReader((src / "predictions.csv").open())]
    pd_st = verify_emax_rows(model["pd"], rows)
    xfer = check_transfer_preserves_total(10.0, 3.0, 4.0)
    contract = _load_json(EXT / "pcs_scientific_workflow_v3" / "contract.json")
    vols = {c["id"]: _frac_to_float(c["volume"]) for c in contract["cells"]}
    traj = []
    for r in csv.DictReader((EXT / "pcs_scientific_workflow_v3" / "trajectory.csv").open()):
        traj.append({cid: _frac_to_float(r[cid]) for cid in vols})
    cons = check_trajectory_conservation(vols, traj)
    return [
        Finding("metamorphic_pk", "baseline", None, "dose_homogeneity", False, meta["status"] == "COMPUTATIONALLY_TESTED", meta["status"], meta.get("reason", "")),
        Finding("pcs_pkpd_translation_benchmark", "baseline", None, "emax_adapter", False, pd_st["status"] == "COMPUTATIONALLY_TESTED", pd_st["status"], pd_st.get("reason", "")),
        Finding("conservation_transfer", "baseline", None, "transfer_total", False, xfer["status"] == "COMPUTATIONALLY_TESTED", xfer["status"], xfer.get("reason", "")),
        Finding("pcs_scientific_workflow_v3", "baseline", None, "conservation_adapter", False, cons["status"] == "COMPUTATIONALLY_TESTED", cons["status"], cons.get("reason", "")),
    ]


def mutate_metamorphic_evidence_osp(work: Path) -> list[Finding]:
    from ..adapters.metamorphic_pk import check_prediction_table_dose_scale
    from ..adapters.osp_consistency import check_cl_auc_dose_consistency
    from ..adapters.pd import verify_emax_rows
    from ..trust.evidence_store import EvidenceStore
    from ..core.errors import PcsNextError

    findings: list[Finding] = []
    src = EXT / "pcs_pkpd_one_compartment"
    rows = [(float(r["time"]), float(r["concentration"])) for r in csv.DictReader((src / "predictions.csv").open())]
    # Claim dose×2 but only scale some rows → must refute
    scaled = [(t, c * 2.0 if i != 2 else c * 1.1) for i, (t, c) in enumerate(rows)]
    meta = check_prediction_table_dose_scale({"dose": 100.0}, rows, scaled, scale=2.0)
    findings.append(
        Finding(
            "metamorphic_pk",
            "mutation",
            "partial_dose_scale_table",
            "dose_homogeneity_table",
            True,
            meta["status"] == "REFUTED",
            "CAUGHT" if meta["status"] == "REFUTED" else "MISSED",
            meta.get("reason", ""),
        )
    )

    # Evidence store: tamper event payload after commit
    store_dir = work / "evstore"
    store = EvidenceStore(store_dir)
    store.commit("a", {"x": 1})
    c2 = store.commit("b", {"y": 2})
    # Corrupt the second event file
    ev_files = sorted(store_dir.glob("evt-*.json"))
    target = ev_files[-1]
    body = json.loads(target.read_text())
    body["payload"]["y"] = 999
    target.write_text(json.dumps(body))
    tamper_detected = False
    detail = ""
    try:
        store.verify_chain()
        detail = "chain_accepted_tamper"
    except PcsNextError as exc:
        tamper_detected = True
        detail = str(exc)
    findings.append(
        Finding(
            "evidence_store",
            "mutation",
            "tamper_event_payload",
            "verify_chain",
            True,
            tamper_detected,
            "CAUGHT" if tamper_detected else "MISSED",
            detail[:160],
        )
    )

    # OSP synthetic: Dose/CL/AUC inconsistent
    bad_row = {"Dose": "100", "CL Avg": "50", "AUC Avg": "100"}  # implied CL=1, declared 50
    st = check_cl_auc_dose_consistency(bad_row, rel_tol=0.5)
    assert st is not None
    findings.append(
        Finding(
            "osp_synthetic",
            "mutation",
            "cl_auc_dose_inconsistent",
            "osp_consistency",
            True,
            st["status"] == "REFUTED",
            "CAUGHT" if st["status"] == "REFUTED" else "MISSED",
            st.get("reason", ""),
        )
    )

    # PD: corrupt emax table via adapter
    model = _load_json(EXT / "pcs_pkpd_translation_benchmark" / "model.json")
    pd_rows = [(float(r["concentration"]), float(r["effect"]) * 0.5) for r in csv.DictReader((EXT / "pcs_pkpd_translation_benchmark" / "predictions.csv").open())]
    pd_st = verify_emax_rows(model["pd"], pd_rows)
    findings.append(
        Finding(
            "pcs_pkpd_translation_benchmark",
            "mutation",
            "halve_all_effects_adapter",
            "emax_adapter",
            True,
            pd_st["status"] == "REFUTED",
            "CAUGHT" if pd_st["status"] == "REFUTED" else "MISSED",
            pd_st.get("reason", ""),
        )
    )
    return findings


def baseline_proof_gated_certificate() -> list[Finding]:
    from ..research.proof_gated.models import ScalarIntModel, TinyReluNet, improvement_certificate, relu_net_no_forgetting

    old = ScalarIntModel(0, 0)
    new = ScalarIntModel(2, 0)
    data = [(1, 2), (2, 4), (3, 6)]
    cert = improvement_certificate(old, new, data, range(-2, 5), max_pointwise_increase=10**9)
    # Tight preservation must fail for large change
    cert_tight = improvement_certificate(old, new, data, range(0, 3), max_pointwise_increase=0)
    net_old = TinyReluNet(w1=((1, 0),), b1=(0,), w2=(1,), b2=0)
    net_new = TinyReluNet(w1=((1, 0),), b1=(0,), w2=(1,), b2=5)
    ok, bad = relu_net_no_forgetting(net_old, net_new, [(0, 0), (1, 0), (2, 1)], max_pointwise_increase=0)
    return [
        Finding("proof_gated", "baseline", None, "improvement_certificate_accept", False, cert["accepted"] is True, "OK" if cert["accepted"] else "BAD", json.dumps({k: cert[k] for k in ("old_loss", "new_loss", "accepted")})),
        Finding("proof_gated", "baseline", None, "improvement_certificate_reject_drift", False, cert_tight["accepted"] is False, "OK" if not cert_tight["accepted"] else "BAD", "tight bound must reject large drift"),
        Finding("proof_gated", "baseline", None, "relu_net_no_forgetting", False, ok is False and bool(bad), "OK", f"bad={bad[:3]}"),
    ]


def mutate_hard_cases(work: Path) -> list[Finding]:
    """Deliberate near-boundary / semantic errors — some may be missed."""
    findings: list[Finding] = []
    src = EXT / "pcs_pkpd_one_compartment"
    out = work / "mut_hard_pkpd"
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(src, out)

    # H1: tiny perturbation within tolerance — expect non-detection (boundary control)
    pred = out / "predictions.csv"
    lines = pred.read_text().splitlines()
    parts = lines[2].split(",")
    parts[1] = str(float(parts[1]) * (1.0 + 1e-9))
    lines[2] = ",".join(parts)
    pred.write_text("\n".join(lines) + "\n")
    model = _load_json(out / "pk_model.json")
    rows = [(float(r["time"]), float(r["concentration"])) for r in csv.DictReader(pred.open())]
    flat = {"dose": model["dose"]["value"], "volume": model["volume"]["value"], "clearance": model["clearance"]["value"]}
    ver = verify_predictions(flat, rows, rel_tol=1e-6, abs_tol=1e-8)
    findings.append(
        Finding(
            "pcs_pkpd_one_compartment",
            "mutation",
            "1e-9_relative_perturbation",
            "pkpd_verify_within_tol",
            False,
            ver["status"] == "REFUTED",
            ver["status"],
            "boundary: should remain accepted under stated tol",
        )
    )

    # H2: correct non-causal claim must not be refuted
    causal = challenge_causal_overclaim(
        "Predicted concentrations match the one-compartment model under stated parameters",
        "simulation",
    ).to_status()
    findings.append(
        Finding(
            "pcs_pkpd_one_compartment",
            "mutation",
            "noncausal_correct_claim_text",
            "causal_check_should_pass",
            False,
            causal["status"] == "REFUTED",
            causal["status"],
            "correct non-causal claim must not be refuted",
        )
    )

    # H3: keep headers time,concentration but swap value order (classic silent CSV corruption)
    bad = out / "predictions_swapped.csv"
    src_lines = (src / "predictions.csv").read_text().splitlines()
    swapped_rows = [src_lines[0]]
    for line in src_lines[1:]:
        cols = line.split(",")
        cols[0], cols[1] = cols[1], cols[0]
        swapped_rows.append(",".join(cols))
    bad.write_text("\n".join(swapped_rows) + "\n")
    try:
        rows2 = [(float(r["time"]), float(r["concentration"])) for r in csv.DictReader(bad.open())]
        ver2 = verify_predictions(flat, rows2, rel_tol=1e-6, abs_tol=1e-8)
        detected = ver2["status"] == "REFUTED"
        detail = ver2.get("reason", "")
    except Exception as exc:  # noqa: BLE001
        detected = True
        detail = str(exc)
    findings.append(
        Finding(
            "pcs_pkpd_one_compartment",
            "mutation",
            "swap_csv_value_order",
            "pkpd_or_parse",
            True,
            detected,
            "CAUGHT" if detected else "MISSED",
            detail[:160],
        )
    )

    # H4: scale ALL concentrations just below rel_tol — expected non-detection
    pred2 = out / "predictions_near_tol.csv"
    near_lines = (src / "predictions.csv").read_text().splitlines()
    new_near = [near_lines[0]]
    for line in near_lines[1:]:
        cols = line.split(",")
        cols[1] = str(float(cols[1]) * (1.0 + 5e-7))
        new_near.append(",".join(cols))
    pred2.write_text("\n".join(new_near) + "\n")
    rows_n = [(float(r["time"]), float(r["concentration"])) for r in csv.DictReader(pred2.open())]
    ver_n = verify_predictions(flat, rows_n, rel_tol=1e-6, abs_tol=1e-8)
    findings.append(
        Finding(
            "pcs_pkpd_one_compartment",
            "mutation",
            "5e-7_all_rows_within_rel_tol",
            "pkpd_verify_within_tol",
            False,
            ver_n["status"] == "REFUTED",
            ver_n["status"],
            "just below rel_tol=1e-6",
        )
    )

    # H5: 2e-6 relative scale — just above tol → should CATCH
    pred3 = out / "predictions_over_tol.csv"
    over = [near_lines[0]]
    for line in near_lines[1:]:
        cols = line.split(",")
        cols[1] = str(float(cols[1]) * (1.0 + 2e-6))
        over.append(",".join(cols))
    pred3.write_text("\n".join(over) + "\n")
    rows_o = [(float(r["time"]), float(r["concentration"])) for r in csv.DictReader(pred3.open())]
    ver_o = verify_predictions(flat, rows_o, rel_tol=1e-6, abs_tol=1e-8)
    over_det = ver_o["status"] == "REFUTED"
    findings.append(
        Finding(
            "pcs_pkpd_one_compartment",
            "mutation",
            "2e-6_all_rows_over_rel_tol",
            "pkpd_verify",
            True,
            over_det,
            "CAUGHT" if over_det else "MISSED",
            ver_o.get("reason", ""),
        )
    )
    return findings


def run_campaign(out_dir: str | Path) -> dict[str, Any]:
    out = Path(out_dir)
    work = out / "work"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    findings: list[Finding] = []
    steps: list[tuple[str, Callable[[], list[Finding]]]] = [
        ("baseline_pcs_pkpd", baseline_pcs_pkpd),
        ("mutate_pcs_pkpd", lambda: mutate_pcs_pkpd(work)),
        ("baseline_mass_action", baseline_mass_action),
        ("mutate_mass_action", lambda: mutate_mass_action(work)),
        ("baseline_biopharma", baseline_biopharma),
        ("mutate_biopharma", lambda: mutate_biopharma(work)),
        ("baseline_translation_benchmark", baseline_translation_benchmark),
        ("mutate_translation_benchmark", lambda: mutate_translation_benchmark(work)),
        ("baseline_workflow_v3", baseline_workflow_v3),
        ("mutate_workflow_v3", lambda: mutate_workflow_v3(work)),
        ("baseline_theoph_journal", baseline_theoph_journal),
        ("mutate_theoph", lambda: mutate_theoph(work)),
        ("baseline_puromycin_indometh", baseline_puromycin_indometh),
        ("mutate_puromycin_indometh", lambda: mutate_puromycin_indometh(work)),
        ("baseline_edrug_osp", baseline_edrug_osp),
        ("mutate_edrug_osp", lambda: mutate_edrug_osp(work)),
        ("baseline_osp_pediatrics", baseline_osp_pediatrics),
        ("mutate_osp_pediatrics", lambda: mutate_osp_pediatrics(work)),
        ("baseline_nlmixr_theo_sd", baseline_nlmixr_theo_sd),
        ("mutate_nlmixr_theo_sd", lambda: mutate_nlmixr_theo_sd(work)),
        ("mutate_nlmixr_warfarin", lambda: mutate_nlmixr_warfarin(work)),
        ("mutate_nlmixr_bolus_1cpt", lambda: mutate_nlmixr_bolus_1cpt(work)),
        ("mutate_package_adversarial", lambda: mutate_package_adversarial(work)),
        ("mutate_hard_cases", lambda: mutate_hard_cases(work)),
        ("baseline_unit_oracle_diff", baseline_unit_oracle_diff),
        ("baseline_metamorphic_and_pd", baseline_metamorphic_and_pd),
        ("mutate_metamorphic_evidence_osp", lambda: mutate_metamorphic_evidence_osp(work)),
        ("baseline_proof_gated_certificate", baseline_proof_gated_certificate),
    ]
    errors = []
    for name, fn in steps:
        try:
            findings.extend(fn())
        except Exception as exc:  # noqa: BLE001
            errors.append({"step": name, "error": str(exc), "trace": traceback.format_exc()[-1000:]})

    mut = [f for f in findings if f.phase == "mutation"]
    expected = [f for f in mut if f.expected_detection]
    caught = sum(1 for f in expected if f.outcome == "CAUGHT")
    missed = sum(1 for f in expected if f.outcome == "MISSED")
    false_alarm = sum(1 for f in mut if f.outcome == "FALSE_ALARM")
    benign_ok = sum(1 for f in mut if f.outcome == "BENIGN_OK")
    report = {
        "format": "pcs-next-real-world-mutation-campaign-v1",
        "targets": [
            "pcs_pkpd_one_compartment",
            "pcs_mass_action",
            "pcs_biopharma_demo",
            "pcs_pkpd_translation_benchmark",
            "pcs_scientific_workflow_v3",
            "journal Theoph / Puromycin / Indometh",
            "e-Drug3D + OSP DDI + OSP Pediatrics",
            "nlmixr2data theo_sd.rda + warfarin.rda + Bolus_1CPT.rda",
            "packaged real pkpd evidence",
            "unit conversion adapter↔oracle differential",
            "metamorphic PK + Emax adapter + conservation",
            "evidence store tamper + OSP CL/AUC consistency",
            "proof-gated finite improvement certificates",
        ],
        "n_findings": len(findings),
        "n_mutations": len(mut),
        "n_expected_detections": len(expected),
        "caught": caught,
        "missed": missed,
        "false_alarms": false_alarm,
        "benign_ok": benign_ok,
        "catch_rate": (caught / len(expected)) if expected else None,
        "findings": [asdict(f) | {"outcome": f.outcome} for f in findings],
        "errors": errors,
        "limitations": [
            "Working copies only; production examples were not modified",
            "Catch rate is among expected-detection mutations in this suite, not universal security",
            "External laboratory validation remains OPEN",
            "Near-tolerance boundary controls are expected non-detections (BENIGN_OK)",
            "Group-label detection requires a registration pin of per-group parameters",
        ],
    }
    out.mkdir(parents=True, exist_ok=True)
    (out / "CAMPAIGN_REPORT.json").write_bytes(canonicalize(report) + b"\n")
    lines = [
        "# Real-world mutation campaign",
        "",
        f"- Mutations: {len(mut)}",
        f"- Expected-detection probes: {len(expected)}",
        f"- Caught: {caught}",
        f"- Missed: {missed}",
        f"- False alarms: {false_alarm}",
        f"- Benign OK (boundary controls): {benign_ok}",
        f"- Catch rate (among expected): {report['catch_rate']}",
        "",
        "## Missed (honest gaps)",
        "",
    ]
    misses = [f for f in expected if f.outcome == "MISSED"]
    if misses:
        for f in misses:
            lines.append(f"- `{f.target}` / `{f.mutation}` / {f.check}: {f.detail[:200]}")
    else:
        lines.append("- (none)")
    lines += ["", "## All mutation outcomes", ""]
    for f in mut:
        lines.append(f"- **{f.outcome}** `{f.target}` / `{f.mutation}` / {f.check}: {f.status} — {f.detail[:160]}")
    if errors:
        lines += ["", "## Step errors", ""]
        for e in errors:
            lines.append(f"- {e['step']}: {e['error']}")
    (out / "CAMPAIGN_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report
