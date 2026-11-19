"""Full split census; candidate inputs consist solely of the public source string."""
import hashlib
import json
import sys
from pathlib import Path

from research.lean_recursive_autoformalization_v1 import set_algebra
from research.lean_recursive_autoformalization_v1.capability import formalize_with_rules
from research.lean_recursive_autoformalization_v1.grammar_extensions import RULE_IDS

FILES = {
    "random_test.json": ("nl_problem", "bf769dfa3f0eee25039d32d44641d29851333b2302bb01102248d87221998147"),
    "real_test.json": ("input", "d3ede02ecdf04f722e4a831c60693cdfcde5f10b9b95aed115a17b64722fb147"),
}


def census(directory):
    results = {}
    for name, (field, digest) in FILES.items():
        raw = (directory/name).read_bytes()
        if hashlib.sha256(raw).hexdigest() != digest:
            raise ValueError("wrong release bytes")
        rows = json.loads(raw)
        accepted, baseline, invalid = [], [], []
        for i, row in enumerate(rows):
            source = row[field]
            try:
                proposed = formalize_with_rules(source, frozenset(RULE_IDS))
            except ValueError as exc:
                if str(exc) != "invalid English source":
                    raise
                invalid.append(i)
                proposed = {}
            if proposed.get("candidates"):
                baseline.append(i)
            if set_algebra.parse_english(source) is not None:
                accepted.append(i)
        results[name] = {"population":len(rows),"accepted_row_indices":accepted,
                         "abstained":len(rows)-len(accepted),"phase1_candidate_indices":baseline,
                         "phase1_input_errors":len(invalid), "sha256":digest}
    return results


if __name__ == "__main__":
    print(json.dumps(census(Path(sys.argv[1])), sort_keys=True, indent=2))
