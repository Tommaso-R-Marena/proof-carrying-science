"""Independent reviewer cases. Only the source is passed to the proposed translator."""
import hashlib
import json
from collections import Counter
from pathlib import Path

from research.lean_recursive_autoformalization_v1 import set_algebra
from research.lean_recursive_autoformalization_v1.capability import formalize_with_rules
from research.lean_recursive_autoformalization_v1.grammar_extensions import RULE_IDS

HERE = Path(__file__).resolve().parent


def review():
    raw = (HERE/"cases.json").read_bytes()
    if hashlib.sha256(raw).hexdigest() != "489bfe29eab6173707db526cb3048732c49120b25fec24b209610c7f9dfdef1f":
        raise ValueError("cases changed")
    rows, counts = [], Counter()
    for case in json.loads(raw):
        prior = formalize_with_rules(case["source"], frozenset(RULE_IDS)).get("candidates")
        counts["phase1_proposals"] += bool(prior)
        candidate = set_algebra.parse_english(case["source"])
        row = dict(id=case["id"], baseline_proposed=bool(prior))
        if candidate is None:
            status = "required_abstention" if case["reference"] is None else "missed_answer"
        elif case["reference"] is None:
            status = "out_of_scope_proposal"
        else:
            result = set_algebra.check_pair(case["reference"], candidate)
            row["receiver"] = result
            expected = "KERNEL_CHECKED" if case["valid"] else "COUNTEREXAMPLE"
            status = ("proved" if case["valid"] else "refuted_with_witness") if (
                result["correspondence"] == "EQUIVALENT" and result["proof"] == expected
            ) else "incorrect_or_unverified"
        rows.append(dict(**row,status=status))
        counts[status] += 1
    return dict(counts=counts, rows=rows)


if __name__ == "__main__":
    print(json.dumps(review(), sort_keys=True, indent=2))
