"""Checked discovery library with equality retrieval for larger term contexts."""
from .library import LibraryEnvironment, reuse_priority
from .environment import act, candidates
from .discovery import spine


class AbstractionEnvironment(LibraryEnvironment):
    def candidates(self, state):
        result = super().candidates(state)
        if not state.get("goals"): return result
        for action in candidates(state, induction=True):
            if action not in result: result.append(action)
        local_names = {l["name"] for g in state["goals"] for l in g["locals"]}
        for entry in self.catalog:
            e = entry["kernel"]["expression"]
            while e["kind"] == "forall": e = e["children"][1]
            head, _ = spine(e)
            if head["kind"] == "constant" and head["value"].startswith("Eq:") and entry["name"] not in local_names:
                result.extend([act("rewrite", entry["name"]), act("rewrite_back", entry["name"])])
        return result


def abstraction_priority(state, options):
    scores = reuse_priority(state, options)
    # Structural matching is retrieval only; failed instantiations cost Lean.
    target = state["goals"][0]["expression"]
    catalog = {e["name"]: e["expression"] for e in state.get("available_lemmas", [])}
    def matches(pattern, expression):
        if pattern["kind"] == "bound": return True
        return (pattern["kind"] == expression["kind"] and pattern["value"] == expression["value"]
                and len(pattern["children"]) == len(expression["children"])
                and all(matches(p, e) for p, e in zip(pattern["children"], expression["children"])))
    def contains(expression, pattern):
        return matches(pattern, expression) or any(contains(c, pattern) for c in expression["children"])
    for i, a in enumerate(options):
        # Rewriting an expression under an unopened binder is not a substitute
        # for introducing that binder. Reserve the strongest priority for the
        # available introduction so retrieved rewrites cannot starve the beam.
        if target["kind"]=="forall" and a["kind"]=="intro":scores[i]=16
        if a["kind"] == "rewrite": scores[i] = 10
        if a["kind"] not in {"rewrite", "rewrite_back"} or a["argument"] not in catalog: continue
        e = catalog[a["argument"]]
        while e["kind"] == "forall": e = e["children"][1]
        head, args = spine(e)
        if head["kind"] == "constant" and head["value"].startswith("Eq:") and len(args) == 3:
            scores[i] = 11.5 if target["kind"]!="forall" and contains(target, args[1 if a["kind"] == "rewrite" else 2]) else -4
    return scores
