import json
import subprocess
import sys

import pytest

from pcs.countermodel_v1 import VERSION, check_countermodel_session_file, replay_countermodel_session


def session(*actions, mission="implication-flip"):
    return {"version": VERSION, "mission_id": mission, "actions": list(actions)}


P = {"type": "toggle", "p": "P", "i": 0}
CHECK = {"type": "check"}


def test_independent_semantics_rewards_and_exposure():
    out = replay_countermodel_session(session(CHECK, P, CHECK, CHECK))
    assert [s["reward"] for s in out["steps"]] == [-1, 0, 10, -2]
    assert out["steps"][0]["checker_feedback_before_action"] is False
    assert out["steps"][1]["checker_feedback_before_action"] is True
    assert out["steps"][1]["state_before"]["P"] == [False]
    assert out["steps"][1]["world"]["P"] == [True]
    assert out["final_verdict"] == {"left": False, "right": True, "counterexample": True}
    assert out["final_verified"] and out["score"] == 116
    assert not out["lean_kernel_checked"] and not out["pcs_authoritative"]


def test_solved_then_edited_never_keeps_a_stale_success():
    out = replay_countermodel_session(session(P, CHECK, P))
    assert out["solved"] and not out["final_verified"] and out["score"] == 0
    assert out["final_world"]["P"] == [False]
    assert out["steps"][0]["world"]["P"] == [True], "later moves must not mutate snapshots"


def test_hint_and_tutorial_assistance_are_recomputed():
    out = replay_countermodel_session(session({"type": "hint"}, P, CHECK))
    assert out["hints"] == 1 and out["score"] == 118
    assert not out["steps"][0]["assisted_before_action"]
    assert out["steps"][1]["assisted_before_action"]
    after = replay_countermodel_session(session(P, CHECK, {"type": "hint"}))
    assert after["solved"] and not after["final_verified"]


def test_real_two_agent_quantifier_counterexample():
    out = replay_countermodel_session(session({"type": "add"}, P, CHECK, mission="quantifier-switch"))
    assert out["final_verdict"] == {"left": False, "right": True, "counterexample": True}
    assert out["minimum_domain_size"] == 2 and out["final_verified"]


def test_relation_resize_preserves_existing_edges():
    out = replay_countermodel_session(session({"type": "add"}, {"type": "toggle_relation", "i": 0, "j": 1},
                                               {"type": "add"}, {"type": "remove"}, CHECK,
                                               mission="quantifier-scope"))
    assert out["final_world"]["R"] == [[False, True], [False, False]]
    assert out["edits"] == 4


@pytest.mark.parametrize("actions", [
    [{"type": "remove"}, CHECK],
    [{"type": "add"}] * 3 + [CHECK],
    [{"type": "hint"}] * 4 + [CHECK],
    [{"type": "toggle", "p": "P", "i": True}, CHECK],
    [{"type": "toggle", "p": "P", "i": -1}, CHECK],
    [{"type": "toggle", "p": "P", "i": 1}, CHECK],
    [{"type": "toggle_relation", "i": 0, "j": 0}, CHECK],
    [{"type": "check", "counterexample": True}],
    [{"type": "run", "code": "return true"}, CHECK],
    [P], [], [CHECK] * 121,
])
def test_invalid_or_forged_choices_fail_closed(actions):
    with pytest.raises(ValueError):
        replay_countermodel_session(session(*actions))


def test_personal_fields_and_claimed_labels_are_forbidden():
    for field, value in [("score", 999), ("email", "fixture@example.invalid"), ("assisted", False)]:
        with pytest.raises(ValueError):
            replay_countermodel_session({**session(P, CHECK), field: value})


def test_file_budget_duplicates_and_downloaded_notebook(tmp_path):
    file = tmp_path / "trace.json"
    file.write_text('{"version":"x","version":"y"}')
    with pytest.raises(ValueError, match="Duplicate"):
        check_countermodel_session_file(file)
    file.write_text('[' * 2000 + '0' + ']' * 2000)
    with pytest.raises(ValueError):
        check_countermodel_session_file(file)
    file.write_text('{"actions":NaN}')
    with pytest.raises(ValueError, match="Non-finite"):
        check_countermodel_session_file(file)
    file.write_text(" " * 32769)
    with pytest.raises(ValueError, match="32 KiB"):
        check_countermodel_session_file(file)
    file.write_text(json.dumps({"format": "pcs-countermodel-local-trace-v1",
                               "scope": "unverified player-recorded action trace; replay on PCS Worker required",
                               **session(P, CHECK)}))
    assert check_countermodel_session_file(file)["final_verified"]


def test_actual_cli_distinguishes_checked_unsuccessful_and_invalid(tmp_path):
    file = tmp_path / "trace.json"
    for value, expected in [(session(P, CHECK), 0), (session(CHECK), 1), ({**session(P, CHECK), "score": 999}, 2)]:
        file.write_text(json.dumps(value))
        run = subprocess.run([sys.executable, "-m", "pcs.cli", "countermodel-replay-v1", str(file)],
                             capture_output=True, text=True, check=False)
        assert run.returncode == expected, run.stderr
        assert json.loads(run.stdout)["pcs_authoritative"] is False
    # Exercise the real CLI's default parser recursion limit, independently of
    # pytest's process-wide recursion settings.
    file.write_text('[' * 12000 + '0' + ']' * 12000)
    run = subprocess.run([sys.executable, "-m", "pcs.cli", "countermodel-replay-v1", str(file)],
                         capture_output=True, text=True, check=False)
    assert run.returncode == 2
    assert "nesting" in json.loads(run.stdout)["error"]
