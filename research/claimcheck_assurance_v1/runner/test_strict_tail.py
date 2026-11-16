"""The runner forgery, reproduced on the withdrawn runner and refused by the corrected one.

* The strict grammar of the installed runner (`research/claimcheck_v1_1/claimcheck_kernel_runner.py`,
  `parse_tail`) accepts every proof file the generator wrote and rejects hand-crafted tails and
  most single-character edits.  No Lean needed.
* With PCS_LEAN set to a Lean 4.28.0 binary: the withdrawn runner, kept byte for byte as evidence in
  `../findings/evidence/claimcheck_kernel_runner_v1.withdrawn` (SHA-256 8d9e07b4...), still accepts the
  forged file and reports MATCHES (the finding reproduces); plain Lean accepts the forged file; the
  installed runner refuses it before Lean is started and accepts a genuine file.

The withdrawn runner is run only from a temporary copy, only on the forged file, to show the defect.
It is not a verification path.

Run: PCS_LEAN=/path/to/lean python3 research/claimcheck_assurance_v1/runner/test_strict_tail.py [--out FILE]
"""
import argparse, hashlib, json, os, shutil, subprocess, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
from research.claimcheck_v1_1.claimcheck_kernel_runner import NotCanonical, parse_tail  # noqa: E402

INSTALLED = ROOT / "research/claimcheck_v1_1/claimcheck_kernel_runner.py"
WITHDRAWN = HERE.parent / "findings/evidence/claimcheck_kernel_runner_v1.withdrawn"
WITHDRAWN_SHA256 = "8d9e07b4ac4b0abed13c9e750cbca113f1db26d82f3709579a7aafa7401f713f"
MARKER = "\n-- ===== generated obligations (data numeral, claims, expected outcomes) =====\n"
CHECKER = (ROOT / "research/claimcheck_v1/formal/ClaimCheck.lean").read_text(encoding="utf-8")
GOOD = ("open PCS.ClaimCheck\n\n"
        "def pcs_src : Source := ⟨0x612c620a312c320a, 8⟩\n\n"
        "def pcs_c0 : Claim :=\n  { column := some (b \"a\"),\n    filter := [],\n    stat := .mean,\n    naTokens := [b \"\", b \"NA\"],\n"
        "    scale := ((1 : Rat) / 1),\n    reported := b \"1\" }\n\n"
        "theorem pcs_batch : runAll pcs_src [pcs_c0] =\n    [.checked .consistent (.rat ((1 : Rat) / 1)) 1 0] := by decide +kernel\n\n"
        "theorem pcs_claim_0 : run pcs_src pcs_c0 = .checked .consistent (.rat ((1 : Rat) / 1)) 1 0 :=\n"
        "  run_of_runAll pcs_batch 0 rfl rfl\n#print axioms pcs_claim_0\n\n")
SHADOW = (HERE.parent / "findings/evidence/forged_tail.lean.txt").read_text(encoding="utf-8")


def rejected(tail):
    try:
        parse_tail(tail)
    except NotCanonical as exc:
        return str(exc)
    return None


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out")
    args = ap.parse_args(argv)
    report = {"installed_runner_sha256": hashlib.sha256(INSTALLED.read_bytes()).hexdigest(),
              "accepted_real_files": 0, "rejected_forgeries": {}, "single_character_edits": 0, "edits_rejected": 0}
    assert hashlib.sha256(WITHDRAWN.read_bytes()).hexdigest() == WITHDRAWN_SHA256, "the preserved evidence changed"
    files = sorted((ROOT / "research/claimcheck_v1/benchmark/results/bundles").glob("*/obligations/*.lean"))
    files += sorted((ROOT / "research/claimcheck_v1_1").glob("**/obligations/*.lean"))
    assert len(files) >= 80
    for f in files:
        head, tail = f.read_text(encoding="utf-8").split(MARKER)
        assert head == CHECKER
        data, outcomes = parse_tail(tail)
        assert len(outcomes) == tail.count("#print axioms") >= 1
        report["accepted_real_files"] += 1
    assert parse_tail(GOOD) == (b"a,b\n1,2\n", [".checked .consistent (.rat ((1 : Rat) / 1)) 1 0"])

    forgeries = {
        "shadowed_run_on_a_decoy_type": SHADOW,
        "namespace_wrapper": GOOD.replace("open PCS.ClaimCheck\n\n", "open PCS.ClaimCheck\n\nnamespace X\n", 1),
        "extra_definition_before_the_claims": GOOD.replace("def pcs_c0", "def helper : Nat := 0\n\ndef pcs_c0", 1),
        "macro_after_the_data": GOOD.replace("def pcs_c0", "macro \"run\" : term => `(fun _ _ => default)\n\ndef pcs_c0", 1),
        "theorem_proved_by_another_term": GOOD.replace("run_of_runAll pcs_batch 0 rfl rfl", "by decide"),
        "per_claim_outcome_differs_from_batch": GOOD.replace("= .checked .consistent (.rat ((1 : Rat) / 1)) 1 0 :=", "= .checked .inconsistent (.rat ((1 : Rat) / 1)) 1 0 :="),
        "text_after_the_last_theorem": GOOD + "theorem extra : True := trivial\n",
        "comment_inside": GOOD.replace("filter := [],", "filter := [], -- note"),
        "set_option": GOOD.replace("theorem pcs_batch", "set_option maxRecDepth 100000 in\ntheorem pcs_batch"),
        "noncanonical_numeral_short": GOOD.replace("0x612c620a312c320a, 8", "0x612c620a312c320a, 9"),
        "noncanonical_numeral_uppercase": GOOD.replace("0x612c620a312c320a", "0x612C620A312C320A"),
        "string_with_a_quote": GOOD.replace('b "a"', 'b "a\\""'),
        "claim_field_is_an_expression": GOOD.replace("scale := ((1 : Rat) / 1)", "scale := ((1 : Rat) / (1 + 0))"),
        "second_source_definition": GOOD.replace("def pcs_c0", "def pcs_src2 : Source := ⟨0x00, 1⟩\n\ndef pcs_c0", 1),
        "claims_not_numbered_from_zero": GOOD.replace("pcs_c0", "pcs_c1").replace("pcs_claim_0", "pcs_claim_1"),
        "empty": "",
    }
    for name, tail in forgeries.items():
        why = rejected(tail)
        assert why, name
        report["rejected_forgeries"][name] = why

    # every single-character deletion, substitution or insertion of a canonical tail is either
    # rejected or still canonical (a different literal: other data, another number)
    for i in range(len(GOOD)):
        for edit in (GOOD[:i] + GOOD[i + 1:], GOOD[:i] + "x" + GOOD[i + 1:], GOOD[:i] + " " + GOOD[i:]):
            report["single_character_edits"] += 1
            if rejected(edit):
                report["edits_rejected"] += 1
    assert report["edits_rejected"] > 0.9 * report["single_character_edits"]

    lean = os.environ.get("PCS_LEAN")
    if lean:
        with tempfile.TemporaryDirectory() as tmp:
            forged = Path(tmp) / "forged.lean"
            forged.write_text(CHECKER + MARKER + SHADOW, encoding="utf-8")
            plain = subprocess.run([lean, str(forged)], capture_output=True, text=True, cwd=tmp)
            withdrawn_copy = Path(tmp) / "withdrawn_runner_v1.py"
            shutil.copy(WITHDRAWN, withdrawn_copy)

            def runner(path, proof):
                out = Path(tmp) / (Path(path).stem + "-" + Path(proof).stem + ".json")
                proc = subprocess.run([sys.executable, str(path), str(proof), "--lean", lean, "--out", str(out)], capture_output=True, text=True)
                return proc.returncode, json.loads(out.read_text())
            code1, rep1 = runner(withdrawn_copy, forged)
            code2, rep2 = runner(INSTALLED, forged)
            good = Path(tmp) / "good.lean"
            good.write_text(CHECKER + MARKER + GOOD, encoding="utf-8")
            code3, rep3 = runner(INSTALLED, good)
            report["with_lean"] = {
                "lean": subprocess.run([lean, "--version"], capture_output=True, text=True).stdout.strip(),
                "plain_lean_accepts_the_forged_file": plain.returncode == 0 and "'pcs_claim_0'" in plain.stdout,
                "withdrawn_runner_accepts_the_forged_file": rep1["accepted"],
                "withdrawn_runner_says": [t["in_words"] for t in rep1["theorems"]],
                "installed_runner_accepts_the_forged_file": rep2["accepted"],
                "installed_runner_says": rep2.get("why_not"),
                "installed_runner_asked_lean_for_anything": "lean" in rep2,
                "installed_runner_accepts_a_genuine_file": rep3["accepted"] and rep3.get("generated_part_canonical") is True,
            }
            assert report["with_lean"]["plain_lean_accepts_the_forged_file"], plain.stdout + plain.stderr
            assert rep1["accepted"] is True and code1 == 0, "the finding no longer reproduces on the withdrawn runner: update the report"
            assert rep2["accepted"] is False and code2 == 1 and "not in canonical form" in rep2["why_not"] and "lean" not in rep2
            assert report["with_lean"]["installed_runner_accepts_a_genuine_file"] and code3 == 0, rep3
    text = json.dumps(report, indent=1)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
