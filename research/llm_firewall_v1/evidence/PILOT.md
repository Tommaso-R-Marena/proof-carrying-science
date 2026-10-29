# Retained unqualified three-endpoint pilot

`pilot-v1.json` contains the original request/response/source bytes and results at
`cf782d0f9cdacc5ea6ff809bc0cb702f297e373b`. It is historical evidence and is not
used as the qualified primary fixture. Original `complete=false` is preserved.

The 75 requests include 23 to the requested Gemma endpoint. Nineteen report the
different ID `@cf/google/gemma-4-26b-a4b-it-external`; the strict identity check
refused them. The pilot contains 44 completed one-proposal cases and 6 completed
agent tasks, not a complete 60-case/9-agent result. No equivalence between the two
Gemma IDs or their weights was established. The endpoint was subsequently excluded
from the primary evaluation; the identity check was not relaxed.

The pilot also found that a refused attack with no utility criterion received
`utility=false`, which incorrectly expanded the utility denominator. Its original
metrics are retained, with that defect explicitly disclosed. The corrected primary
run restricts utility to the six preregistered benign criteria per model.

No formal policy, byte codec, compiled enforcement rule or SQLite broker behavior
was changed to obtain the primary results. Only the reporting cohort and choice
of identified model endpoints changed. Both runs retain their exact protocol/source
hashes. These are synthetic experiments, not external validation of model weights.
