import PCS.V2.Witnesses.AISafetyGolden
import PCS.V2.Witnesses.AISafetyDeployment
import PCS.V2.DistributedContributors

/-!
# Golden AI-safety archive: end-to-end results and adversarial campaign

## What is proved (kernel-checked theorems)

* `aiSafetyGoldenArchive_domain_sound` ‚Äî if the executable authority prints `ACCEPT` on the
  golden raw bytes, then the certified extended authority accepted them, and for every
  obligation graph with which the signed claim `C1` is domain-accepted as the golden trace
  claim, the committed `trace` bytes satisfy the bounded invariant (no action `7`, cumulative
  risk `‚â§ 4` after every step).  No cryptographic hypothesis.
* `aiSafetyGoldenArchive_deployed_safe` ‚Äî the same, transported to a deployed execution
  under the explicit `FaithfulLog` premise.
* Kernel-checked facts about the committed data: the decoded claim, the certified checker's
  PASS on the committed trace, the obligation graph's acceptance against the committed
  evidence, the invariant of the committed trace.
* Rejection explanations: `replay_mismatch_rejects`, `unknown_tag_no_leaf`,
  `duplicate_registry_fails_closed`, and small `decide` theorems for graph attacks.

## What is evaluated (`#guard`, compiled evaluation ‚Äî tests, not proofs)

* `aiSafetyGoldenArchive_verdict = "ACCEPT"` ‚Äî the exact function run by
  `pcs-lean-authority --zip`, on the raw golden bytes;
* the accepted result's artifact table is exactly `[("trace", trace bytes)]` and the golden
  graph is domain-accepted with the golden claim;
* every adversarial mutation is rejected **at the intended stage**.

A direct `decide` proof of `aiSafetyGoldenArchive_verdict = "ACCEPT"` is out of reach (kernel
reduction of the JCS / UTF-8 / SHA-256 stages over the ~7.7 KB archive exceeds 15‚Äì20 minutes
per stage).  The verdict **is** kernel-proved, stage by stage and without `native_decide`, in
`PCT—P–ÄL@ˆÎù8r´