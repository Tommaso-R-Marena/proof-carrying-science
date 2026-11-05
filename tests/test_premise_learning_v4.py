"""Learning firewall and verifier-controlled rewards; mocked unit boundary only."""
import pytest

pytest.importorskip("torch")
from pcs.experimental.prover.premise_learning_v4 import MathlibRLEnvironment, actor_critic, collect_checked_training, transitions

class BoundaryFixture:
    """Unit fixture, never used as research evidence or actual Lean trajectories."""
    def __init__(self, kernel_failure=False):
        self.kernel_failure = kernel_failure
    def start(self, statement): return {"goals": [{"target": statement}]}
    def options(self, state, limit=6): return [{"kind": "assumption", "argument": None}]
    def step(self, statement, actions, action): return {"valid": True, "closed": True, "state": {"goals": []}}
    def verify(self, statement, actions):
        if self.kernel_failure: raise RuntimeError("actual verifier would reject proof")
        return {"kernel": {"axioms": []}, "statement": statement, "actions": actions}


def test_no_success_reward_when_independent_kernel_verifier_fails():
    env = MathlibRLEnvironment(BoundaryFixture(kernel_failure=True)); env.reset("P → P")
    _,reward,done,response=env.step({"kind": "assumption", "argument": None})
    assert reward<0 and done and response['status']=='verification_failed' and response['receipt'] is None
    assert 'verifier' in response['error']


def test_positive_reward_requires_verifier_receipt_and_immutable_goal():
    env = MathlibRLEnvironment(BoundaryFixture()); env.reset("P → P")
    _, reward, done, response = env.step({"kind": "assumption", "argument": None})
    assert reward == 1 and done and response["receipt"]["kernel"]
    env.reset("P → P"); env.goal = "False"
    with pytest.raises(ValueError, match="changed"):
        env.step({"kind": "assumption", "argument": None})


def test_training_intake_and_rl_reject_final_tasks_before_execution():
    with pytest.raises(ValueError, match="firewall"):
        collect_checked_training(BoundaryFixture(), [{"split": "final"}])
    with pytest.raises(ValueError, match="firewall"):
        actor_critic(None, None, [{"split": "final"}])
    with pytest.raises(ValueError, match="checked"):
        transitions([{"split": "final", "independent_receipt": {"kernel": {}}}])


def test_unapproved_action_and_terminal_reuse_fail_closed():
    env = MathlibRLEnvironment(BoundaryFixture()); env.reset("P → P")
    with pytest.raises(ValueError, match="grammar"):
        env.step({"kind": "raw_tactic", "argument": "sorry"})
    env.step({"kind": "assumption", "argument": None})
    with pytest.raises(ValueError, match="terminal"):
        env.step({"kind": "assumption", "argument": None})
