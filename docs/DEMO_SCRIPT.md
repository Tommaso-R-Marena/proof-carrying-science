# PCS product demo script

Target length: 4–6 minutes.

## 1. Problem — 30 seconds

"Scientific teams increasingly make consequential decisions from computational workflows, but the evidence is fragmented across code, data, environments, notebooks, validation reports, and human review. PCS packages a scoped claim together with independently replayable evidence and makes the remaining assumptions explicit."

Do **not** say that PCS proves a biological model true.

## 2. The four assurance dimensions — 45 seconds

Open the homepage and point to:

1. scientific replay;
2. package integrity;
3. signer authenticity;
4. reviewer policy.

Explain that these deliberately answer different questions.

A package can replay correctly but be unsigned.
A signed package can still fail reviewer policy.
A computational model can be correctly implemented but empirically inadequate.

## 3. Clean PK/PD run — 60 seconds

Open `demo.html`.

Keep the default synthetic model:

- Dose = 100 mg;
- V = 20 L;
- CL = 2 L/h;
- one-compartment IV bolus;
- direct Emax PD.

Click **Verify package**.

Expected visual result:

- Scientific replay: PASS
- Package integrity: PASS
- Signer authenticity: VERIFIED
- Reviewer policy: PASS
- `C_PKPD_CONTRACT`: supported
- `C_PKPD_REPLAY`: supported

Say:

"The production CLI performs this against actual packaged artifacts, hashes, runtime provenance, signatures, and a reviewer-supplied policy. The browser version is only the explanatory visualization."

## 4. Tamper attack — 60 seconds

Toggle **Tamper delivered result**.

Show that the observed concentration changes while the declared model does not.

The illustrative verifier moves the replay claim to failure and invalidates the package/authentication path.

Say:

"The important property is that the producer does not get to leave PASS in the certificate after changing the artifact. The production verifier replays supported checks from the packaged bytes."

## 5. Reviewer-controlled policy — 45 seconds

Restore the clean package and toggle **Require formal proof**.

The computation can still replay correctly, but reviewer policy fails.

Say:

"This is intentional. PCS does not let the producer define what 'acceptable' means. The receiving organization can require a stronger assurance class."

## 6. Show actual CLI — 60 seconds

Use a terminal if appropriate:

```bash
pcs init pilot --template pkpd --subject demo
pcs keygen --private-key signing-private.pem --public-key signing-public.pem
pcs attest pilot/manifest.json -o pilot-evidence \
  --private-key signing-private.pem \
  --public-key signing-public.pem
pcs verify-bundle pilot-evidence.zip \
  --public-key signing-public.pem \
  --require-signature \
  --policy policies/pkpd_design_partner.example.json
```

Then show:

- `certificate.json`
- `report.html`
- `limitations.json`
- runtime provenance
- package manifest/signature.

## 7. Close — 30 seconds

"The first product is not universal formal verification. It is a bounded computational-assurance pilot for scientific workflows. We start with expensive, review-heavy biopharma computation, learn which assurance obligations recur, and convert those recurring obligations into maintained adapters."

Then ask the design partner:

"What is one computational workflow where a subtle error, irreproducible handoff, or review failure would be expensive enough that you would want this evidence package?"
