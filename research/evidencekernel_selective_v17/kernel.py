"""Outcome-blind covariate-balancing assignment, exact finite-population causal inference.

v17 research-only: algebraic selected-assignment histogram + single-pass ATE inversion.
Requires externally fixed covariates, a genuinely random registered draw law, and
independent retention of the complete draw/transcript history. This code does not
prove those physical premises. It is NOT a production PCS authority.
"""
from __future__ import annotations

from fractions import Fraction
from hashlib import sha256
from itertools import combinations, product
from json import dumps, loads
from math import comb
from pathlib import Path

FORMAT = 'pcs-evidencekernel-balanced-selection-v17'
MAX_UNITS = 8
MAX_DRAWS = 4096
MAX_DESIGN_BITS = 32768
MAX_WORLD_ASSIGNMENT_EVALS = 5_000_000


class Reject(ValueError):
    pass


def insist(condition, message):
    if not condition:
        raise Reject(message)


def exact_keys(obj, names, context):
    insist(type(obj) is dict and set(obj) == set(names), context + ': unexpected or missing keys')


def digest(obj):
    return sha256(dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=True,
                        allow_nan=False).encode('utf-8')).hexdigest()


def parse_fraction(s):
    insist(type(s) is str and len(s) <= 30, 'noncanonical rational')
    try:
        x = Fraction(s)
    except (ValueError, ZeroDivisionError) as exc:
        raise Reject('invalid rational') from exc
    insist(str(x) == s, 'noncanonical rational')
    return x


def load_strict(path):
    def pairs(items):
        obj = {}
        for k, v in items:
            insist(k not in obj, 'duplicate JSON object key')
            obj[k] = v
        return obj
    def bad_float(_):
        raise Reject('JSON floats prohibited')
    def bad_const(_):
        raise Reject('nonfinite JSON number')
    raw = Path(path).read_bytes()
    insist(len(raw) <= 1_000_000, 'oversized JSON')
    return loads(raw.decode('utf-8'), object_pairs_hook=pairs,
                 parse_float=bad_float, parse_constant=bad_const)


def fall(n, k):
    """Ordered distinct draws: (n)_k, and zero when k>n."""
    if k > n:
        return 0
    acc = 1
    for j in range(k):
        acc *= n - j
    return acc


def design(protocol):
    """Count selected allocations exactly in O(C(n,k) + unique-score count).

    Let A_s be number of assignments with score >= s, B_s with score > s,
    and m_s=A_s-B_s. The number of equally likely ordered candidate sequences
    whose best score is s equals F(A_s)-F(B_s); by relabeling symmetry, each
    of the m_s equal-score assignments has equal selected mass. F(x) = x^b
    for IID replacement; F(x) = (x)_b for ordered without replacement.
    """
    exact_keys(protocol, ('format', 'n', 'k', 'baseline_covariate', 'candidate_draws',
                          'candidate_law', 'selection_rule', 'null_ate_upper',
                          'max_interval_misses', 'confidence_alpha', 'randomizer_support', 'randomizer_rule'), 'protocol')
    insist(protocol['format'] == FORMAT, 'unsupported format')
    n, k, b = protocol['n'], protocol['k'], protocol['candidate_draws']
    insist(type(n) is int and 2 <= n <= MAX_UNITS and type(k) is int and 1 <= k < n,
           'trial size outside research bound')
    insist(type(b) is int and 1 <= b <= MAX_DRAWS, 'candidate count outside bound')
    law = protocol['candidate_law']
    insist(law in ('iid_with_replacement', 'ordered_without_replacement'), 'unsupported draw law')
    insist(protocol['selection_rule'] == 'minimum_absolute_baseline_imbalance_first_tie',
           'unrecognized selection rule')
    x = protocol['baseline_covariate']
    insist(type(x) is list and len(x) == n and all(type(v) is int and -16 <= v <= 16 for v in x),
           'invalid baseline covariates')
    insist(-1 <= parse_fraction(protocol['null_ate_upper']) <= 1, 'invalid ATE null bound')
    insist(Fraction(0) < parse_fraction(protocol['confidence_alpha']) < 1,
           'confidence alpha must lie strictly between zero and one')
    insist(protocol['randomizer_rule'] == 'independent_right_endpoint_uniform',
           'unsupported randomized-tie rule')
    insist(type(protocol['randomizer_support']) is int and
           2 <= protocol['randomizer_support'] <= 256, 'invalid randomizer support')
    K = protocol['max_interval_misses']
    insist(type(K) is int and 0 <= K <= n, 'invalid miss tolerance')
    space = list(combinations(range(n), k))
    N = len(space)
    insist(law == 'iid_with_replacement' or b <= N, 'insufficient distinct assignments')
    bits = (N.bit_length() * b) if law == 'iid_with_replacement' else (N.bit_length() * min(N, b))
    insist(bits <= MAX_DESIGN_BITS, 'large design integer rejected')
    sx = sum(x)
    scores = [abs(n*sum(x[i] for i in z) - k*sx) for z in space]
    groups = {}
    for i, score in enumerate(scores):
        groups.setdefault(score, []).append(i)
    mass = [0]*N
    above = 0
    F = (lambda count: count ** b) if law == 'iid_with_replacement' else (lambda count: fall(count, b))
    for score in sorted(groups, reverse=True):
        m = len(groups[score])
        wins = F(above + m) - F(above)
        insist(wins >= 0 and wins % m == 0, 'invalid score-symmetry count')
        for i in groups[score]:
            mass[i] = wins // m
        above += m
    denominator = F(N)
    insist(sum(mass) == denominator, 'selected-assignment probability does not normalize')
    return space, scores, mass, denominator


def observed_world_misses(world, observed, labels):
    z = set(observed)
    return sum(label != '01' and label != str(world[i][int(i in z)])
               for i, label in enumerate(labels))


def effect_stat(world, assignment, n, k):
    z = set(assignment)
    return (n-k) * sum(world[i][1] for i in z) - k * sum(world[i][0] for i in range(n) if i not in z)


def evidence_check(protocol, evidence, *, external_pin, space, scores, mass):
    insist(type(external_pin) is str and len(external_pin) == 64 and
           all(c in '0123456789abcdef' for c in external_pin), 'external pin required')
    insist(digest(protocol) == external_pin, 'protocol not matched to independently pinned hash')
    exact_keys(evidence, ('attempts', 'selected_assignment', 'observed_intervals'), 'evidence')
    b, k, n = protocol['candidate_draws'], protocol['k'], protocol['n']
    attempts, z, labels = evidence['attempts'], evidence['selected_assignment'], evidence['observed_intervals']
    insist(type(z) is list and len(z) == k and all(type(i) is int for i in z)
           and z == sorted(set(z)) and tuple(z) in space, 'invalid selected assignment')
    insist(type(labels) is list and len(labels) == n and
           all(type(x) is str and x in ('0', '1', '01') for x in labels), 'invalid binary interval')
    insist(type(attempts) is list and len(attempts) == b, 'missing or extra recorded draws')
    ix = {a:i for i,a in enumerate(space)}
    indices = []
    for a in attempts:
        insist(type(a) is list and len(a) == k and all(type(i) is int for i in a)
               and a == sorted(set(a)) and tuple(a) in ix, 'malformed candidate attempt')
        indices.append(ix[tuple(a)])
    if protocol['candidate_law'] == 'ordered_without_replacement':
        insist(len(set(indices)) == len(indices), 'duplicate assignment without replacement')
    selected_idx = min(indices, key=lambda i: scores[i])
    insist(tuple(z) == space[selected_idx], 'chosen assignment violates registered balance selection')
    insist(mass[selected_idx] > 0, 'allocation impossible under registered design')
    return tuple(z), tuple(labels)


def audit(protocol, evidence, *, external_pin, external_uniform_index=None):
    space, scores, mass, denominator = design(protocol)
    z, labels = evidence_check(protocol, evidence, external_pin=external_pin,
                               space=space, scores=scores, mass=mass)
    n, k = protocol['n'], protocol['k']
    insist(4**n * len(space) <= MAX_WORLD_ASSIGNMENT_EVALS, 'world enumeration exceeds cap')
    K = protocol['max_interval_misses']
    registered_null = parse_fraction(protocol['null_ate_upper'])
    alpha = parse_fraction(protocol['confidence_alpha'])
    M = protocol['randomizer_support']
    if external_uniform_index is not None:
        insist(type(external_uniform_index) is int and 1 <= external_uniform_index <= M,
               'randomizer index outside preregistered range')

    # Single enumeration produces the entire composite-null p-value *curve*,
    # including the chosen weak-null decision and all finite-population ATE cutoffs.
    by_ate = {}
    best_world = {}
    randomized_by_ate = {}
    count_compatible = 0
    for indices in product(range(4), repeat=n):
        world = tuple(((v >> 1) & 1, v & 1) for v in indices)
        if observed_world_misses(world, z, labels) > K:
            continue
        count_compatible += 1
        ate_num = sum(y1-y0 for y0,y1 in world)
        observed_stat = effect_stat(world, z, n, k)
        gt = 0
        eq = 0
        for alt, m in zip(space, mass):
            if m:
                stat = effect_stat(world, alt, n, k)
                if stat > observed_stat:
                    gt += m
                elif stat == observed_stat:
                    eq += m
        hits = gt + eq
        if external_uniform_index is not None:
            randomized_hits = M*gt + external_uniform_index*eq
            if randomized_hits > randomized_by_ate.get(ate_num, -1):
                randomized_by_ate[ate_num] = randomized_hits
        if hits > by_ate.get(ate_num, -1):
            by_ate[ate_num] = hits
            best_world[ate_num] = [''.join(map(str, x)) for x in world]
    insist(count_compatible > 0, 'no compatible potential-outcome model: assumed coverage contradictory')
    prefix_max = -1
    curve = []
    for ate_num in range(-n, n+1):
        if ate_num in by_ate:
            prefix_max = max(prefix_max, by_ate[ate_num])
        curve.append({'ate_upper': str(Fraction(ate_num, n)),
                      'max_p': str(Fraction(prefix_max, denominator)) if prefix_max >= 0 else None,
                      'null_feasible': prefix_max >= 0})
    registered_idx = max(i for i in range(len(curve)) if Fraction(curve[i]['ate_upper']) <= registered_null)
    reported = curve[registered_idx]
    # A confidence lower bound is the first nonrejected ATE cutoff; if no cutoff
    # survives, output an EMPTY_SET flag rather than an impossible effect > 1.
    first_nonrejected = next((c['ate_upper'] for c in curve
                              if c['null_feasible'] and Fraction(c['max_p']) > alpha), None)
    randomized_curve = None
    randomized_report = None
    randomized_lower = None
    randomized_set_status = None
    if external_uniform_index is not None:
        randomized_curve = []
        best_random = -1
        for ate_num in range(-n, n+1):
            if ate_num in randomized_by_ate:
                best_random = max(best_random, randomized_by_ate[ate_num])
            randomized_curve.append({
                'ate_upper':str(Fraction(ate_num,n)),
                'max_p':str(Fraction(best_random, M*denominator)) if best_random >= 0 else None,
                'null_feasible':best_random >= 0})
        randomized_report = randomized_curve[registered_idx]['max_p']
        randomized_lower = next((c['ate_upper'] for c in randomized_curve
                                 if c['null_feasible'] and Fraction(c['max_p']) > alpha), None)
        randomized_set_status = 'NONEMPTY' if randomized_lower is not None else 'EMPTY_SET'
    declared_status = 'CONDITIONALLY_VERIFIED' if reported['null_feasible'] else 'INCONSISTENT_NULL'
    witness = None
    # Determine a maximizer deterministically, preferring earliest ATE numerator.
    if reported['null_feasible']:
        compatible_nums = [t for t in sorted(by_ate)
                           if Fraction(t,n) <= registered_null]
        max_hits = max(by_ate[t] for t in compatible_nums)
        selected_ate_num = next(t for t in compatible_nums if by_ate[t] == max_hits)
        witness = best_world[selected_ate_num]
    return {
        'status':declared_status,
        'conditional_robust_p':reported['max_p'],
        'null_feasible':reported['null_feasible'],
        'compatible_worlds':count_compatible,
        'design_denominator':str(denominator),
        'selected_assignment_mass':str(mass[space.index(z)]),
        'maximizing_world':witness,
        'confidence_alpha':str(alpha),
        'conditional_lower_ate':first_nonrejected,
        'confidence_set_status':'NONEMPTY' if first_nonrejected is not None else 'EMPTY_SET',
        'null_curve':curve,
        'randomized_conditional_p':randomized_report,
        'randomized_conditional_lower_ate':randomized_lower,
        'randomized_confidence_set_status':randomized_set_status,
        'randomized_null_curve':randomized_curve,
        'external_uniform_index':external_uniform_index,
        'randomizer_support':M,
        'protocol_sha256':external_pin,
        'warning':'Conditional result only: candidate draw law, chronology, baseline blindness, interval coverage and complete attempts are external assumptions. Randomized p-values additionally require an independently uniform tie randomizer, not chosen or reset by the researcher.'
    }


def main():
    import argparse
    import json
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('protocol')
    p.add_argument('evidence')
    p.add_argument('--protocol-pin', required=True)
    p.add_argument('--external-uniform-index', type=int, default=None,
                   help='External post-outcome draw in 1..randomizer_support; independence is not authenticated here')
    args = p.parse_args()
    try:
        result = audit(load_strict(args.protocol), load_strict(args.evidence),
                       external_pin=args.protocol_pin, external_uniform_index=args.external_uniform_index)
    except (Reject, ValueError, TypeError, KeyError, OverflowError, OSError) as exc:
        p.exit(2, 'REJECTED: '+str(exc)+'\n')
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
