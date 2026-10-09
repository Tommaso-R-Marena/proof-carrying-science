#!/usr/bin/env bash
# End-to-end bounded translation example (PCS Semantic Intelligence v2), exercising the real
# compiled authority.  Writes a reproducible artifact directory with every intermediate object:
#   examples/semantic_v2_end_to_end/
#     authority.json             approved registry + authorized receipt keys (Ed25519, test seeds)
#     request.json               authenticated selected interpretation + candidate (no certificate)
#     decision.json              `pcs-semantic-check --v2` output: outcome, certificate found by the
#                                untrusted search and re-checked, Explanation IR, CNL, views
#     training_record.json       `--v2-record` checker-derived feedback record
#     mistranslation_request.json / mistranslation_decision.json   a ∀→∃ mistranslation
#     countermodel_bundle.json   the countermodel from that decision, re-verified independently
#     grounding.txt              registry checked against the real Lean environment
#     Rendered.lean / elaboration.txt   the exact rendered statement, elaborated by Lean
#     TRUST_ASSUMPTIONS.txt      what is proved, what is external
# Usage (from the project root, after `lake build`): bash tools/run_semantic_v2_end_to_end.sh
set -u
BIN=.lake/build/bin/pcs-semantic-check
FIX=fixtures/semantic_intelligence_v2
OUT=examples/semantic_v2_end_to_end
mkdir -p "$OUT"
cp "$FIX/authority.json" "$OUT/authority.json"
cp "$FIX/requests/pos_bio_search_certificate.json" "$OUT/request.json"
cp "$FIX/requests/neg_forall_to_exists.json" "$OUT/mistranslation_request.json"
set +e
$BIN --v2 "$OUT/authority.json" "$OUT/request.json" > "$OUT/decision.json"; rc1=$?
$BIN --v2 "$OUT/authority.json" "$OUT/mistranslation_request.json" > "$OUT/mistranslation_decision.json"; rc2=$?
set -e
$BIN --v2-record "$OUT/authority.json" "$OUT/request.json" machine-generated-fixture "$(git rev-parse HEAD 2>/dev/null || echo unknown)" > "$OUT/training_record.json"
python3 - "$OUT" <<'PY'
import json, sys
out = sys.argv[1]
req = json.load(open(f"{out}/mistranslation_request.json"))["request"]
dec = json.load(open(f"{out}/mistranslation_decision.json"))
bundle = {"candidate": req["candidate"]["claim"], "countermodel": dec["semantic_status"]["countermodel"],
          "interpretation": req["interpretation"]["selected"], "schema": "pcs-countermodel-v1"}
open(f"{out}/countermodel_bundle.json", "w").write(
    json.dumps(bundle, sort_keys=True, separators=(",", ":"), ensure_ascii=False))
PY
cm=$($BIN --check-countermodel "$OUT/authority.json" "$OUT/countermodel_bundle.json")
# grounding of every registry entry in the real Lean environment
lake env lean --run tools/CheckRegistryGrounding.lean "$OUT/authority.json" > "$OUT/grounding.txt"; rcg=$?
# elaboration of the exact rendered Lean statement of the certified candidate
python3 - "$OUT" <<'PY'
import json, sys
out = sys.argv[1]
src = json.load(open(f"{out}/decision.json"))["expected_lean_source"]
open(f"{out}/Rendered.lean", "w").write(
    "import PCS.Examples.Agent\nimport PCS.Examples.Repro\nimport PCS.Examples.Bio\n\n"
    "/-- The exact Lean rendering of the certified candidate (elaborated by Lean). -/\n"
    f"def pcs_certified_claim : Prop := {src}\n")
PY
lake env lean "$OUT/Rendered.lean" > "$OUT/elaboration.txt" 2>&1; rce=$?
cat > "$OUT/TRUST_ASSUMPTIONS.txt" <<'TXT'
KERNEL-PROVED (Lean 4.28.0, see PCS_PROOF_CARRYING_SEMANTIC_INTELLIGENCE_V2_REPORT.md):
  * CERTIFIED_TRANSLATION  =>  the raw request bytes decode to a request whose selected
    interpretation and candidate are denotationally equivalent in every model and valuation
    (accepted_wire_translation_preserves_semantics), all gates hold (semanticCheckV2_certified_sound),
    and the receipts are signed by authorized keys of the right role and bound to the exact
    interpretation / Lean source (semantic_authority_cannot_be_bypassed_by_unsigned_receipts).
  * VALID_COUNTERMODEL  =>  the bundle decodes to two claims and a registry-conforming finite
    structure, with every approved sort inhabited, in which they differ (countermodel_bundle_sound,
    countermodel_refutes_inhabited_equivalence).
  * The Explanation IR and the CNL sentences mean the accepted claim
    (explanationIR_preserves_semantics, controlled_language_render_preserves_semantics).
EXECUTABLE-TESTED (not proved): that the compiled binary computes the pure Lean functions
  (Lean compiler + runtime), JSON file IO.
EXTERNAL TRUST ASSUMPTIONS:
  * Ed25519 signing keys are held only by the authorized confirmation / elaboration / proof
    processes, and those processes are honest (they sign only what they checked).
  * The authorized confirmation records a human / authorized choice of interpretation; it is
    NOT a proof of the speaker's intent.
  * Lean elaboration and kernel checking of the rendered source happen outside this checker
    (attested by receipts), and the elaboration bridge maps the rendered Lean statement to the
    intended model.
  * Registered symbols mean what their Lean definitions say; registry names alone do not fix
    meaning (registry_name_does_not_fix_meaning).  The example symbols in PCS/Examples/*.lean
    are uninterpreted `opaque` placeholders: no AI-safety, reproducibility or biological fact
    is asserted.
  * The fixture elaboration / proof receipts are signed with PUBLIC TEST KEYS.  They exercise
    the receipt-verification path; they are NOT evidence that any statement was kernel-proved.
EXECUTABLE-CHECKED HERE (meta level, not a Lean theorem): grounding.txt (every registry entry
  is a real non-axiom declaration with exactly the registered signature) and elaboration.txt
  (the exact rendered Lean statement elaborates against those declarations).
TXT
echo "certified example: exit $rc1 ($(python3 -c "import json;print(json.load(open('$OUT/decision.json'))['outcome'])"))"
echo "mistranslation:    exit $rc2 ($(python3 -c "import json;print(json.load(open('$OUT/mistranslation_decision.json'))['outcome'])"))"
echo "countermodel re-verification: $cm"
echo "registry grounding in Lean environment: exit $rcg ($(tail -1 "$OUT/grounding.txt"))"
echo "rendered Lean statement elaborates: exit $rce"
[ $rc1 -eq 0 ] && [ $rc2 -eq 3 ] && [ "$cm" = VALID_COUNTERMODEL ] && [ $rcg -eq 0 ] && [ $rce -eq 0 ]
