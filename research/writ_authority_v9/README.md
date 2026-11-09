# Writ/9 authority chains — isolated PCS research pilot

This is a self-contained reference calculus for hierarchical agent delegation, not a production PCS authority component.

## Research question

Can a composed delegation prevent an autonomous agent from obtaining authority that none of its ancestors held? Each scope consists of permitted actions, a confidentiality ceiling, a payload byte limit, a use quota, and an optional purpose. A child must be no more permissive than its parent. Authorization structurally checks **every** ancestor for live scope, quota, and revocation.

## Source language

    delegate analyst from publisher to research_worker actions publish uses 4 clearance internal limit 512 bytes;
    subdelegate reviewer from analyst to qa_worker actions publish uses 3 clearance public limit 256 bytes;
    subdelegate releaser from reviewer to release_worker actions publish uses 2 clearance public limit 128 bytes;

The standalone core parses these *declarations only*. It does not parse a full Writ policy or authenticate a bearer token. The companion Writ/9 language package adds complete action policies, strict ordered HMAC caveat chains, transactional ancestor quota debits, and pending-effect revocation to the Writ/8 gateway.

## Reproduction from the PCS repository root

    python -m unittest -v research.writ_authority_v9.test_core research.writ_authority_v9.test_trace
    python -m research.writ_authority_v9.verify_bounds

The bounded oracle enumerates 32,768 scope triples and checks non-amplification under every valid chain in that finite domain. The pure trace checker models an unlimited number of sequential admissions (subject to finite initial quotas), separate sibling delegations, inherited revocation, and shared ancestor debit. These Python tests are independent of the companion Writ gateway.

## Formal core

Lean 4.28.0 source: formal/Authority.lean

With the repository's pinned Lean 4 environment activated:

    lean research/writ_authority_v9/formal/Authority.lean

**Kernel verified on GitHub Actions**: [successful Lean 4.28.0 run](https://github.com/Tommaso-R-Marena/proof-carrying-science/actions/runs/42572588843) checked the exact theorem file at commit `29242714adf5fc326c8423697d321fd9f2cfdfe4`. The first attempt hit an HTTP 504 downloading Lean; the successful retry ran `lean research/writ_authority_v9/formal/Authority.lean`. The formal results include arbitrary-depth attenuation, action-scope inheritance, exact quota accounting over an arbitrary finite sequence of atomic successful admissions, no overspending, and inherited revocation. **No Python/SQLite-to-Lean refinement theorem has been proved.** Subsequent PR commits require fresh exact-head checks. The pinned toolchain is not available in the local container; the hosted CI result is a separate, source-bound fact.

## Integration boundary

No production PCS files, policies, proof checkers, claim authority, or existing CI workflow definitions are changed. One additive, research-only GitHub Actions workflow was introduced to actually run the Writ Lean and Python checks. This research PR is intended for independent evaluation before any considered PCS integration. Root signing keys, host process identity, data labels, tool mediation and external delivery remain trusted assumptions. Revocation cannot undo already executed actions; an interrupted worker may leave an uncertain outcome.

This is not a claim that Writ solves general AI safety, proves claims true, or establishes novelty over existing capability-based security systems.
