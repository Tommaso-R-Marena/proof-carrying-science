"""Exact, design-aware binary finite-population inference after outcome-blind rerandomization.

Research-only; not a PCS authority. Standard library, exact rational arithmetic.
The physical independence / exchangeability of randomness is an external premise.
"""
from __future__ import annotations

from fractions import Fraction
from hashlib import sha256
from itertools import combinations, product, permutations
from json import dumps
from math import perm
from pathlib import Path

FORMAT = 'pcs-evidencekernel-outcome-blind-selection-v16'
MAX_UNITS = 7
MAX_CANDIDATE_TUPLES = 20000
MAX_WORLD_ASSIGNMENT_EVALS = 2_000_000


class Reject(ValueError):
    """Explicit fail-closed rejection of untrusted evidence."""


def insist(ok, why):
    if not ok:
        raise Reject(why)


def exact_keys(obj, fields, context):
    insist(type(obj) is dict and set(obj) == set(fields), f'{context}: unexpected or missing fields')


def canonical_bytes(obj):
    return dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode()


def digest(obj):
    return sha256(canonical_bytes(obj)).hexdigest()


def parse_fraction(s):
    insist(type(s) is str and len(s) <= 30, 'noncanonical rational')
    try:
        x = Fraction(s)
    except (ValueError, ZeroDivisionError) as exc:
        raise Reject('invalid rational') from exc
    insist(str(x) == s, 'noncanonical rational')
    return x


def parse_json_file(path):
    def pairs(items):
        d = {}
        for k, v in items:
            insist(k not in d, 'duplicate JSON object key')
            d[k] = v
        return d
    def bad_constant(x):
        raise Reject('nonfinite JSON number')
    data = Path(path).read_bytes()
    insist(len(data) <= 1000000, 'JSON document exceeds one-megabyte cap')
    text = data.decode('utf-8', errors='strict')
    from json import loads
    result = loads(text, object_pairs_hook=pairs,
                   parse_float=lambda _: (_ for _ in ()).throw(Reject('floating JSON number')),
                   parse_constant=bad_constant)
    insist(all(not (0xd800 <= ord(c) <= 0xdfff) for c in str(result)),
           'lone surrogate prohibited')
    return result


def assignment_universe(n, k):
    insist(type(n) is int and 2 <= n <= MAX_UNITS and type(k) is int and 1 <= k < n,
           'trial size outside bounded research domain')
    return list(combinations(range(n), k))


def design_distribution(protocol):
    """Integer histogram of selected assignment under all registered candidate tuples.

    Uniform draws are with replacement or ordered without replacement.
    The selection rule is outcome-blind: smallest absolute baseline imbalance,
    with ties resolved in favor of the *earliest candidate*.
    """
    exact_keys(protocol, ('format', 'n', 'k', 'baseline_covariate', 'candidate_draws',
                          'candidate_law', 'selection_rule', 'null_ate_upper', 'max_interval_misses'), 'registered protocol')
    insist(protocol['format'] == FORMAT, 'unsupported protocol format')
    n, k = protocol['n'], protocol['k']
    space = assignment_universe(n, k)
    x = protocol['baseline_covariate']
    insist(type(x) is list and len(x) == n and all(type(v) is int and -16 <= v <= 16 for v in x),
           'invalid externally fixed covariates')
    b = protocol['candidate_draws']
    law = protocol['candidate_law']
    insist(type(b) is int and 1 <= b <= 3 and law in ('iid_with_replacement', 'ordered_without_replacement'),
           'unsupported candidate drawing design')
    insist(protocol['selection_rule'] == 'minimum_absolute_baseline_imbalance_first_tie',
           'unsupported outcome-blind selection function')
    insist(-1 <= parse_fraction(protocol['null_ate_upper']) <= 1, 'invalid registered null')
    insist(type(protocol['max_interval_misses']) is int and 0 <= protocol['max_interval_misses'] <= n,
           'invalid registered failure budget')
    N = len(space)
    insist(law != 'ordered_without_replacement' or b <= N, 'cannot draw distinct assignments')
    total = N**b if law == 'iid_with_replacement' else perm(N, b)
    insist(total <= MAX_CANDIDATE_TUPLES, 'candidate universe exceeds fail-closed cap')
    sx = sum(x)
    scores = [abs(n * sum(x[i] for i in z) - k * sx) for z in space]
    h = [0]*N
    iterator = product(range(N), repeat=b) if law == 'iid_with_replacement' else permutations(range(N), b)
    for draw in iterator:
        chosen = min(draw, key=lambda i: scores[i])
        h[chosen] += 1
    insist(sum(h) == total, 'internal design mass mismatch')
    return space, scores, h, total


def observation_misses(world, assignment, labels):
    z = set(assignment)
    outcomes = [world[i][int(i in z)] for i in range(len(world))]
    return sum(label != '01' and label != str(outcome) for label, outcome in zip(labels, outcomes))


def effect_stat(world, z, n, k):
    treated = set(z)
    return (n-k)*sum(world[i][1] for i in treated) - k*sum(world[i][0] for i in range(n) if i not in treated)


def robust_test(protocol, evidence, *, external_pin):
    """Exact composite weak-null p and a maximizing latent-world witness.

    This function checks a *reported attempt transcript* against the pinned
    selection rule. Completeness / unbiased generation of attempts are NOT proven.
    """
    insist(type(external_pin) is str and len(external_pin) == 64 and
           all(c in '0123456789abcdef' for c in external_pin), 'external SHA-256 pin required')
    insist(digest(protocol) == external_pin, 'protocol differs from independent pin')
    space, scores, mass, total = design_distribution(protocol)
    n, k, b = protocol['n'], protocol['k'], protocol['candidate_draws']
    exact_keys(evidence, ('attempts', 'selected_assignment', 'observed_intervals'), 'observed evidence')
    attempts = evidence['attempts']
    z = evidence['selected_assignment']
    labels = evidence['observed_intervals']
    insist(type(attempts) is list and len(attempts) == b, 'missing or extra allocation attempt')
    insist(type(z) is list and len(z) == k and all(type(i) is int for i in z) and
           z == sorted(set(z)) and tuple(z) in space, 'invalid reported treatment allocation')
    insist(type(labels) is list and len(labels) == n and all(v in ('0', '1', '01') for v in labels),
           'invalid binary uncertainty labels')
    indexed = {a:i for i,a in enumerate(space)}
    candidate_indices = []
    for attempt in attempts:
        insist(type(attempt) is list and len(attempt) == k and
               all(type(i) is int for i in attempt) and attempt == sorted(set(attempt)) and
               tuple(attempt) in indexed, 'invalid allocation attempt')
        candidate_indices.append(indexed[tuple(attempt)])
    if protocol['candidate_law'] == 'ordered_without_replacement':
        insist(len(set(candidate_indices)) == len(candidate_indices), 'repeated assignment in without-replacement design')
    winner = min(candidate_indices, key=lambda i: scores[i])
    insist(list(space[winner]) == z, 'reported allocation does not follow selected candidate rule')
    zi = indexed[tuple(z)]
    insist(mass[zi] > 0, 'reported allocation impossible under preregistered design')
    max_misses = protocol['max_interval_misses']
    h0 = parse_fraction(protocol['null_ate_upper'])
    # Resource cap accounts for all latent worlds, not only the favorable ones.
    insist(4**n * len(space) <= MAX_WORLD_ASSIGNMENT_EVALS, 'latent world search exceeds cap')
    observed = tuple(z)
    best = -1
    witness = None
    worlds_compatible = 0
    for indices in product(range(4), repeat=n):
        world = tuple(((v >> 1)&1, v&1) for v in indices)
        if observation_misses(world, observed, labels) > max_misses:
            continue
        if Fraction(sum(y1-y0 for y0,y1 in world),n) > h0:
            continue
        worlds_compatible += 1
        threshold = effect_stat(world, observed, n, k)
        hits = sum(weight for target, weight in zip(space, mass)
                   if weight and effect_stat(world, target, n, k) >= threshold)
        if hits > best:
            best = hits
            witness = [''.join(map(str, pair)) for pair in world]
    if best < 0:
        # An impossible composite null is NOT accepted as a scientific discovery:
        # a contradictory/null-incompatible model should be flagged separately.
        return {'status':'INCONSISTENT_NULL', 'conditional_robust_p':None,
                'compatible_worlds':0,'design_denominator':total,'protocol_sha256':external_pin}
    return {'status':'CONDITIONALLY_VERIFIED', 'conditional_robust_p':str(Fraction(best,total)),
            'tail_mass':best,'design_denominator':total, 'compatible_worlds':worlds_compatible,
            'maximizing_world':witness,'protocol_sha256':external_pin,
            'warning':'Randomness, chronology, baseline blindness, interval calibration and complete attempt custody are unverified external premises.'}


def main():
    import argparse
    import json
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('protocol');p.add_argument('evidence');p.add_argument('--protocol-pin',required=True)
    args=p.parse_args()
    try:
        r=robust_test(parse_json_file(args.protocol),parse_json_file(args.evidence),
                      external_pin=args.protocol_pin)
    except (Reject,ValueError,TypeError,KeyError,OverflowError,OSError) as e:
        p.exit(2,'REJECTED: '+str(e)+'\n')
    print(json.dumps(r,sort_keys=True,indent=2))


if __name__=='__main__':
    main()
