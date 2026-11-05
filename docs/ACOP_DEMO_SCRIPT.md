# ACoP Demo / Talk Track

## 30 seconds

> We are building Proof-Carrying Science. The basic idea is that a consequential computational claim should travel with independently replayable evidence: the exact artifacts, explicit assumptions, checks or proofs, runtime provenance, signer identity, and what remains unverified. We are starting narrowly with computational biopharma and PK/PD workflows. It does not claim that a biological model is true; it makes the computational evidence and its limits much harder to lose or misstate.

Then ask a question. Do not continue monologuing.

## Best immediate question

> What part of reviewing or handing off a PK/PD or QSP analysis is still surprisingly manual for you?

## Five-minute technical demo

### 0:00–0:45 — Start with the workflow

Show the restricted PK/PD input and two scoped claims. Point out the explicit model-adequacy assumption.

### 0:45–1:30 — Attest

Show the resulting evidence package:

- certificate.json
- report.html
- LIMITATIONS.md
- runtime.json
- package_manifest.json
- package_signature.json
- artifacts/

Do not explain the entire internal architecture.

### 1:30–2:15 — Independent replay

Run/show bundle verification with a pinned signer fingerprint and reviewer policy.

Point out the four separate dimensions:

- scientific replay;
- package integrity;
- signer authenticity;
- reviewer-policy result.

### 2:15–3:00 — Tamper attack

Change the human report or a scientific artifact and show verification reject the modified package.

### 3:00–3:45 — Scientific change

Change a model/input and show that the affected evidence/claim must be re-established rather than silently inheriting the earlier result.

### 3:45–4:20 — Provenance

Show runtime.json or an environment diff. Say explicitly: same runtime helps reproducibility; it does not prove scientific correctness.

### 4:20–5:00 — End on the limitation

Open LIMITATIONS.md and explain that PCS is designed to make overclaiming harder, not easier.

Then ask:

> If I gave you this around one of your real workflows, what is the first thing you would distrust or want checked differently?

## Phrases to avoid

- “PCS verifies biology.”
- “PCS proves the model is correct.”
- “FDA-compliant” or “FDA-approved.”
- “It eliminates model review.”
- “It verifies arbitrary Python.”
- “The Lean kernel is machine checked” until a real successful build is frozen.

## Good objections

If someone says existing tools already provide provenance, ask exactly what they provide and where independent replay/manual review still happens.

If someone says formal verification cannot validate biology, agree. That distinction is part of PCS’s design.

If someone says the extra evidence is too burdensome, ask what the smallest evidence object would have to contain to be worth using.

If someone finds a false accept or misleading status, treat it as the most valuable conversation of the conference.
