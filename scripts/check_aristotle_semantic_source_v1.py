"""Fail closed if the Aristotle Semantic v1 source has not been integrated."""
from pathlib import Path
import json
import sys
ROOT=Path(__file__).resolve().parents[1]
REQUIRED=["formal/PCS/V2/SemanticIR.lean","formal/PCS/V2/SemanticNormalize.lean",
"formal/PCS/V2/TranslationChecker.lean","formal/PCS/V2/TranslationContract.lean",
"formal/PCS/V2/TranslationAuthority.lean","formal/PCS/V2/TranslationJson.lean",
"formal/PCS/V2/ExplanationIR.lean","formal/PCSSemanticCheck.lean",
"formal/tools/run_semantic_fixture_tests.sh",
"formal/fixtures/semantic_translation_v1/expected.json"]
missing=[p for p in REQUIRED if not (ROOT/p).is_file()]
if missing:
 print(json.dumps({"state":"BLOCKED_MISSING_ARISTOTLE_SOURCE","missing":missing},indent=2))
 sys.exit(2)
index=json.loads((ROOT/"formal/fixtures/semantic_translation_v1/expected.json").read_text())
if index.get("schema")!="pcs-semantic-fixtures-v1" or len(index.get("fixtures",[]))!=36:
 raise SystemExit("FAIL_CLOSED: unexpected fixture version/count")
print(json.dumps({"state":"SOURCE_PRESENT_NOT_YET_KERNEL_VERIFIED","fixtures":36}))
