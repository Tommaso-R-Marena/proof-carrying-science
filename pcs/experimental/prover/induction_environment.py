"""Explicit extended action domain; published ordinary action spaces are preserved."""
from .environment import LeanEnvironment, candidates, _symbolic_priority


def induction_priority(state, options):
    return [10 if a["kind"] == "rewrite" else _symbolic_priority(state,a) for a in options]


class InductionEnvironment(LeanEnvironment):
    default_rank = staticmethod(induction_priority)

    def candidates(self, state):
        return candidates(state, induction=True)
