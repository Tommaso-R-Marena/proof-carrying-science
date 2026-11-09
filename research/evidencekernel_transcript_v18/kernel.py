"""Research-only, exact transcript-rank randomization inference (EvidenceKernel v18).

A *single* preregistered allocation-draw mechanism supplies both the selected
assignment and an exact, deterministic tie rank. No extra post-outcome random
number is needed. This module does not authenticate the physical draw process.
"""
from __future__ import annotations

from fractions import Fraction
from itertools import product
from json import dumps
from math import comb
from pathlib import Path

from research.evidencekernel_selective_v17.kernel import (
    FORMAT as V17_FORMAT, Reject, insist, exact_keys, digest, design,
    evidence_check, effect_stat, fall, load_strict, parse_fraction,
)

FORMAT = 'pcs-evidencekernel-transcript-rank-v18'
TIE_RULE = 'conditional_selected_assignment_transcript_rank'
FIELDS = ('format', 'n', 'k', 'baseline_covariate', 'candidate_draws',
          'candidate_law', 'selection_rule', 'null_ate_upper',
          'max_interval_misses', 'confidence_alpha', 'tie_rule')


def v17_adapter(protocol):
    exact_keys(protocol, FIELDS, 'v18 protocol')
    insist(protocol['format'] == FORMAT, 'unsupported protocol')
    insist(protocol['tie_rule'] == TIE_RULE, 'unsupported transcript tie rule')
    return {**{k: v for k, v in protocol.items() if k != 'tie_rule'},
            'format': V17_FORMAT, 'randomizer_support': 2,
            'randomizer_rule': 'independent_right_endpoint_uniform'}


def selected_histogram_after_prefix(space, scores, prefix, suffix, law):
    """Count *every* suffix yielding each winning selected assignment.

    The prefix fixes a running first-minimum winner. For lower-score groups,
    selection symmetry gives each member equal share of suffixes whose strict
    minimum lies in that group. This works for IID and distinct draws.
    """
    N = len(space)
    insist(suffix >= 0, 'negative suffix length')
    used = set(prefix)
    insist(law == 'iid_with_replacement' or len(used) == len(prefix),
           'duplicate candidate in distinct-draw prefix')
    eligible = (set(range(N)) if law == 'iid_with_replacement'
                else set(range(N)) - used)
    insist(law == 'iid_with_replacement' or suffix <= len(eligible),
           'not enough unused draws')
    F = (lambda m: m**suffix) if law == 'iid_with_replacement' else (lambda m: fall(m, suffix))
    winner = min(prefix, key=lambda i: scores[i]) if prefix else None
    boundary = scores[winner] if winner is not None else float('inf')
    counts = [0]*N
    if winner is not None:
        eligible_not_better = sum(scores[i] >= boundary for i in eligible)
        counts[winner] = F(eligible_not_better)
    for s in sorted({scores[i] for i in eligible}):
        if s >= boundary:
            continue
        tied = [i for i in eligible if scores[i] == s]
        above_or_equal = sum(scores[i] >= s for i in eligible)
        strictly_above = sum(scores[i] > s for i in eligible)
        win_sequences = F(above_or_equal) - F(strictly_above)
        insist(win_sequences % len(tied) == 0, 'nonintegral tie-group multiplicity')
        for i in tied:
            counts[i] = win_sequences // len(tied)
    insist(sum(counts) == F(len(eligible)), 'suffix counts do not normalize')
    return counts


def lex_before_histogram(space, scores, attempts, law):
    """Count complete candidate sequences lexicographically *before* attempts,
    grouped by their final winner. No sequence enumeration is used.
    """
    N = len(space)
    ix = {z:i for i,z in enumerate(space)}
    indices = [ix[tuple(a)] for a in attempts]
    result = [0]*N
    prefix = []
    for position, observed in enumerate(indices):
        for alt in range(observed):
            if law == 'ordered_without_replacement' and alt in prefix:
                continue
            after = selected_histogram_after_prefix(
                space, scores, prefix+[alt], len(indices)-position-1, law)
            result = [a+b for a,b in zip(result,after)]
        prefix.append(observed)
    if law == 'iid_with_replacement':
        numeric_lex_rank = sum(v*N**(len(indices)-j-1) for j,v in enumerate(indices))
    else:
        used = set()
        numeric_lex_rank = 0
        for j,v in enumerate(indices):
            smaller_unused = sum(a not in used for a in range(v))
            numeric_lex_rank += smaller_unused*fall(N-j-1,len(indices)-j-1)
            used.add(v)
    insist(sum(result) == numeric_lex_rank, 'inconsistent transcript rank')
    return result


def audit(protocol, evidence, *, external_pin):
    insist(type(external_pin) is str and len(external_pin) == 64 and
           all(c in '0123456789abcdef' for c in external_pin), 'external SHA-256 pin required')
    insist(digest(protocol) == external_pin, 'untrusted or mismatched protocol')
    adapter = v17_adapter(protocol)
    space, scores, mass, total = design(adapter)
    z, labels = evidence_check(adapter, evidence, external_pin=digest(adapter),
                               space=space, scores=scores, mass=mass)
    n, k = protocol['n'], protocol['k']
    insist(4**n*len(space) <= 5_000_000, 'bounded-world capacity exceeded')
    before = lex_before_histogram(space, scores, evidence['attempts'], protocol['candidate_law'])
    observed_index = space.index(z)
    K = protocol['max_interval_misses']
    alpha = parse_fraction(protocol['confidence_alpha'])
    upper = parse_fraction(protocol['null_ate_upper'])
    by_ate = {}
    witnesses = {}
    compatible = 0
    for digits in product(range(4), repeat=n):
        world = tuple(((v >> 1) & 1, v & 1) for v in digits)
        zset = set(z)
        misses = sum(labels[i] != '01' and
                     labels[i] != str(world[i][int(i in zset)]) for i in range(n))
        if misses > K:
            continue
        compatible += 1
        ate = sum(y1-y0 for y0,y1 in world)
        stats = [effect_stat(world, assignment, n, k) for assignment in space]
        threshold = stats[observed_index]
        tail_gt = sum(m for m,s in zip(mass,stats) if s > threshold)
        tie_mass = sum(m for m,s in zip(mass,stats) if s == threshold)
        selected_mass = mass[observed_index]
        rank = before[observed_index]+1
        insist(1 <= rank <= selected_mass, 'invalid conditional ancillary rank')
        # Conditional on selected assignment z, the rank of its candidate
        # transcript is uniform on {1,...,mass[z]}. This is a superuniform
        # tie-breaker *without any additional independent source*.
        hits = tail_gt*selected_mass + rank*tie_mass
        denom = total*selected_mass
        insist(1 <= hits <= denom, 'invalid rank statistic')
        if hits > by_ate.get(ate, -1):
            by_ate[ate] = hits
            witnesses[ate] = [''.join(map(str,pair)) for pair in world]
    insist(compatible, 'no compatible potential-outcome model')
    curve = []
    peak = -1
    for j in range(-n,n+1):
        peak = max(peak, by_ate.get(j,-1))
        curve.append({'ate_upper':str(Fraction(j,n)), 'null_feasible':peak >= 0,
                      'max_p':str(Fraction(peak,total*mass[observed_index])) if peak >= 0 else None})
    # Binary outcomes imply ATE <= 1 without statistical assumptions. The
    # top null is a tautology: report p=1 and never an empty confidence set.
    curve[-1]['max_p'] = '1'
    target = [c for c in curve if Fraction(c['ate_upper']) <= upper][-1]
    first = next((c['ate_upper'] for c in curve if c['null_feasible'] and
                  Fraction(c['max_p']) > alpha), None)
    relevant = [(t,v) for t,v in by_ate.items() if Fraction(t,n) <= upper]
    witness = (witnesses[min(t for t,v in relevant if v == max(x for _,x in relevant))]
               if relevant else None)
    return {
        'status':'CONDITIONALLY_VERIFIED' if target['null_feasible'] else 'INCONSISTENT_NULL',
        'conditional_rank_p':target['max_p'],
        'conditional_lower_ate':first,
        'confidence_set_status':'NONEMPTY' if first is not None else 'EMPTY_SET',
        'compatible_worlds':compatible,
        'design_denominator':str(total),
        'selected_assignment_mass':str(mass[observed_index]),
        'lexicographically_prior_transcripts':str(sum(before)),
        'within_selected_assignment_transcript_rank':str(before[observed_index]+1),
        'within_selected_assignment_transcript_mass':str(mass[observed_index]),
        'confidence_alpha':str(alpha),
        'maximizing_world':witness,
        'null_curve':curve,
        'protocol_sha256':external_pin,
        'warning':'Conditional inference only. Transcript completeness, ex ante protocol pinning, random candidate draws, outcome blindness, and interval coverage are external premises; a submitted transcript does not authenticate them. No auxiliary post-outcome random draw is assumed.'
    }


def main():
    import argparse, json
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('protocol');p.add_argument('evidence')
    p.add_argument('--protocol-pin',required=True)
    a=p.parse_args()
    try:
        result=audit(load_strict(a.protocol),load_strict(a.evidence),external_pin=a.protocol_pin)
    except (Reject, ValueError, TypeError, KeyError, OverflowError, OSError) as exc:
        p.exit(2, 'REJECTED: '+str(exc)+'\n')
    print(json.dumps(result,indent=2,sort_keys=True))

if __name__=='__main__':main()
