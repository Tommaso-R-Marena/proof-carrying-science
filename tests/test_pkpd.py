import csv
import json
import math
from pathlib import Path

from pcs.adapters.pkpd import validate_one_compartment_iv, verify_one_compartment_iv_output
from pcs.kernel import build_certificate, verify_certificate


def spec():
    return {
        "model_type":"one_compartment_iv_bolus","dose":{"value":100.0,"unit":"mg"},"volume":{"value":10.0,"unit":"L"},
        "clearance":{"value":1.0,"unit":"L/h"},"time_unit":"h","concentration_unit":"mg/L",
        "pd":{"model_type":"direct_emax","e0":{"value":0.0,"unit":"1"},"emax":{"value":100.0,"unit":"1"},"ec50":{"value":2.0,"unit":"mg/L"},"effect_unit":"1"}
    }


def write_predictions(path: Path, *, tamper=False):
    with path.open("w", newline="", encoding="utf-8") as f:
        w=csv.writer(f); w.writerow(["time","concentration","effect"])
        for t in [0.0,1.0,4.0,12.0]:
            c=10.0*math.exp(-0.1*t); e=100.0*c/(2.0+c)
            if tamper and t==4.0: c+=0.25
            w.writerow([t,c,e])


def test_pkpd_contract_accepts_canonical_units():
    ok,details=validate_one_compartment_iv(spec()); assert ok; assert details["derived"]["kel_per_s"]>0


def test_pkpd_contract_rejects_wrong_clearance_dimension():
    s=spec(); s["clearance"]={"value":1.0,"unit":"mg/h"}
    ok,details=validate_one_compartment_iv(s); assert not ok; assert "expected" in details["message"]


def test_pkpd_contract_rejects_pd_ec50_wrong_dimension():
    s=spec(); s["pd"]["ec50"]={"value":2.0,"unit":"h"}
    ok,details=validate_one_compartment_iv(s); assert not ok; assert "expected" in details["message"]


def test_pkpd_output_replay_rejects_effect_tamper(tmp_path):
    p=tmp_path/"pred.csv"; write_predictions(p)
    rows=list(csv.reader(p.open("r",encoding="utf-8"))); rows[2][2]=str(float(rows[2][2])+5.0)
    with p.open("w",newline="",encoding="utf-8") as f: csv.writer(f).writerows(rows)
    ok,details=verify_one_compartment_iv_output(spec(),p)
    assert not ok; assert any(m["field"]=="effect" for m in details["mismatches"])


def test_pkpd_output_replay_accepts_reference(tmp_path):
    p=tmp_path/"pred.csv"; write_predictions(p)
    ok,details=verify_one_compartment_iv_output(spec(),p); assert ok; assert details["row_count"]==4


def test_pkpd_output_replay_rejects_tamper(tmp_path):
    p=tmp_path/"pred.csv"; write_predictions(p,tamper=True)
    ok,details=verify_one_compartment_iv_output(spec(),p); assert not ok; assert details["mismatches"]


def test_pkpd_certificate_replays_adapter(tmp_path):
    model=tmp_path/"model.json"; model.write_text(json.dumps(spec()),encoding="utf-8")
    pred=tmp_path/"predictions.csv"; write_predictions(pred)
    manifest={
      "subject":"synthetic-one-compartment-pk",
      "assumptions":[{"id":"A1","statement":"Restricted one-compartment IV-bolus model is the declared computational model."}],
      "claims":[
        {"id":"C1","statement":"The model specification satisfies the restricted PK unit/positivity contract.","kind":"computational","required_evidence":["E1"],"assumptions":["A1"],"predicate":{"type":"pkpd_contract","model_artifact":"model"}},
        {"id":"C2","statement":"The prediction artifact matches the restricted analytic model within tolerance.","kind":"computational","required_evidence":["E2"],"assumptions":["A1"],"predicate":{"type":"pkpd_reference_match","model_artifact":"model","output_artifact":"pred","time_column":"time","concentration_column":"concentration","effect_column":"effect","rel_tol":1e-9,"abs_tol":1e-12}}
      ],
      "artifacts":[{"id":"model","path":"model.json","role":"pk-model","media_type":"application/json"},{"id":"pred","path":"predictions.csv","role":"pk-predictions","media_type":"text/csv"}],
      "checks":[{"id":"E1","type":"pkpd_contract","claim_ids":["C1"],"model_artifact":"model"},{"id":"E2","type":"pkpd_reference_match","claim_ids":["C2"],"model_artifact":"model","output_artifact":"pred","time_column":"time","concentration_column":"concentration","effect_column":"effect","rel_tol":1e-9,"abs_tol":1e-12}],
      "workflow":{"nodes":[]}
    }
    mp=tmp_path/"manifest.json"; mp.write_text(json.dumps(manifest),encoding="utf-8")
    out=tmp_path/"evidence"; cert=build_certificate(mp,out)
    assert cert["claims"][0]["assessment"]["status"]=="COMPUTATIONALLY_SUPPORTED"
    assert cert["claims"][1]["assessment"]["status"]=="COMPUTATIONALLY_SUPPORTED"
    result=verify_certificate(out/"certificate.json"); assert result["valid"], result["errors"]
