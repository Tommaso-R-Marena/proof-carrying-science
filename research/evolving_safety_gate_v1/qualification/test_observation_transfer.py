from itertools import product

from .observation_transfer import cases, episode, error_by_coverage, study, would_misroute


def exhaustive(rows):
    observations = sorted({key for key, _ in rows})
    best = {}
    for decisions in product((None, False, True), repeat=len(observations)):
        policy = dict(zip(observations, decisions, strict=True))
        answers = [(policy[k], y) for k, y in rows if policy[k] is not None]
        n = len(answers)
        misses = sum(actual != expected for actual, expected in answers)
        best[n] = min(misses, best.get(n, misses))
    return best


def test_frontier_agrees_with_all_selective_rules():
    keys = (0, 1, 1, 2, 2, 2)
    for labels in product((False, True), repeat=len(keys)):
        rows = list(zip(keys, labels, strict=True))
        assert error_by_coverage(reversed(rows)) == exhaustive(rows)


def test_labels_are_unavailable_to_catalog_detectors():
    for move in cases():
        assert set(episode(move)) == {"guarded_complete", "tools", "proposals"}
    assert sum(map(would_misroute, cases())) == 8


def test_information_bound_is_sharp():
    result = study()
    assert result["wrong_executed"] == 0
    frontier = result["minimum_errors_by_exact_coverage"]
    assert frontier["executed_move"][16] == 8
    assert frontier["with_proposal"][16] == 0
    assert result["confusion"]["mandated_route_comparison"]["FN"] == 0
