"""The strict grammar accepts every proof file the generator wrote and rejects hand-crafted tails.

No Lean needed.  With PCS_LEAN set to a Lean 4.28.0 binary, also shows the difference between the
v1.1 runner (accepts the forged file and reports MATCHES) and the v2 runner (refuses before running
Lean).  Run: python3 research/claimcheck_assurance_v1/runner/test_strict_tail.py
"""
import json, os, subprocess, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
from strict_tail import NotCanonical, parse_tail  # noqa: E402

MARKER = "\n-- ===== generated obligations (data numeral, claims, expected outcomes) =====\n"
CHECKER = (ROOT / "research/claimcheck_v1/formal/ClaimCheck.lean").read_text(encoding="utf-8")
GOOD = ("open PCS.ClaimCheck\n\n"
        "def pcs_src : Source := ⟨0x612c620a312c320a, 8⟩\n\n"
        "def pcs_c0 : Claim :=\n  { column := some (b \"a\"),\n    filter := [],\n    stat := .mean,\n    naTokens := [b \"\", b \"NA\"],\n"
        "    scale := ((1 : Rat) / 1),\n    reported := b \"1\" }\n\n"
        "theorem pcs_batch : runAll pcs_src [pcs_c0] =\n    [.checked .consistent (.rat ((1 : Rat) / 1)) 1 0] := by decide +kernel\n\n"
        "theorem pcs_claim_0 : run pcs_src pcs_c0 = .checked .consistent (.rat ((1 : Rat) / 1)) 1 0 :=\n"
        "  run_of_runAll pcs_batch 0 rfl rfl\n#print axioms pcs_claim_0\n\n")
SHADOW = ("open PCS.ClaimCheck\n\n"
          "def pcs_src : Source := ⟨0x612c620a312c320a, 8⟩\n\n"
          "structure Decoy where\n  n : Nat\n\n"
          "def pcs_c0 : Decoy := ⟨0⟩\n\n"
          "def run (_ : Source) (_ : Decoy) : Outcome := .checked .consistent (.rat ((999 : Rat) / 1)) 2 0\n\n"
          "theorem pcs_claim_0 : run pcs_src pcs_c0 = .checked .consistent (.rat ((999 : Rat) / 1)) 2 0 :=\n  rfl\n#print axioms pcs_claim_0\n\n")


def rejected(tail):
    try:
        parse_tail(tail)
    except NotCanonical as exc:
        return str(exc)
    return None


def main():
    report = {"accepted_real_files": 0, "rejected_forgeries": {}, "single_character_edits": 0, "edits_rejected": 0}
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

    # every single-character deletion or substitution of a canonical tail is either rejected or
    # still canonical (a different literal: other data, another number)
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
            def runner(path):
                out = Path(tmp) / (Path(path).stem + ".json")
                proc = subprocess.run([sys.executable, str(path), str(forged), "--lean", lean, "--out", str(out)], capture_output=True, text=True)
                return proc.returncode, json.loads(out.read_text())
            code1, rep1 = runner(ROOT / "research/claimcheck_v1_1/claimcheck_kernel_runner.py")
            code2, rep2 = runner(HERE / "claimcheck_kernel_runner_v2.py")
            report["with_lean"] = {
                "v1_1_runner_accepts_the_forged_file": rep1["accepted"],
                "v1_1_runner_says": [t["in_words"] for t in rep1["theorems"]],
                "v2_runner_accepts_the_forged_file": rep2["accepted"],
                "v2_runner_says": rep2.get("why_not"),
            }
            assert rep1["accepted"] is True and code1 == 0, "the finding no longer reproduces: update the report"
            assert rep2["accepted"] is False and code2 != 0
            good = Path(tmp) / "good.lean"
            good.write_text(CHECKER + MARKER + GOOD, encoding="utf-8")
            out = Path(tmp) / "good.json"
            proc = subprocess.run([sys.executable, str(HERE / "claimcheck_kernel_runner_v2.py"), str(good), "--lean", lean, "--out", str(out)], capture_output=True, text=True)
            rep3 = json.loads(out.read_text())
            assert rep3["accepted"] is True and rep3["generated_part_canonical"] is True and proc.returncode == 0, rep3
            report["with_lean"]["v2_runner_accepts_a_genuine_file"] = True
    print(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
