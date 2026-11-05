# Kernel-checked integer ReLU certificates (research stack)

This isolated library is stacked above PR #129, initially at
`782be9e1d1744a8c5b848f94aa569fa11efffe91`. It changes no production authority,
existing `ProofGated*.lean` file, PGSI1 codec, store schema or promotion policy.
It imports no new Aristotle output. The original source fence remains enforced.

The new capability is **kernel-checked replay of universal mathematical claims
about finite scalar-input integer ReLU sums**. Python supplies a finite witness;
Lean verifies it and proves its meaning. There is no reliance on the optimized
Python sweep, its branch-selection algorithm or its verdict for theorem validity.

The modeled networks have one scalar integer input, a finite sum of weighted
ReLUs and an output bias. This includes arbitrary finite width, negative output
coefficients, cancellations, redundant units, linear neurons and unbounded
integer inputs. It does not model deeper networks, floating point or GPUs.
The generic Lean theorems have no parameter-width or integer-size restriction.
The executable receiver has explicit resource budgets: 128 total terms, 513
cells, 512-bit emitted integers, 256 claims per batch, 4 GiB Lean memory and a
120-second per-invocation limit. Budget exhaustion fails closed.

## Mathematical contract

`IntegerAffine.lean` proves the local-to-global chain:

- Endpoint/sign checks imply nonnegativity on an entire possibly unbounded cell.
- Verified ReLU branches and their accumulated coefficients equal network
  predictions throughout each cell.
- Checked adjacency and unbounded endpoints cover **every integer**.
- Accepted equivalence certificates imply equality at every integer input.
- Accepted preservation certificates imply that every old-correct integer input
  remains correct; this condition alone can be vacuous.
- Nonvacuity requires an actual correct integer witness. Separate certificates
  can prove that **no** correct integer input exists.
- Accepted maximum certificates prove an error upper bound on the specified
  integer interval and an in-interval witness attaining it.
- Negative decisions require an actual evaluated counterexample.

`PGSI1Bridge.lean` proves that the new network embedding equals the **existing
mathematical PGSI1 neuron prediction for all integers**, for both activations.
Its additional offline guard composes the unchanged finite benchmark predicate,
nonvacuous universal preservation and exact nonincreasing window maximum error.
The theorem includes the peaks' membership in the protected interval.

`CertificateClaims.lean` packages positive, negative, nonvacuity, no-correct-input
and exact-maximum claims into checked batches. `Controls.lean` gives two actual
stronger-guard examples and a proved counterexample outside the protected window.
`Audit.lean` inventories every theorem in these four modules. The receiver rejects
missing/duplicate audit entries, unexpected output or dependencies beyond the
existing approved `propext`, `Classical.choice`, and `Quot.sound` set.

Concrete data proofs use `by decide` and are checked by Lean's kernel. No native
reflection axiom, new axiom, assumed positive verdict or proof placeholder is used.

## Run the data-only receiver

Use Lean 4.28.0; the repository's `scripts/activate_lean_428.sh` installs the pinned
release when needed. From the repository root:

```bash
source scripts/activate_lean_428.sh
python -m unittest discover -s research/proof-gated-self-improvement-v1/kernel/tests -v
```

For the offline stronger PGSI1 guard, create canonical request bytes from the
research directory (replace output paths with fresh paths):

```bash
cd research/proof-gated-self-improvement-v1
python - <<'PY'
from pathlib import Path
from promotion_v2 import canonical
Path('/tmp/pgsi-guard-request.json').write_bytes(canonical({
    'old': {'relu': True, 'weight': 0, 'bias': 0},
    'candidate': {'relu': True, 'weight': 1, 'bias': 1},
    'interval': [-20, 20]}))
PY
python kernel/guard.py --request /tmp/pgsi-guard-request.json \
  --output /tmp/pgsi-guard-proof
```

Optionally add `--bundle /owner/path/to/native-bundle` to require the existing
real pinned native finite authority as well. Build that bundle with the parent
`build_authority.py`; Linux namespace isolation must actually work. With
`PCS_PGSI_AUTHORITY_BUNDLE` set and `PCS_PGSI_REQUIRE_NATIVE=1`, tests require the
real native authorization alongside the mathematical proof. No fake affirmative
verifier is supported. **The guard never promotes a model.** Its receipt records
`promotion_performed: false`; the existing store remains governed by its existing
finite policy. Other store clients are not constrained by this offline guard.

The generic `kernel/replay.py --request ... --output ...` receiver accepts exactly
`property`, `models`, `certificate`, `interval` and `witness`. Models are objects
with `terms: [[coefficient, weight, bias], ...]` and `bias`. Properties are `equal`,
`preserves` or `max_error`; `witness` is null or a correct-input witness for positive
preservation. Supply the **receiver's expected models/property**, not identities
copied uncritically from an unsigned producer package. Certificates retain the
parent format and its historical `kernel_proved: false`; a successful new receipt
and its concrete Lean theorem record the new kernel replay. Old evidence is not
retroactively relabeled.

The receiver accepts only bounded, canonical ASCII JSON and typed integer
constructors. It never interpolates requester-supplied Lean code. It builds the
reviewed checker from source, pins source/object hashes before and after replay,
and rejects substituted compiled checker files. Request and proof identities bind
the original captured bytes, including when a request pathname changes mid-proof. These checks do not establish
an immutable storage root or protect against a compromised owner/kernel.

## Reproduce the exhaustive experiment

```bash
python kernel/campaign.py --output /tmp/pgsi-affine-campaign
python kernel/verify_results.py --folder /tmp/pgsi-affine-campaign \
  --expected kernel/results/v1/RESULTS.json
```

The protocol is saved before evaluating cases. Results include all 16,384 ordered
transitions of the original 128-model lattice, 729 ordered two-unit configurations,
seeded wider networks, exact maxima, model-correctness classification and actual
stronger-guard proofs. Every reported claim must pass a real kernel check.
Bounded brute-force scans are independent compatibility controls, not the basis
of the universal theorem. Runtime/scaling measurements are host observations.

`PROOFS.tar.gz` retains every generated concrete Lean proof module. The inventory
verifier checks bounded archive contents and hashes without extracting or
executing archived code. The data-only receiver is the preferred interface for
untrusted external packages: arbitrary Lean source can execute elaboration/IO
commands, so a hash inventory alone is not authority to run external code.
Unsigned source hashes and logs do not authenticate historical execution.

See [REPORT.md](REPORT.md) for measured results, negative controls, limits and the
next proof/integration milestones.
