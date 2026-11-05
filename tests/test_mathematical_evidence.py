import copy
import json

import pytest

from pcs.experimental.prover.induction_ir import digest, theorem
from pcs.experimental.prover.induction_language import formalize
from pcs.experimental.prover.mathematical_evidence import audit, _checked, validate_transfer_protocol


def fixture(tmp_path):
    goal = formalize("For all natural numbers n, (n + 0) equals n.")["candidates"][0]["ir"]
    task = {"id": "new", "kind": "typed", "split": "final", "goal": goal}
    for name, value in (("tasks.json", [task]), ("protocol.json", {"tasks_sha256": digest([task])}),
                        ("checkpoint-transfer-protocol.json", {"tasks_sha256": digest([task]), "models": []})):
        (tmp_path / name).write_text(json.dumps(value))
    (tmp_path / "results").mkdir()
    (tmp_path / "checkpoint-transfer").mkdir()
    return task


def test_missing_comparisons_cannot_be_reported_complete(tmp_path):
    fixture(tmp_path)
    result = audit(tmp_path)
    assert result["complete"] is False
    assert result["recorded_comparisons"] == 0
    assert result["expected_comparisons"] == 5
    assert len(result["missing"]) == 5


def test_unknown_remains_unknown_and_extra_policy_is_rejected(tmp_path):
    task = fixture(tmp_path)
    row = {"task": task, "mode": "symbolic", "result": {"status": "unknown", "receipt": None}}
    path = tmp_path / "results/new-symbolic.json"
    path.write_text(json.dumps(row))
    assert audit(tmp_path)["counts"]["typed:final:symbolic"]["unknown"] == 1
    (tmp_path / "results/unfrozen-new-policy.json").write_text(json.dumps(row))
    with pytest.raises(ValueError, match="membership"):
        audit(tmp_path)


def test_result_task_and_goal_kernel_bindings_are_checked(tmp_path):
    task = fixture(tmp_path)
    kernel = {"axioms": [], "expression": {}}
    receipt = {"goal_sha256": digest(task["goal"]), "statement": theorem(task["goal"]), "kernel": kernel}
    row = {"task": task, "result": {"status": "verified", "receipt": receipt,
                                    "independent_replay": {"kernel": kernel}}}
    _checked(row, task)
    for mutate in (lambda r: r["result"]["receipt"].update(goal_sha256="f" * 64),
                   lambda r: r["result"]["independent_replay"]["kernel"].update(axioms=["sorryAx"]),
                   lambda r: r["result"].update(independent_replay=None),
                   lambda r: r["task"].update(id="changed")):
        forged = copy.deepcopy(row)
        mutate(forged)
        with pytest.raises(ValueError):
            _checked(forged, task)


def test_frozen_task_digest_is_not_only_a_display_label(tmp_path):
    fixture(tmp_path)
    rows = json.loads((tmp_path / "tasks.json").read_text())
    rows[0]["id"] = "tampered"
    (tmp_path / "tasks.json").write_text(json.dumps(rows))
    with pytest.raises(ValueError, match="frozen corpus"):
        audit(tmp_path)


def test_transfer_cannot_silently_change_library_or_compute(tmp_path):
    task = fixture(tmp_path)
    library = {"format": "pcs-checked-lemma-library-v1", "entries": []}
    protocol = {"format": "pcs-checkpoint-transfer-v2", "frozen_before_variant_evaluation": True,
                "tasks_sha256": digest([task]), "library_sha256": digest(library),
                "budget": 48, "depth": 18, "beam": 4, "models": [{"id": "frozen"}]}
    experiment = {"typed_action_budget": 48, "depth": 18, "beam": 4}
    assert validate_transfer_protocol(protocol, [task], library, experiment) == [task]
    for changed in ({**protocol, "budget": 96}, {**protocol, "library_sha256": "f" * 64},
                    {**protocol, "models": [{"id": "frozen"}, {"id": "frozen"}]}):
        with pytest.raises(ValueError):
            validate_transfer_protocol(changed, [task], library, experiment)
