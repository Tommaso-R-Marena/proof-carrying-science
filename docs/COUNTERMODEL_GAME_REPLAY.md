# Independent replay of actual game choices

Download a local search notebook from the website's Countermodel Lab and run:

```sh
pcs countermodel-replay-v1 pcs-countermodel-implication-flip-local.json
```

This independent Python implementation recomputes every world, formula outcome,
feedback/hint exposure, reward, final counterexample and score from the bounded
typed choices. It uses the pinned seven-mission formula inventory and accepts no
submitted labels, personal fields or executable code. It is separate from the
JavaScript evaluator used by the browser and Worker.

Exit 0 means the final action checks an actual finite counterexample. Exit 1
means the choices replay correctly but do not finish with a counterexample;
earlier success never survives an unchecked edit or subsequent hint as a final
verified result. Exit 2 rejects malformed, forged or unsupported input. A bare
`{version, mission_id, actions}` session is also accepted. Files are limited to
32 KiB and duplicate JSON keys are rejected.

Hints include guided tutorials and model assistance in the game. Replaying
their flags allows the trainer to exclude assisted episodes from unassisted
demonstration fitting. Flags cannot authenticate human independence: a script
can record identical choices. This command grants neither research consent nor
proof of account provenance. Verified-email/adult opt-in donation, owner-only
deidentified export and self-service deletion remain website server operations.

This is deterministic finite first-order evaluation over explicit worlds with
one to three entities. It is not a Lean kernel run, scientific authority, a
claim about every domain size or a guarantee about a deployed AI. Concrete
downloaded Lean witnesses still require actual compilation. The existing
`pcs countermodel-check-v1 witness.json` independently checks a final witness;
the replay command additionally checks the path that produced it.
