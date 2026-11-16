"""Proof files the stand-alone kernel runner must refuse before starting Lean (negative controls).

The first is the forgery reported in research/claimcheck_assurance_v1/findings/RUNNER_TAIL_FORGERY.md:
a hand-written generated part that defines its own `run` on its own type and proves the expected
equation by `rfl`.  The Lean kernel accepts such a file, and the previous runner (receipt schema v1)
reported "MATCHES" for it, although the theorem says nothing about the reviewed checker.  The other
controls alter a genuine generated part in ways the generator never does.  Used by
tests/test_runner_strict.py (no Lean needed) and check_live_v11.py (real kernel).
"""
from __future__ import annotations

MARKER = "\n-- ===== generated obligations (data numeral, claims, expected outcomes) =====\n"


def shadowed_run_tail(data: bytes) -> str:
    """The forged generated part: its own `Decoy` type and its own `run`, proved by `rfl`."""
    return ("open PCS.ClaimCheck\n\n"
            f"def pcs_src : Source := ⟨0x{data.hex() or '0'}, {len(data)}⟩\n\n"
            "structure Decoy where\n  n : Nat\n\n"
            "def pcs_c0 : Decoy := ⟨0⟩\n\n"
            "def run (_ : Source) (_ : Decoy) : Outcome := .checked .consistent (.rat ((999 : Rat) / 1)) 2 0\n\n"
            "theorem pcs_claim_0 : run pcs_src pcs_c0 = .checked .consistent (.rat ((999 : Rat) / 1)) 2 0 :=\n  rfl\n"
            "#print axioms pcs_claim_0\n\n")


def _once(text: str, old: str, new: str) -> str:
    i = text.index(old)
    return text[:i] + new + text[i + len(old):]


def altered_tails(genuine: str, data: bytes) -> dict[str, str]:
    """Named variants of a genuine generated part, each of which the runner must refuse."""
    first_theorem = genuine.index("theorem pcs_claim_0 : run pcs_src pcs_c0 = ")
    statement_end = genuine.index(" :=\n", first_theorem)
    statement = genuine[first_theorem:statement_end]
    other = (statement.replace(".checked .consistent", ".checked .inconsistent") if ".checked .consistent" in statement
             else statement.replace(".checked .inconsistent", ".checked .consistent") if ".checked .inconsistent" in statement
             else statement.replace(".undefined .", ".undefined .x", 1))
    numeral_start = genuine.index("⟨0x") + 3
    numeral_end = genuine.index(",", numeral_start)
    length_end = genuine.index("⟩", numeral_end)
    length = int(genuine[numeral_end + 2:length_end])
    return {
        "shadowed_run_on_a_decoy_type": shadowed_run_tail(data),
        "namespace_wrapper": _once(genuine, "open PCS.ClaimCheck\n\n", "open PCS.ClaimCheck\n\nnamespace X\n"),
        "extra_definition_before_the_claims": _once(genuine, "def pcs_c0", "def helper : Nat := 0\n\ndef pcs_c0"),
        "macro_before_the_claims": _once(genuine, "def pcs_c0", "macro \"run\" : term => `(fun _ _ => default)\n\ndef pcs_c0"),
        "import_after_the_marker": _once(genuine, "open PCS.ClaimCheck\n\n", "import Lean\nopen PCS.ClaimCheck\n\n"),
        "claim_theorem_proved_by_another_term": _once(genuine, "run_of_runAll pcs_batch 0 rfl rfl", "by decide"),
        "claim_theorem_states_another_outcome": genuine[:first_theorem] + other + genuine[statement_end:],
        "text_after_the_last_theorem": genuine + "theorem extra : True := trivial\n",
        "comment_inside_a_claim": _once(genuine, "\n    stat := ", " -- note\n    stat := "),
        "set_option_before_the_batch_theorem": _once(genuine, "theorem pcs_batch", "set_option maxRecDepth 100000 in\ntheorem pcs_batch"),
        "second_source_definition": _once(genuine, "def pcs_c0", "def pcs_src2 : Source := ⟨0x00, 1⟩\n\ndef pcs_c0"),
        "uppercase_hexadecimal_numeral": genuine[:numeral_start] + genuine[numeral_start:numeral_end].upper().replace("0X", "0x")
                                         + genuine[numeral_end:] if any(c in "abcdef" for c in genuine[numeral_start:numeral_end])
                                         else _once(genuine, "⟨0x", "⟨0X"),
        "numeral_length_one_more": genuine[:numeral_end + 2] + str(length + 1) + genuine[length_end:],
        "empty_generated_part": "",
    }
