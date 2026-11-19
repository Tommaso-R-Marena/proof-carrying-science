# Statement evaluation at PR #221

Baseline `62cca4472a77ea397a0ccf1c59f73451fe184346`. Python 3.12.14, Lean 4.28.0 on Linux. All 53 original research tests passed at this head. The isolated research Lake project built its three original modules. The production authority and thin experimental Python adapter are outside this experiment.

| Claim | Classification | Evidence and scope |
| --- | --- | --- |
| The historical model stack surpassed PDA | NOT_EVALUATED | 51/80 first-slice items compiled after search. PDA reported 46.28 on 970 under a separate protocol. The local 80 were selected by position and demonstration retrieval read later Basic test rows. Available logs cannot establish exactly which prompts each historical call received. |
| Successful compilation guarantees a faithful translation | REFUTED | Compiled items 0 and 2 changed the subject to topological closure and set cardinality. The historical audit binds each judgment to both the recorded English and candidate bytes. |
| The original three-way comparison can be reproduced by regenerating model outputs | UNREPRODUCIBLE in this run | The recorded first-40 summary differs from its frozen checksum, the other 40 are in a separate file, and some attempts are truncated. The Kimina GGUF, llama-cpp runtime and historical Mathlib project were unavailable. The recount reads recorded rows. |
| The existing controlled grammar covers unrestricted FormL4 Basic | REFUTED for this release | The grammar abstained on 970/970 rows, including eight duplicate English strings. Ground truth, explanations, proofs and demonstrations are excluded from the parser input. Abstention measures coverage, with no human adjudication of its appropriateness. |
| A bounded candidate can be checked against an independently supplied formal reference | EXECUTABLY_VERIFIED | See the kernel inputs and axiom reports in the three-item reference replay. The reference author supplies the relationship to the English. Definitional equality suffices for this checker. Other equivalences can be missed. |
| Recursive training improves general mathematical reasoning | NOT_EVALUATED | The original finite authored corpus and fitting gates delimit the supported conclusion. A pretrained model's benchmark exposure is unknown. |

The historical records contain **28/80** first-candidate compiler successes and **51/80** after **163 logged attempts**. Of the 51 successes, two received retrospective semantic rejection and 49 remain unassessed. Zero proof checks entered that metric. These targeted reviews do not estimate a population error rate. The descriptive Wilson interval in the recount assumes binomial sampling and cannot correct selection or prompt contamination. The 14/16 miniF2F historical result used a compilation proxy, whereas the quoted leaderboard numbers used other acceptance rules and budgets.

## Pinned benchmark protocol

PDA publishes the dataset under CC BY 4.0. At revision `7f65d2c27e79239d754e08af2de84a4cea58acc7` the README reports separate greedy/pass@ figures and the RFT + Verifier table. The file in `code/Automatic-Lean4-Compilation` is an empty placeholder at that revision. We could inspect the published split, inputs and scores, but could not reproduce the original compiler procedure from that file. [Upstream release](https://github.com/rookie-joe/PDA/tree/7f65d2c27e79239d754e08af2de84a4cea58acc7)

The exact Basic file hash fixes all 970 source indices. The standalone census uses the complete split. For a prospective budgeted generation run, `selection_80.json` freezes 80 indices and prompt hashes selected by English-length quartile with seed `pgra-forml4-basic-v1`. The old bundled sample uses IDs that collide with different upstream English and cannot substitute for this file. Only the English passes to the proposer, along with a public row name. Demonstration count is zero. Candidate selection stops at the first elaboration. The first-candidate count and aggregate any-attempt count have different denominators from sampled pass@k. A matched model comparison and a confidence interval for semantic accuracy remain open.

The revised runner freezes its protocol to a fresh output directory before generation and checks for local model weights. New runs explicitly request any Gemini use. This audit made zero model requests and incurred zero API charges. We did not rerun historical neural generation or model-assisted repair.

## Elaboration, source equivalence and proof

The legacy checker rewrote arbitrary theorem text around a proof placeholder. The replacement accepts a single named theorem, lemma or example over explicit Nat, Int, Bool and Prop binders. It translates binders to fresh names and renders only a fixed expression vocabulary into a definition of type Prop with implicit variable creation disabled. An optional exact historical proof placeholder is discarded. The checker invokes Lean on files in fresh temporary directories, with a bounded input size and a per-invocation deadline.

An unsupported statement returns `UNSUPPORTED_SYNTAX` (it may be valid general Lean). Lean parses the emitted term independently and returns `SYNTAX_INVALID` for malformed expressions. Lean rejects well-parsed, ill-typed expressions with `ELABORATION_FAILED`. Success establishes `WELL_TYPED_UNVALIDATED`. Input/project or timeout failures have no authority. A separately supplied reference enables an axiom-free `rfl` check on the equality of whole propositions. Failed definitional equality leaves the semantic verdict open. The printed axiom closure and identical compiler source support independent checking of the result. A third Lean invocation attempts trusted introductory/arithmetic tactics after reference equivalence succeeds. Its axiom allowlist consists of propext, Classical.choice and Quot.sound. The positive regression needs none. The proof branch accepts no model-supplied tactic scripts.

For an alpha-renamed reflexivity statement the checker obtained equality and a proof. Comparing False to itself established equality but yielded no proof. Replacing False by True yielded only elaboration. The fixtures witness these three outcomes; they do not measure language-model performance. The historical Borel and volume rejections are byte-bound editorial rulings. Changing the English or candidate bytes yields UNKNOWN in that judgment table. No claim of automated unrestricted semantic detection follows.

The trusted computing base includes the pinned Lean elaborator/kernel, Std, the trusted research Lake project and its configuration, compiler executable, subprocess host and operating system. The parser, renderer and receipt interpreter connect bytes to kernel inputs. This command accepts a trusted project directory. Proof checking is local; arbitrary projects, arbitrary tactics and untrusted libraries are outside the interface.

## Replay from the repository root

Use the published Python and Lean environment. The first three commands use only repository inputs. The next commands read the pinned upstream Basic file from a separate checkout. Compare regenerated JSON byte-for-byte with the artifacts in `results/statement_integrity/`.

```sh
pkg=research/lean_recursive_autoformalization_v1
mod=research.lean_recursive_autoformalization_v1
out=$(mktemp -d)
python -m pytest -q "$pkg/tests/test_pgra_integrity.py" "$pkg/tests/test_pgra_lean_compile_oracle.py" "$pkg/tests/test_pgra_sota_comparison.py"
python -m "$mod.reference_replay" > "$out/reference_replay.json"
python -m "$mod.historical_statement_audit" > "$out/historical_audit.json"
git clone https://github.com/rookie-joe/PDA.git "$out/PDA"
git -C "$out/PDA" checkout --detach 7f65d2c27e79239d754e08af2de84a4cea58acc7
data="$out/PDA/data/FormL4/basic_test.json"
python -m "$mod.forml4_protocol" "$data" --n 80 > "$out/selection_80.json"
python -m "$mod.forml4_protocol" "$data" --grammar-census > "$out/grammar_census.json"
for f in reference_replay historical_audit selection_80 grammar_census; do
  cmp "$pkg/results/statement_integrity/$f.json" "$out/$f.json" || exit 1
done
```
