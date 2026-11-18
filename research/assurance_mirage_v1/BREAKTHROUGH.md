# Breakthrough claim: sharp blindness of channel-1 scores

## Statement

Under a correcting unique-action guard, a score on episodes is blind to a
constructive safe/unsafe mirage pair **if and only if** it is
channel-1-factorable (depends only on the guarded tool trace).

Lean (kernel-checked, axioms ⊆ `{propext, Quot.sound}`):

- `Channel1Factorable score` := ∃ f, ∀ e, score e = f e.tools
- `channel1_factorable_blind_constructive`: every factorable score ties the pair
- `separates_constructive_not_channel1_factorable`: separation ⇒ ¬ factorable
- `joint_not_channel1_factorable`: the joint score is a separating witness
- Transfer: the same blindness holds for a second lab-notebook correcting program
  (`lab_tool_trace_independent`, `lab_channel1_blind`)

## Why this is the measurement result, not a vibes claim

Agent evaluations that report only guarded tool success / task completion are
channel-1-factorable. The theorems say they **cannot** measure proposer refusal
quality in this model class. Joint scoring of proposals and raw outputs can.

## Empirical counterpart (finite, local)

| Score class | Qwen local weights | Gemini flash-lite |
|---|---|---|
| Channel-1 completion | perfect | perfect |
| Joint detector | flags many attacks | clean on tested suite |

`detect` emits `leaderboard_flip.json`: channel-1 would not distinguish Qwen from
Gemini; the joint detector does. Transfer campaigns on `LabNotebook` reproduce
mirages under the same protocol with remapped actions.

## Non-claims

Not a frontier alignment theorem, not production PCS authority, not a claim that
Gemini is generally safe, not a claim that joint scoring is the unique correct
metric — only that channel-1-factorable metrics are structurally blind here.
