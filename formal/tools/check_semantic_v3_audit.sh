#!/usr/bin/env bash
# Elaborate PCS/V2/SemanticV3Audit.lean and fail unless every v3 theorem depends only on
# propext / Classical.choice / Quot.sound (no sorryAx, no Lean.ofReduceBool, no project axiom).
# Usage (from the project root, after `lake build`): bash tools/check_semantic_v3_audit.sh
set -u
lake env lean PCS/V2/SemanticV3Audit.lean > /tmp/pcs_v3_audit.out 2>&1; rc=$?
python3 - "$rc" <<'PY'
import re, sys
rc = int(sys.argv[1])
out = open('/tmp/pcs_v3_audit.out', encoding='utf-8').read()
expected = sum(1 for l in open('PCS/V2/SemanticV3Audit.lean', encoding='utf-8') if l.startswith('#print axioms'))
deps = re.findall(r"'([^']+)' depends on axioms: \[([^\]]*)\]", out, re.S)
none = re.findall(r"'([^']+)' does not depend on any axioms", out)
allowed = {'propext', 'Classical.choice', 'Quot.sound'}
bad = sorted({(n, a.strip()) for n, axs in deps for a in axs.split(',') if a.strip() not in allowed})
total = len(deps) + len(none)
print(f"v3 axiom audit: {total}/{expected} theorems reported, lean exit {rc}")
if re.search(r'(^|\n)[^\n]*: error', out):
    print(out[:2000]); sys.exit(1)
if bad:
    print("DISALLOWED AXIOMS:", bad); sys.exit(1)
if rc != 0 or total != expected:
    sys.exit(1)
print("AUDIT PASS: only propext / Classical.choice / Quot.sound")
PY
