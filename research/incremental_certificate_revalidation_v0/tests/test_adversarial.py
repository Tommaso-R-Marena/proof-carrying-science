from adversarial.attacks import run_all_attacks


def test_all_attacks_resisted():
    results = run_all_attacks()
    failed = [r for r in results if r.attack_succeeded]
    assert not failed, [(r.name, r.detail, r.counterexample) for r in failed]


def test_attack_categories_present():
    names = {r.name for r in run_all_attacks()}
    required = {
        "input_substitution",
        "dependency_manipulation",
        "op_substitution",
        "policy_substitution",
        "version_mismatch",
        "cache_forgery",
        "serialization_duplicate_keys",
        "rollback",
        "proof_context_misuse",
    }
    assert required <= names
