# Delegated Action Gate v1 — experimental authority boundary

**Status: isolated research prototype; not a safety breakthrough or production authorization service.** The purpose is to test multi-agent **authority preservation** when approvals, delegation and resource state change. No real network, file deletion, email, shell command, credential, or external tool is exposed.

The experimental gate admits an action only if the complete parent-to-child Ed25519 grant chain is signature-valid, every child's capabilities and lifetime are subsets of its parent, the exact actor signed the action, the capability is in a host allowlist, the state generation and resource preimage match, and any risky operation has a distinct signed reviewer approval bound to that exact action, chain, version, resource hash and expiry. All checks and synthetic SQLite effects happen behind a `BEGIN IMMEDIATE` writer lock. Revocation rotates the policy epoch and invalidates prior chains.

A hash-linked receipt records every **accepted** state transition. Before each subsequent accepted operation, the complete history is replayed, including signatures and resource effects. A separately retained `expected_head` can detect whole-database rollback, which the database cannot detect on its own. The gate caps history length and resource sizes. Failed attempts are not committed; this is not a complete monitoring or forensic log.

## Reproduce

The only external dependency is `cryptography` (tested against 46.0.4) on Python 3.11+.

After extracting the ZIP, from the **parent directory** of `delegated_action_gate_v1/`:

```sh
python -m pip install 'cryptography>=42,<47'
python -m unittest delegated_action_gate_v1.test_gate -v
python -m delegated_action_gate_v1.demo
```

If copying this package into PCS as `research/delegated_action_gate_v1/`, instead use `python -m unittest research.delegated_action_gate_v1.test_gate -v` and `python -m research.delegated_action_gate_v1.demo` from the repository root.

The simulation uses **fresh disposable signing keys**, a local temporary SQLite file, and six labeled choices; it touches no production surface. The test suite includes cryptographic mutation, cross-agent impersonation, delegation amplification, review spoofing, stale approval replay, historical tampering, clock rollback, epoch revocation, one-winner concurrency, random hostile-input mutations, and exhaustive finite capability-subset checks. Report actual test counts only from a run on the exact file bytes/commit; no CI or Lean execution is claimed here.

## Conditional safety invariant

For each accepted transition `i` at current epoch `e_i`, if trusted signing keys are uncompromised, the host fixes the roots and allowlist outside model-controlled inputs, **all relevant effects are mediated exclusively through this gate**, the local SQLite transaction semantics hold, and the clock is trusted:

1. The action capability is in every authenticated ancestor delegation, with each child inheriting a subset and no longer duration.
2. The action came from the final delegate's signing key, and its state version and resource preimage matched the state at commitment.
3. For risky actions, an independently signed reviewer authorized those exact bytes and the approval was consumed at most once.
4. A changed epoch invalidates previously issued delegations.

This is a precise **implementation-oriented invariant**, supported by tests and a replay checker, **not a kernel-checked theorem or proof of the actual Python/SQLite implementation**.

## High-priority limitations and open problems

- The trust roots, reviewer key, writer access and host clock are assumptions. The `clock` injection exists for testing and must not be controlled by an agent. A developer signing the review in a unit test does **not** establish a real human reviewed anything.
- SQLite is a local simulation of tool effects. Real emails, API calls, filesystem operations, and network side effects cannot generally be rolled back atomically with its transaction. Production integration needs a separately authenticated effect adapter with idempotency or genuine transactional support, and a separate security review.
- An agent given permission can still make harmful choices. There is **no semantic content moderation, information-flow confidentiality, or model-alignment guarantee**; it can write a secret into an authorized public channel.
- A host/root compromise or substitution of both the database and its external checkpoint can defeat audit. Hash chaining by itself is **not tamper-proof storage**. Only an independently retained head anchor detects a consistent database rollback.
- Replay shares the Python verifier and cryptography implementation with admission. This is not independent checker diversity, a Lean-verified refinement or a guarantee about compilers/hardware. The simple ASCII-only wire format and fixed resource set are intentional prototype restrictions.
- Full-history verification is O(history) per action, and accepted history is bounded at 4096; throughput and availability are not established. Rejected attempts are not recorded. `cryptography` version range is not a reproducible hash-pinned deployment environment.
- Tests are authored, synthetic and largely white-box. No fresh third-party benchmark, frontier-model adversarial evaluation, formal noninterference proof, or measured real-world attack prevention is claimed.

**Next research hurdle:** kernel-check an abstract state-transition safety theorem, prove a refinement into the actual admission codec, validate separate out-of-process effect enforcement, and conduct a frozen multi-agent adversarial study with independent reviewers and realistic tool adapters. Do not merge into production authority until these obligations are met.
