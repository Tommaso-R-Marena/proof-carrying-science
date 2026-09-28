# Launch Sprint to ACoP 2026

**Internal target:** private PCS design-partner alpha ready for live demonstration by October 10, 2026.

Public launch is not required. The target is a credible private technical artifact plus a disciplined discovery process.

## September 28–30 — Freeze the alpha boundary

- No new scientific domains.
- PCS Core + restricted PK/direct-Emax adapter only.
- Preserve the publication firewall.
- Keep evidence accounting exact: do not claim the expanded test/attack suite has run until it actually runs.
- Close obvious package/handoff hazards: stale output, private keys, unsigned report/limitations, ambiguous verifier status.
- Freeze the four verifier dimensions: replay, package integrity, signer authenticity, reviewer policy.
- Register for ACoP if attending; late registration is currently the relevant registration period.

## October 1–3 — Make the demo independently understandable

- Freeze one synthetic PK/PD design-partner demo.
- Generate a signed evidence ZIP from a clean output directory.
- Create a reviewer policy with pinned signer fingerprint.
- Demonstrate a valid replay.
- Demonstrate a tampered artifact/report being rejected.
- Demonstrate a changed input reopening/failing a dependent claim.
- Demonstrate runtime provenance comparison.
- Confirm LIMITATIONS.md is present and signed.
- Prepare a five-minute demo with no architecture detour.

## October 4–7 — Discovery preparation

- Practice the 30-second explanation until it does not rely on formal-methods jargon.
- Prepare the ten discovery questions in ACOP_2026_DISCOVERY_PLAN.md.
- Identify high-priority sessions and organization types.
- Prepare a simple way to record interview notes without collecting sensitive information.
- Do not mass-email generic pitches; target technical conversations.

## October 8–10 — Release rehearsal

- Run the full Python test suite if an executable environment is available.
- Run the full adversarial campaign.
- Run the Lean build if a runner/toolchain becomes available; otherwise carry the explicit OPEN status.
- Perform the pilot release procedure from a clean directory.
- Independently verify the bundle using only the reviewer-side key/policy inputs.
- Record the exact PCS commit used for the demo.
- Freeze a backup offline copy of the demo and evidence package.

## October 11–14 — ACoP

Primary objective: learn, not sell.

Targets:
- 15 substantive problem interviews;
- 5 five-minute demos;
- 3 concrete post-conference technical follow-ups;
- 1–3 offers of a bounded synthetic/de-identified external workflow.

Use FDA/regulatory conversations for terminology and credibility feedback, not sales.

## October 15–16 — Follow-up

- Follow up within 24–48 hours only where a concrete problem surfaced.
- Offer one bounded design-partner run.
- Ask the reviewer to define the claims and acceptance policy.
- Record objections and missing assurance checks verbatim.

## October 17–31 — First external falsification

- Run PCS on a workflow PCS did not author.
- Measure integration time, manual review effort, false-positive/false-negative concerns, and missing adapters.
- Treat a failed/rejected workflow as useful product evidence.
- Decide which repeated manual step becomes the next adapter.

## November — Paid-pilot gate

Only pursue a paid fixed-scope engagement after at least one external design-partner workflow has completed.

Before taking payment, close the entity/payment path and get qualified review of the pilot agreement/SOW, confidentiality, IP, data handling, and limitations language.

## Alpha success criterion

By the end of ACoP, PCS does not need to be universal. It needs to be understandable enough that an independent pharmacometrician can say:

> I know exactly what this artifact checked, what it did not check, who signed it, what assumptions it depends on, and whether I would use it in my review workflow.
