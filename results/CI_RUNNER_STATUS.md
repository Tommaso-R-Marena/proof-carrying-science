# CI runner status — 2026-09-28

## Observation

The standalone PCS repository has triggered multiple GitHub Actions workflows. The inspected jobs have completed as failures while exposing **no executed steps** through the GitHub job API. This includes the initial trivial smoke workflow as well as the PCS CI workflow.

The latest inspected PCS job for commit `9068f57381277d346c1e55150e0041e67ab23d04` reported an empty step list. Therefore no repository command such as checkout, Python installation, `pytest`, adversarial testing, Elan installation, or `lake build` is known to have executed in those failed jobs.

## Interpretation

Treat this as an **external CI/runner provisioning blocker**, not as a Python or Lean test failure.

Do not infer that the formal kernel compiled. Do not infer that it failed to compile.

## Local/reference evidence

Before migration, the v0.5 Python candidate executed:

- 44/44 tests passing;
- 16/16 targeted adversarial attacks rejected;
- 0 false accepts in that finite adversarial campaign.

Those results remain implementation evidence, not a formal security proof.

## Required closure

CI is considered restored only when a workflow exposes normal steps and successfully runs:

1. `pytest -q`;
2. `python scripts/adversarial_campaign.py`;
3. the reference certificate round trip;
4. the no-`sorry` formal source audit;
5. `lake build` for the Lean 4.16 kernel.
