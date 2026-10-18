# Implementation ledger

Statuses: COMPLETE | PARTIAL | BLOCKED | OPEN | UNSTARTED

| Requirement | Path | Status | Tests | Formal | Limitations |
|---|---|---|---|---|---|
| Isolation + noninterference | `scripts/check_noninterference.py` | COMPLETE | validate_all | n/a | Git isolation ≠ trust |
| Capability inventory | `docs/CAPABILITY_INVENTORY.md` | COMPLETE | n/a | n/a | Snapshot at base SHA |
| Intake + freeze | `pcs_next_v1/pilot/intake.py` | COMPLETE | unit | n/a | Timestamps not prospective proof |
| Pilot state machine | `pcs_next_v1/pilot/state_machine.py` | COMPLETE | unit | n/a | |
| Pilot runner + synthetic E2E | `pcs_next_v1/pilot/runner.py` | COMPLETE | integration | conditional | External lab OPEN |
| Policy pin / producer PASS ignore | `pcs_next_v1/trust/policy.py` | COMPLETE | unit+adv | n/a | |
| Evidence store CAS/chain | `pcs_next_v1/trust/evidence_store.py` | COMPLETE | unit | n/a | Local chain ≠ external anchor |
| Independent reviewer | `pcs_next_v1/reviewer/independent.py` | COMPLETE | adv+integration | n/a | Second-process only |
| Assurance card + workbench | `reviewer/assurance_card.py`, `workbench/` | COMPLETE | integration | n/a | UI non-authoritative |
| Claim IR + formalize | `translation/` | COMPLETE | unit | ClaimIR.lean | Tiny NL fragment |
| POG | `translation/pog.py` | COMPLETE | unit | n/a | |
| Falsification + calibration | `falsification/` | COMPLETE | unit+scientific | n/a | |
| Adapters | `adapters/` | COMPLETE | unit | n/a | Restricted fragments |
| Benchmarks | `benchmarks/suite.py` | COMPLETE | run_benchmarks | n/a | Small suite |
| Proof-gated research | `research/proof_gated/` | PARTIAL | unit | ScalarGuard.lean | Finite domains |
| Lean workspace | `formal/` | PARTIAL | lake if avail | ClaimIR, ScalarGuard, Approx, NCA, Bateman, Units, Conservation, MM, Emax | Discrete Nat fragments only |
| External lab completion | kit docs | OPEN | n/a | n/a | Needs real participant |
| Production integration | proposals | OPEN | n/a | n/a | Human authorization |
| Journal demos (Theoph/Indometh/e-Drug3D/OSP) | `demos/`, `fixtures/journal_demos/` | COMPLETE | scientific+adv | NCA.lean | External lab OPEN; public data only |
| Puromycin MM demo + oracles + cleanroom | `demos/puromycin_demo.py`, `oracles/`, `scripts/run_cleanroom_replay.py` | COMPLETE | unit+scientific | Bateman.lean | Cleanroom ≠ external lab |
| Real-world mutation campaign | `campaigns/real_world_mutation.py` | COMPLETE | integration | n/a | Multi-target suite; catch rate among expected probes; external lab OPEN |
| Unit-aware PK + clearance oracle | `adapters/units.py`, `oracles/units_oracle.py` | COMPLETE | unit+property | Units.lean | Restricted unit vocabulary |
| Tabular / longitudinal integrity | `adapters/tabular_integrity.py` | COMPLETE | unit | Conservation.lean | Registration required for group-label swap |
| Puromycin group-label registration | `demos/puromycin_demo.py` | COMPLETE | scientific | n/a | Needs registration pin |
| Emax PD adapter | `adapters/pd.py` | COMPLETE | unit+bench | Emax.lean | Direct effect only |
| Conservation adapter | `adapters/conservation.py` | COMPLETE | unit | Conservation.lean | Closed-system assumption |
| Metamorphic PK | `adapters/metamorphic_pk.py` | COMPLETE | unit+bench | n/a | Linear IV bolus only |
| OSP CL/AUC consistency | `adapters/osp_consistency.py` | COMPLETE | unit | n/a | Coarse; units often incommensurate |
| Finite improvement certificates | `research/proof_gated/models.py` | COMPLETE | unit+campaign | ScalarGuard.lean | Explicit finite domains only |
| Differential oracle suite | `scripts/run_differential_oracles.py` | COMPLETE | validate_all | n/a | Same-host; external lab OPEN |
