"""Exhaustively compare full-potential-response populations to the Lean wire receiver."""
import hashlib
import json
import subprocess
import tempfile
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from fractions import Fraction
from itertools import combinations_with_replacement, product
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_HASH = "4714a2cb5f1ad1dbf39527c134c5de7ecb5059aea39523a68d57f0a775335e5d"
GRIDS = ((2, 2, 3), (2, 3, 2))


def encode_rows(rows):
    return ";".join(",".join(map(str, row)) for row in rows)


def encode_source(assumption, actions, policy, rows):
    return f"{assumption}|{actions}|{','.join(map(str, policy))}|{encode_rows(rows)}"


def encode_model(model):
    return encode_rows((z, x, sum(y * (2 ** a) for a, y in enumerate(response)))
                       for z, x, response in model)


def compatible_populations(strata, actions, size):
    """Index all complete unit-type multisets by their actual joint observations."""
    responses = tuple(product((0, 1), repeat=actions))
    types = product(range(strata), range(actions), responses)
    groups = defaultdict(list)
    for model in combinations_with_replacement(types, size):
        data = tuple(sorted((z, x, response[x]) for z, x, response in model))
        groups[data].append(model)
    return groups


def classify(model, policy):
    """Compare followers' and nonfollowers' actual potential-response rates."""
    groups = defaultdict(lambda: ([], []))
    successes = 0
    for z, assigned, outcomes in model:
        result = outcomes[policy[z]]
        groups[z][assigned == policy[z]].append(result)
        successes += result
    supported = all(followers for _, followers in groups.values())
    balanced = all(not followers or not others or
                   Fraction(sum(followers), len(followers)) == Fraction(sum(others), len(others))
                   for others, followers in groups.values())
    return successes, supported, balanced


@dataclass
class Replay:
    studies: list[str] = field(default_factory=list)
    proposals: list[str] = field(default_factory=list)
    expected: list[str] = field(default_factory=list)
    counts: Counter = field(default_factory=Counter)

    def add(self, tag, study, proposal, expected):
        self.studies.append(study)
        self.proposals.append(proposal)
        self.expected.append(expected)
        self.counts[tag] += 1

    def run(self, root):
        path = root / "studies.txt"
        path.write_text("\n".join(self.studies) + "\n", encoding="utf-8")
        proc = runner(self.proposals, "--paired", str(path))
        proc.check_returncode()
        got = proc.stdout.splitlines()
        for i, (want, actual) in enumerate(zip(self.expected, got, strict=True)):
            if want != actual:
                raise AssertionError((i, self.studies[i], self.proposals[i], want, actual))


def runner(lines, *args):
    return subprocess.run(["lake", "env", "lean", "--run", "CheckPolicy.lean", *args],
                          cwd=ROOT / "lean", input="\n".join(lines) + "\n", capture_output=True,
                          text=True, timeout=240, check=False)


def exhaustive(replay):
    counts = Counter()
    for strata, actions, max_size in GRIDS:
        policies = tuple(product(range(actions), repeat=strata))
        for size in range(1, max_size + 1):
            for rows, models in compatible_populations(strata, actions, size).items():
                counts["observational_multisets"] += 1
                counts["complete_populations"] += len(models)
                for policy in policies:
                    counts["contexts"] += 1
                    potential = {}
                    eligible = {}
                    excluded = {}
                    for model in models:
                        count, supported, balanced = classify(model, policy)
                        potential.setdefault(count, model)
                        (eligible if supported and balanced else excluded).setdefault(count, model)
                    unrestricted = encode_source("U", actions, policy, rows)
                    exchangeable = encode_source("E", actions, policy, rows)
                    values = sorted(potential)
                    for lo, hi in product(range(size + 2), repeat=2):
                        expected = "REJECT"
                        if values == list(range(lo, hi + 1)):
                            expected = (f"IDENTIFIED {lo}" if lo == hi else
                                        f"PARTIALLY_IDENTIFIED {lo} {hi}")
                        replay.add("intervals", unrestricted, f"B|{lo}|{hi}", expected)
                    for first, second in product(values, repeat=2):
                        m = encode_model(potential[first])
                        n = encode_model(reversed(potential[second]))
                        expected = f"NOT_IDENTIFIED {first} {second}" if first != second else "REJECT"
                        replay.add("witness_pairs", unrestricted, f"W|{first}|{second}|{m}|{n}",
                                   expected)
                    if eligible:
                        if len(eligible) != 1:
                            raise AssertionError(("exchangeability failed to identify", rows, policy))
                        counts["feasible_positive_contexts"] += 1
                    elif supported:
                        counts["positive_infeasible_contexts"] += 1
                    else:
                        counts["unsupported_contexts"] += 1
                    for k, m in eligible.items():
                        witness = encode_model(m)
                        replay.add("adjustments", exchangeable, f"A|{k}|{witness}", f"IDENTIFIED {k}")
                        replay.add("adjustment_value_mutations", exchangeable, f"A|{k + 1}|{witness}",
                                   "REJECT")
                    for k, m in excluded.items():
                        replay.add("inadmissible_adjustment_witnesses", exchangeable,
                                   f"A|{k}|{encode_model(m)}", "REJECT")
    return counts


def directed(replay):
    base = "U|2|1|0,0,0;0,1,0"
    first, second = "0,0,0;0,1,0", "0,0,2;0,1,0"
    witness = f"W|0|1|{first}|{second}"
    cases = [
        (base, witness, "NOT_IDENTIFIED 0 1"),
        (base, f"W|0|1|{second}|{first}", "REJECT"),
        (base, f"W|0|1|{first}|0,0,3;0,1,0", "REJECT"),
        (base, f"W|0|1|{first}|0,0,2;0,0,0", "REJECT"),
        (base, f"W|0|1|{first}|0,0,2", "REJECT"),
        (base.replace("|1|", "|0|"), witness, "REJECT"),
        (base.replace("U", "E"), witness, "REJECT"),
        (base, f"A|0|{first}", "REJECT"),
        (base.replace("U", "E"), "B|0|1", "REJECT"),
        (base, f"W|0|1|{first}|0,0,4;0,1,0", "REJECT"),
        (base, "B|00|1", "REJECT"),
        (base, "B|0|-1", "REJECT"),
        (base, "B|0|1|", "REJECT"),
        (base, "B|0|1\t", "REJECT"),
        (base, "B|0|" + "1" * 8192, "REJECT"),
        (base, "B|0|１", "REJECT"),
        (base, "B|0|1\r", "REJECT"),
        (base, "", "REJECT"),
    ]
    for bad in ["0,2,0", "1,0,0", "0,0,2", "", "0,0,", "0,0,0;", "0,0,0;0,0,0;"]:
        cases.append((f"U|2|1|{bad}", "B|0|0", "REJECT"))
    for bad in ["U|0|0|0,0,0", "U|17|1|0,0,0", "U|2|2|0,0,0", "X|2|1|0,0,0",
                "U|2|" + ",".join(["0"] * 33) + "|0,0,0",
                "U|2|0|" + ";".join(["0,0,0"] * 129)]:
        cases.append((bad, "B|0|0", "REJECT"))
    # All three subjects share one stratum. One of the two followers responds.
    # The equal-weight grid has no population in which total policy success is 3/2.
    cases.append(("E|2|1|0,1,1;0,1,0;0,0,0", "A|1|0,1,2;0,1,0;0,0,0", "REJECT"))
    # Raw follower rate = 3/5; stratum-standardized policy rate = 4/8.
    population = [(0, 1, (0, 1, 0)), (0, 1, (0, 0, 0)), (0, 1, (0, 0, 0)),
                  (0, 0, (0, 1, 0)), (0, 0, (0, 0, 0)), (0, 2, (0, 0, 0)),
                  (1, 2, (0, 0, 1)), (1, 2, (0, 0, 1))]
    rows = [(z, x, y[x]) for z, x, y in population]
    stratified = encode_source("E", 3, (1, 2), rows)
    model = encode_model(population)
    cases.extend([(stratified, f"A|4|{model}", "IDENTIFIED 4"),
                  (stratified, f"A|3|{model}", "REJECT"),
                  (encode_source("E", 3, (0, 2), rows), f"A|4|{model}", "REJECT")])
    for source, proposal, expected in cases:
        replay.add("directed_cases", source, proposal, expected)


def main():
    protocol = hashlib.sha256((ROOT / "POLICY_REPLAY_PROTOCOL.md").read_bytes()).hexdigest()
    if protocol != PROTOCOL_HASH:
        raise AssertionError("protocol hash mismatch")
    subprocess.run(["lake", "build", "PcsPccr.PolicyReceiver"], cwd=ROOT / "lean", check=True,
                   stdout=subprocess.DEVNULL)
    replay = Replay()
    populations = exhaustive(replay)
    directed(replay)
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        replay.run(root)
        context = root / "single.txt"
        context.write_text("U|2|1|0,0,0;0,1,0\n", encoding="utf-8")
        single = runner(["B|0|1", "B|0|0"], str(context))
        single.check_returncode()
        if single.stdout.splitlines() != ["PARTIALLY_IDENTIFIED 0 1", "REJECT"]:
            raise AssertionError("single trusted context mode mismatch")
        extra = runner(["B|0|1", "B|0|1"], "--paired", str(context))
        context.write_text(context.read_text(encoding="utf-8") * 2, encoding="utf-8")
        missing = runner(["B|0|1"], "--paired", str(context))
        if not extra.returncode or not missing.returncode:
            raise AssertionError("paired context stream length mismatch accepted")
    print(json.dumps({"protocol_sha256": protocol, "grids": GRIDS, **populations,
                      "decisions": dict(replay.counts), "paired_decisions": len(replay.studies),
                      "agreement": len(replay.expected), "single_study_decisions": 2,
                      "misaligned_streams_rejected": 2}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
