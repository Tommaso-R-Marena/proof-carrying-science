"""Integrity regressions: fake audit/negative logs must not pass release gates."""
import pytest

from scripts.verify_omega_dd_formal import check_inventory, check_negative


def test_complete_axiom_inventory_and_empty_dependencies():
    result = check_inventory("'A' depends on axioms: [propext, Quot.sound]\n"
                             "'B' does not depend on any axioms\n", ["A", "B"])
    assert result == {"A": ["Quot.sound", "propext"], "B": []}


@pytest.mark.parametrize("text", [
    "'A' depends on axioms: [propext]\n",
    "'A' depends on axioms: [propext]\n'A' depends on axioms: [propext]\n",
    "'A' depends on axioms: [sorryAx]\n'B' does not depend on any axioms\n",
    "'A' depends on axioms: [Lean.ofReduceBool]\n'B' does not depend on any axioms\n",
    "'A' depends on axioms: []\n'C' depends on axioms: []\n",
])
def test_incomplete_duplicate_or_untrusted_inventory_rejected(text):
    with pytest.raises(ValueError):
        check_inventory(text, ["A", "B"])


def test_only_expected_semantic_rejection_is_accepted():
    text = "Negative.lean:4:0: error: Tactic `decide` proved that the proposition\n  some 1 = some 0\nis false\n"
    check_negative(1, text, ["some 1 = some 0"])
    for code, log in [(0, text), (1, "error: unknown module prefix 'PCSDecisionDiagram'"),
                      (1, text + "error: unexpected token"), (1, text.replace("some 0", "some 2"))]:
        with pytest.raises(ValueError):
            check_negative(code, log, ["some 1 = some 0"])


from scripts.verify_omega_dd_formal import check_control_overlay
ORIGINAL='''def smallLim : Limits := ⟨40, 100000⟩
example : (check tDense smallLim).decision = .resourceLimit := by decide

theorem count_control : count = 4096 := by decide
example : flag = false := by decide
example : flag = false := by decide
'''
def test_proof_changes_preserve_original_obligations():
    changed=ORIGINAL.replace('by decide','by exact independentlyCheckedEvidence')
    assert check_control_overlay(ORIGINAL,changed)['original_assertions_preserved']==4
@pytest.mark.parametrize('old,new',[
 ('count = 4096','count = 4095'),
 ('.resourceLimit','.counterexample'),
 ('⟨40, 100000⟩','⟨41, 100000⟩'),
 ('flag = false','flag = true'),
])
def test_weakened_or_modified_control_is_rejected(old,new):
    with pytest.raises(ValueError):check_control_overlay(ORIGINAL,ORIGINAL.replace(old,new))
def test_duplicate_anonymous_obligations_cannot_be_dropped():
    changed=ORIGINAL.replace('example : flag = false := by decide\n','',1)
    with pytest.raises(ValueError):check_control_overlay(ORIGINAL,changed)
