# Finite tool-use action shield

This authored finite model is an illustrative AI-agent monitor, not deployment
measurements or a claim that real tool behavior has been identified exhaustively.

| State ID | Meaning in this explicit model |
|---|---|
| 0 | Request has not received review |
| 1 | Reviewed authorization grant exists |
| 2 | Confidential payload is loaded |
| 3 | Payload has been sanitized |
| 4 | Task is complete |
| 5 | Unauthorized disclosure has occurred (unsafe) |

| Action ID | Proposed tool action |
|---|---|
| 0 | Request review |
| 1 | Load confidential payload |
| 2 | Sanitize payload |
| 3 | Send on network |
| 4 | Complete / idle |
| 5 | Explicitly forbidden bypass action |

Review has two possible outcomes (remaining unreviewed or obtaining a grant).
Sending a confidential payload has both safe and unsafe modeled successors.
The shield blocks that action even when a submitted observed run used its safe
successor. It instead permits review, authorized loading, sanitization, sanitized
network sending, and completion. A forbidden bypass remains blocked even for a
declared edge whose target is safe; action exclusion and state preservation are
separate obligations.

The certificate checks all declared successors and then Lean induction proves
the state invariant and forbidden-action exclusion for **every finite admitted
history**, of any length and under any proposing policy. It does not establish
liveness or maximal permissiveness. An all-deny certificate can preserve safety
and deadlock; replay reports reachable deadlocks and keeps liveness OPEN.

The three deployment premises in `model.json` remain OPEN: transition-model
completeness, accurate state/action observations, and enforcement without a bypass.
A changed or incomplete model receives a different identity. A certificate for
that changed model cannot establish its correspondence to the original deployed
system. Source/parser/compiler correspondence and empirical safety require
separate evidence.

Run the first-party finite-model/kernel campaign with a new output directory:

```sh
python scripts/run_action_shield_campaign_v1.py --output /tmp/pcs-action-shield-new
```

No untrusted project code, proof-generation trace or training data is executed.
