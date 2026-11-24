"""Live end-to-end checks of ClaimCheck v1.1 with the real Lean 4.28.0 kernel.  Never skips.

    python -m research.claimcheck_v1_1.check_live_v11 [--out report.json]

1. One command path: gates -> kernel -> policy -> bundle, on a small table, with the expected
   outward verdicts, then the independent replay of that bundle.
2. Tampering: a forged or stale bundle must fail the independent replay (upgraded verdict, edited
   findings, substituted data, edited checker, forged kernel outcome, removed corroboration, a
   record moved to another bundle).
3. Resource exhaustion and interruption: a killed, hung or silent Lean process can only yield
   UNKNOWN, never a positive result.
4. The stand-alone kernel runner accepts a real proof file; rejects a forged outcome (Lean refuses
   it); and refuses a forged generated part that defines its own `run` before Lean starts.
5. Hardening after the 2026-11-17 security review: the receipt lists every claim's settings; with
   a scale the page never writes, the kernel accepts exactly one of the two verdicts and the receipt
   flags the scale; a too-small --max-memory-mb is refused; the receipt records which `lean` ran.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

from ..claimcheck_v1.lean import checker_sha256, find_lean, lean_version
from ..claimcheck_v1.spec import canonical, sha256_hex
from .tests.test_v11_offline import DATA, MANIFEST
from .verify import verify, write_bundle_v11

HERE = Path(__file__).resolve().parent
SENTENCES = ["Mean body mass was 14.76 g (range 11.95–18.09 g) across the 12 individuals.",
             "In a second report the mean body length was 111.2 mm (range 99.7–121.6 mm).",
             "The median age was 4 in this sample."]
TEXT = "\n\n".join(SENTENCES)
PROPOSALS = [("c001", {"quote": SENTENCES[0], "spec": {"stat": "mean", "reported": "14.76", "column": "mass"}}, "live check"),
             ("c002", {"quote": SENTENCES[1], "spec": {"stat": "mean", "reported": "111.2", "column": "length"}}, "live check"),
             ("c003", {"quote": SENTENCES[2], "spec": {"stat": "median", "reported": "4", "column": "age"}}, "live check")]
EXPECTED = {"c001": ("CONFIRMATION", "MATCH_PROVED"), "c002": ("DISCREPANCY_FOR_REVIEW", "MISMATCH_PROVED"), "c003": ("REQUIRE_HUMAN_REVIEW", "MATCH_PROVED")}


def make_bundle(out: Path, **kw) -> dict:
    result = verify(PROPOSALS, source_text=TEXT, source_meta={"name": "live"}, data=DATA, manifest=MANIFEST,
                    keep_dir=out / "v1" / "obligations", **kw)
    write_bundle_v11(out, result, source_text=TEXT, data=DATA, manifest=MANIFEST, source_name="live.txt", data_name="live.csv")
    return result


def replay(bundle: Path) -> tuple[bool, dict]:
    proc = subprocess.run([sys.executable, str(HERE / "replay_independent_v1_1.py"), str(bundle), "--checker-sha256", checker_sha256()],
                          capture_output=True, text=True)
    return proc.returncode == 0, json.loads(proc.stdout)


def _reseal_v1(bundle: Path) -> None:
    """What a careful forger would do: make every digest in the indexes consistent again."""
    index = json.loads((bundle / "v1" / "bundle.json").read_text(encoding="utf-8"))
    for name in index["files"]:
        raw = (bundle / "v1" / name).read_bytes()
        index["files"][name] = {"sha256": sha256_hex(raw), "bytes": len(raw)}
    (bundle / "v1" / "bundle.json").write_text(json.dumps(index, indent=1, sort_keys=True), encoding="utf-8")


def _reseal(bundle: Path, records: list | None = None) -> None:
    if records is not None:
        for r in records:
            r["record_sha256"] = sha256_hex(canonical({k: v for k, v in r.items() if k != "record_sha256"}))
        (bundle / "records.json").write_text(json.dumps(records, indent=1, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    index = json.loads((bundle / "claimcheck_v1_1.json").read_text(encoding="utf-8"))
    for name in index["files"]:
        index["files"][name] = sha256_hex((bundle / name).read_bytes())
    (bundle / "claimcheck_v1_1.json").write_text(json.dumps(index, indent=1, sort_keys=True), encoding="utf-8")


def tamper_cases(good: Path, other: Path, work: Path) -> dict:
    out = {}

    def case(name: str, edit) -> None:
        target = work / name
        shutil.copytree(good, target)
        edit(target)
        ok, summary = replay(target)
        problems = summary["bundle_problems"] + [i for r in summary["records"] for i in r["issues"]]
        out[name] = {"replay_rejected": not ok, "first_problem": (problems or ["(v1 replay failed)"])[0][:160]}

    def upgrade(b):
        recs = json.loads((b / "records.json").read_text(encoding="utf-8"))
        r = next(x for x in recs if x["claim_id"] == "c003")
        r["outward"]["verdict"] = "CONFIRMATION"
        _reseal(b, recs)

    def edit_findings(b):
        recs = json.loads((b / "records.json").read_text(encoding="utf-8"))
        r = next(x for x in recs if x["claim_id"] == "c003")
        for f in r["source_reading"]["findings"]:
            f["passed"] = True
        r["outward"]["verdict"] = "CONFIRMATION"
        _reseal(b, recs)

    def substitute_data(b):
        path = b / "v1" / "data.csv"
        path.write_bytes(path.read_bytes().replace(b"12.31", b"12.41"))
        _reseal_v1(b)
        _reseal(b)

    def edit_checker(b):
        path = b / "v1" / "ClaimCheck.lean"
        path.write_bytes(path.read_bytes() + b"\n-- edited\n")
        _reseal_v1(b)
        _reseal(b)

    def forge_outcome(b):
        receipts = json.loads((b / "v1" / "receipts.json").read_text(encoding="utf-8"))
        recs = json.loads((b / "records.json").read_text(encoding="utf-8"))
        r = next(x for x in receipts if x["claim_id"] == "c002")
        old = r["receipt_sha256"]
        for v in r["q1_mathematics"]["variants"]:
            v["predicted_outcome"]["verdict"] = "consistent"
            v["status"] = "PROVED"
        r["q1_mathematics"]["status"] = r["result"] = "PROVED"
        r["receipt_sha256"] = sha256_hex(canonical({k: v for k, v in r.items() if k != "receipt_sha256"}))
        rec = next(x for x in recs if x["v1_receipt_sha256"] == old)
        rec.update(v1_receipt_sha256=r["receipt_sha256"], v1_result="PROVED")
        rec["mathematical"]["status"] = "MATCH_PROVED"
        rec["outward"]["verdict"] = "CONFIRMATION"
        (b / "v1" / "receipts.json").write_text(json.dumps(receipts, indent=1, ensure_ascii=False, sort_keys=True), encoding="utf-8")
        _reseal_v1(b)
        _reseal(b, recs)

    def drop_corroboration(b):
        recs = json.loads((b / "records.json").read_text(encoding="utf-8"))
        r = next(x for x in recs if x["claim_id"] == "c002")
        r["source_reading"]["corroborated_by"] = []
        _reseal(b, recs)

    def foreign_records(b):
        shutil.copy(other / "records.json", b / "records.json")
        _reseal(b)

    for name, edit in (("verdict_upgraded", upgrade), ("findings_edited", edit_findings), ("data_substituted", substitute_data),
                       ("checker_edited", edit_checker), ("kernel_outcome_forged", forge_outcome),
                       ("corroboration_removed", drop_corroboration), ("records_from_another_bundle", foreign_records)):
        case(name, edit)
    return out


FAKE = """#!/bin/sh
if [ "$1" = "--version" ]; then echo "{version}"; exit 0; fi
{body}
"""


def fail_closed(work: Path, real_version: str) -> dict:
    out = {}
    cases = {"killed_for_lack_of_memory": ("kill -9 $$", {}), "hangs_until_timeout": ("sleep 30", {"lean_timeout": 3}),
             "exits_zero_without_output": ("exit 0", {}), "prints_a_warning": ('echo "warning: something"; exit 0', {})}
    saved = os.environ.get("PCS_CLAIMCHECK_LEAN")
    try:
        for name, (body, kw) in cases.items():
            exe = work / f"fake-{name}"
            exe.write_text(FAKE.format(version=real_version, body=body), encoding="utf-8")
            exe.chmod(exe.stat().st_mode | stat.S_IEXEC)
            os.environ["PCS_CLAIMCHECK_LEAN"] = str(exe)
            result = verify(PROPOSALS[:1], source_text=TEXT, source_meta={"name": "live"}, data=DATA, manifest=MANIFEST, find_siblings=False, **kw)
            rec = result["records"][0]
            out[name] = {"verdict": rec["outward"]["verdict"], "mathematical": rec["mathematical"]["status"],
                         "kernel_run_recorded": rec["mathematical"]["kernel_run"] is not None}
        os.environ["PCS_CLAIMCHECK_LEAN"] = str(work / "no-such-lean")
        rec = verify(PROPOSALS[:1], source_text=TEXT, source_meta={"name": "live"}, data=DATA, manifest=MANIFEST, find_siblings=False)["records"][0]
        out["lean_missing"] = {"verdict": rec["outward"]["verdict"], "mathematical": rec["mathematical"]["status"],
                               "kernel_run_recorded": rec["mathematical"]["kernel_run"] is not None}
    finally:
        if saved is None:
            os.environ.pop("PCS_CLAIMCHECK_LEAN", None)
        else:
            os.environ["PCS_CLAIMCHECK_LEAN"] = saved
    return out


def runner_cases(good: Path, work: Path) -> dict:
    from .runner_negative_controls import MARKER, shadowed_run_tail
    proof = sorted((good / "v1" / "obligations").glob("*.lean"))[0]
    run = lambda p, *extra: json.loads(subprocess.run([sys.executable, str(HERE / "claimcheck_kernel_runner.py"), str(p), *extra],
                                                      capture_output=True, text=True).stdout)
    real = run(proof)
    forged = work / "forged.lean"
    text = proof.read_text(encoding="utf-8")
    swap = (".checked .consistent", ".checked .inconsistent") if ".checked .consistent" in text.split("generated obligations")[1] else (".checked .inconsistent", ".checked .consistent")
    head, tail = text.split("-- ===== generated obligations", 1)
    forged.write_text(head + "-- ===== generated obligations" + tail.replace(*swap), encoding="utf-8")
    # the forgery of research/claimcheck_assurance_v1/findings/RUNNER_TAIL_FORGERY.md, with the real kernel available
    shadow = work / "shadowed-run.lean"
    shadow.write_text(text.split(MARKER)[0] + MARKER + shadowed_run_tail(DATA), encoding="utf-8")
    shadow_report = run(shadow)
    # and with a stand-in lean that records being started: it must not be started
    marker, standin = work / "lean-was-started", work / "standin-lean"
    standin.write_text(f"#!{sys.executable}\nimport pathlib\npathlib.Path({str(marker)!r}).write_text('x')\nprint('Lean (version 4.28.0, stand-in)')\n")
    standin.chmod(0o755)
    run(shadow, "--lean", str(standin))
    # a scale the page never writes can force either verdict: the kernel accepts the true one, and the receipt flags it
    from .claimcheck_kernel_runner import parse_tail_claims
    head_, tail_ = text.split(MARKER)
    _, _, outcomes = parse_tail_claims(tail_)
    i = next(k for k, o in enumerate(outcomes) if o.startswith(".checked"))
    cut = [k for k in range(len(tail_)) if tail_.startswith("scale := ", k)][i]
    end = tail_.index(",\n", cut)
    scaled = tail_[:cut] + "scale := ((4571 : Rat) / 4247)" + tail_[end:]
    flip = outcomes[i].replace(".consistent", ".inconsistent") if ".consistent" in outcomes[i] else outcomes[i].replace(".inconsistent", ".consistent")
    forced = []
    for outcome in (outcomes[i], flip):
        batch = scaled.index("theorem pcs_batch")
        b = scaled.index(outcomes[i], batch)
        t = scaled[:b] + outcome + scaled[b + len(outcomes[i]):]
        line = f"theorem pcs_claim_{i} : run pcs_src pcs_c{i} = "
        c = t.index(line) + len(line)
        t = t[:c] + outcome + t[c + len(outcomes[i]):]
        path = work / f"forced-scale-{len(forced)}.lean"
        path.write_text(head_ + MARKER + t, encoding="utf-8")
        forced.append(run(path))
    accepted = [r for r in forced if r["accepted"]]
    return {"real_proof_file_accepted": real["accepted"], "theorems": len(real["theorems"]),
            "real_receipt_lists_settings_without_flags": real.get("all_settings_as_the_page_writes") is True
                                                         and all("statement" in t for t in real.get("theorems", [])),
            "forced_scale_exactly_one_verdict_accepted": len(accepted) == 1,
            "forced_scale_receipt_flags_the_scale": bool(accepted) and accepted[0]["all_settings_as_the_page_writes"] is False
                                                    and any("scale" in n for n in accepted[0]["theorems"][i]["settings_the_page_never_writes"]),
            "memory_cap_too_small_refused": run(proof, "--max-memory-mb", "256")["accepted"] is False,
            "lean_executable_recorded": bool(real.get("lean_executable")) and len(real.get("lean_executable_sha256", "")) == 64,
            "real_receipt_schema": real.get("schema"), "data_sha256_matches": real.get("data_sha256") == sha256_hex(DATA),
            "forged_outcome_accepted": run(forged)["accepted"],
            "shadowed_run_accepted": shadow_report["accepted"], "shadowed_run_why_not": shadow_report.get("why_not"),
            "lean_started_for_shadowed_run": marker.exists()}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out")
    args = ap.parse_args(argv)
    version = lean_version(find_lean())            # raises if Lean 4.28.0 is not available: this check never skips
    report: dict = {"lean": version, "checker_sha256": checker_sha256()}
    with tempfile.TemporaryDirectory(prefix="claimcheck-v11-live-") as tmp:
        work = Path(tmp)
        result = make_bundle(work / "good")
        got = {r["claim_id"]: (r["outward"]["verdict"], r["mathematical"]["status"]) for r in result["records"] if not r["auxiliary"]}
        report["end_to_end"] = {"verdicts": {k: list(v) for k, v in got.items()}, "as_expected": got == EXPECTED,
                                "supporting_readings_found_and_kernel_checked": sum(1 for r in result["records"] if r["auxiliary"]),
                                "every_decided_record_has_a_fresh_kernel_run": all(r["mathematical"]["kernel_run"] for r in result["records"]
                                                                                   if r["mathematical"]["status"] != "NOT_ESTABLISHED")}
        ok, summary = replay(work / "good")
        report["independent_replay"] = {"all_replayed": ok, "proofs_rechecked": summary["proofs_rechecked_by_the_lean_kernel"],
                                        "obligation_files_rechecked": summary["v1_replay"]["obligation_files_rechecked"]}
        other = verify(PROPOSALS[2:], source_text=TEXT, source_meta={"name": "other"}, data=DATA.replace(b"12.31", b"12.51"),
                       manifest={k: v for k, v in MANIFEST.items() if k != "sha256"}, keep_dir=work / "other" / "v1" / "obligations")
        write_bundle_v11(work / "other", other, source_text=TEXT, data=DATA.replace(b"12.31", b"12.51"),
                         manifest={k: v for k, v in MANIFEST.items() if k != "sha256"}, source_name="o.txt", data_name="o.csv")
        report["tampering"] = tamper_cases(work / "good", work / "other", work)
        report["fail_closed"] = fail_closed(work, version)
        report["kernel_runner"] = runner_cases(work / "good", work)
    passed = (report["end_to_end"]["as_expected"] and report["end_to_end"]["every_decided_record_has_a_fresh_kernel_run"]
              and report["independent_replay"]["all_replayed"] and report["independent_replay"]["proofs_rechecked"]
              and all(c["replay_rejected"] for c in report["tampering"].values())
              and all(c["verdict"] == "UNKNOWN" and c["mathematical"] == "NOT_ESTABLISHED" and not c["kernel_run_recorded"] for c in report["fail_closed"].values())
              and report["kernel_runner"]["real_proof_file_accepted"] and report["kernel_runner"]["data_sha256_matches"]
              and not report["kernel_runner"]["forged_outcome_accepted"]
              and not report["kernel_runner"]["shadowed_run_accepted"]
              and not report["kernel_runner"]["lean_started_for_shadowed_run"]
              and report["kernel_runner"]["real_receipt_schema"] == "pcs-claimcheck-kernel-run-v2"
              and report["kernel_runner"]["real_receipt_lists_settings_without_flags"]
              and report["kernel_runner"]["forced_scale_exactly_one_verdict_accepted"]
              and report["kernel_runner"]["forced_scale_receipt_flags_the_scale"]
              and report["kernel_runner"]["memory_cap_too_small_refused"]
              and report["kernel_runner"]["lean_executable_recorded"])
    report["passed"] = passed
    text = json.dumps(report, indent=1, ensure_ascii=False)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
