"""Independent bounded search for transitive scope non-amplification.

This enumerates a finite domain; it is not a theorem about all Python or
Lean inputs and does not exercise cryptography or external execution.
"""
from itertools import product
import json

scopes = [(mask, label, size, quota)
          for mask, label, size, quota in
          product(range(4), range(2), range(1, 3), range(1, 3))]

def oracle(child, parent):
    child_actions = {i for i in range(2) if child[0] & (1 << i)}
    parent_actions = {i for i in range(2) if parent[0] & (1 << i)}
    return child_actions.issubset(parent_actions) and all(
        x <= y for x, y in zip(child[1:], parent[1:]))

def compressed(child, root):
    return ((child[0] & ~root[0]) == 0 and
            child[1] <= root[1] and child[2] <= root[2] and
            child[3] <= root[3])

def main():
    triples = valid = checks = 0
    for root in scopes:
        for mid in scopes:
            for leaf in scopes:
                triples += 1
                if oracle(leaf, mid) and oracle(mid, root):
                    valid += 1
                    assert compressed(leaf, root)
                    for action, label, size in product(range(2), range(2), range(1,3)):
                        leaf_ok = ((leaf[0] & (1 << action)) != 0 and
                                   label <= leaf[1] and size <= leaf[2])
                        root_ok = ((root[0] & (1 << action)) != 0 and
                                   label <= root[1] and size <= root[2])
                        assert not leaf_ok or root_ok
                        checks += 1
    result = {"result": "PASS", "scopes": len(scopes),
              "triples": triples, "attenuating_chains": valid,
              "action_implications": checks}
    print(json.dumps(result, sort_keys=True))

if __name__ == "__main__":
    main()
