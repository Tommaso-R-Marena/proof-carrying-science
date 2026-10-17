# Whole-integer pointwise error dominance (research only)

This isolated extension closes the worsening-tail gap demonstrated in
[`../kernel/REPORT.md`](../kernel/REPORT.md). A received positive certificate
proves, for the three exact encoded mathematical networks,

```
forall x : Int, abs(candidate(x) - target(x)) <= abs(incumbent(x) - target(x))
```

The scope is finite flat sums of scalar-input ReLUs with integer coefficients,
integer parameters and an integer output bias. The target is another such sum.
There is no restriction of the theorem to a bounded test window.

`Pointwise.lean` proves the checker sound. It derives preservation of every
previously correct integer prediction, every existing error bound on any modeled
domain, finite-list aggregate absolute error, and transitivity across updates.
`guard_sound` composes dominance with the unchanged finite PGSI1 admissibility
specification. This mathematical composition does not change runtime authority.

## Replay

Use Lean 4.28.0 and the existing project configuration. From the research root:

```sh
python -m unittest discover -s pointwise/tests -v
python pointwise/campaign.py --output /absolute/fresh/campaign-directory
python pointwise/verify_results.py --folder /absolute/fresh/campaign-directory \
  --expected pointwise/results/v1/RESULTS.json
```

A receiving party supplies a canonical ASCII JSON request with exactly `models`
and `certificate`. `models` is an ordered list `[incumbent,candidate,target]`;
each model contains exactly `bias` and `terms`, with each term represented as
`[coefficient,weight,bias]`. Generate certificate data with
`dominance.certificate(old,new,target)` and serialize with the existing canonical
JSON encoder. Then run:

```sh
python pointwise/receive.py --request /absolute/request.json \
  --output /absolute/fresh/replay-directory
```

The receiver binds the certificate to its requested models, accepts only bounded
typed numeric fields, creates proof source from a fixed template, and invokes
the real Lean kernel. Positive claims require a complete ordered covering of all
integers. Negative claims require a concrete integer where candidate error is
strictly larger. A successful negative replay proves rejection, not dominance.
Read the request and theorem, not merely a receipt's successful-execution flag.

The checker recomputes each model's affine form from its terms. The producer
splits at activation thresholds and both error zero crossings. Lean independently
checks form correctness, absolute-value signs and nonnegative error margins on
each entire cell, including both infinite tails. Producer verdicts have no proof
authority. `kernel_proved` remains false in producer certificates.

## Trust and integration boundary

The CLI records the original request bytes once, hashes source inventories and
generated proofs, and pins compiled checker files during replay. These checks
detect accidental drift and tested substitution attacks. They do not establish
immutability against a compromised host owner or Lean installation. The host,
kernel/toolchain, Python orchestration and artifact storage remain trusted for
execution and evidence attribution. Unsigned evidence is not authenticated.

There is no model promotion, inference-path change, credential boundary or new
production policy. Python/Lean semantic refinement, native compiler refinement,
floating-point/GPU behavior and deployment correctness are not proved here.
Earlier PGSI1 codec compatibility and isolated native-authority tests continue
unchanged in the parent stack. Future Aristotle codec/proof results require a
separate reviewed integration and complete differential testing.

The experiment is synthetic exact mathematics and bounded algorithm testing.
It supplies no external scientific validation, learned adaptive proposer,
accelerating recursive self-improvement or assurance about unmodeled tasks.

Keep all earlier source-bound evidence and formal modules unchanged. New source
and retained results live entirely here; CI is an additional research job.
