"""Add v1.1 outward verdicts to the website's recorded examples, and publish the kernel runner.

    python -m research.claimcheck_v1_1.export_site_v11 --site ../proof-carrying-science-site/public

Reads the examples that ``claimcheck_v1/tools/export_site.py`` wrote (kernel-checked v1 receipts
whose proof file the page rebuilds byte for byte) and adds, per receipt, the v1.1 decision computed
from those receipts alone: supporting numbers count only if they are kernel-checked receipts of the
same example.  No Lean run, no network.  The receipts themselves are not modified.
"""
from __future__ import annotations

import argparse
import json
import shutil
from collections import Counter
from pathlib import Path

from ..claimcheck_v1.spec import sha256_hex
from . import POLICY_ID
from .dev.common import context, documents, manifest_v11
from .policy import assess_document, policy_parameters

RUNNER = Path(__file__).with_name("claimcheck_kernel_runner.py")
DEV_NOTE = ("The v1.1 reading rules were designed on these same six articles, so the following is development evidence, not a test. "
            "From the same kernel results, with readings proposed by two language models: misleading refutations fell from 131 and 2 to 0 and 0; "
            "correct confirmations fell from 40 and 24 to 26 and 17; detected discrepancies fell from 13 and 11 to 3 and 2. "
            "An adversary allowed to pick any eligible reading after seeing the data obtained 12 confirmations of numbers not labelled true "
            "(145 under v1) and no accusation of a true number. A prospective evaluation on new papers has been specified and not yet run.")


def export(site: Path) -> dict:
    docs = {d.slug: d for d in documents("heldout") if d.variant == "original"}
    catalog_path = site / "claim-check" / "examples.json"
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    totals: Counter = Counter()
    for meta in catalog["examples"]:
        path = site / "claim-check" / "examples" / f"{meta['id']}.json"
        ex = json.loads(path.read_text(encoding="utf-8"))
        doc = docs[ex["id"]]
        decisions = assess_document(context(doc), ex["receipts"])
        for r, d in zip(ex["receipts"], decisions):
            assert d["verdict"] != "CONFIRMATION" or r["result"] == "PROVED"
            assert d["verdict"] != "DISCREPANCY_FOR_REVIEW" or r["result"] == "REFUTED"
        ex["v1_1"] = {
            "policy": policy_parameters(),
            "manifest_additions": {"row_unit": manifest_v11(doc).get("row_unit"),
                                   "note": "What one row represents, added for v1.1 after reading the deposit; the v1 manifest is unchanged."},
            "decisions": [{"claim_id": r["claim_id"], "verdict": d["verdict"], "mathematical_status": d["mathematical_status"], "reasons": d["reasons"],
                           "findings": [{"rule": f["rule"], "passed": f["passed"], "detail": f["detail"]} for f in d["findings"]],
                           "supported_by": [c["printed"] for c in d["corroborated_by"]]} for r, d in zip(ex["receipts"], decisions)],
        }
        counts = Counter(d["verdict"] for d in decisions)
        meta["v1_1_counts"] = dict(sorted(counts.items()))
        totals.update(counts)
        path.write_text(json.dumps(ex, ensure_ascii=False), encoding="utf-8")
    shutil.copy(RUNNER, site / "claim-check" / "claimcheck_kernel_runner.py")
    catalog["v1_1"] = {"policy_id": POLICY_ID, "kernel_runner": {"path": "claim-check/claimcheck_kernel_runner.py", "sha256": sha256_hex(RUNNER.read_bytes())},
                       "kernel_run_schema": "pcs-claimcheck-kernel-run-v1", "recorded_example_verdicts": dict(sorted(totals.items())),
                       "development_note": DEV_NOTE, "prospective_evaluation": "specified, not approved, not run"}
    catalog_path.write_text(json.dumps(catalog, indent=1, ensure_ascii=False), encoding="utf-8")
    return {"examples": {m["id"]: m["v1_1_counts"] for m in catalog["examples"]}, "totals": dict(totals), "runner_sha256": catalog["v1_1"]["kernel_runner"]["sha256"]}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--site", required=True)
    args = ap.parse_args(argv)
    print(json.dumps(export(Path(args.site)), indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
