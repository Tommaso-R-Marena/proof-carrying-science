"""Shared helpers for the v1.1 DEVELOPMENT evaluation.

The documents used here are the ClaimCheck v1 development and held-out documents.  They were all
seen while v1.1 was designed, so for v1.1 they are development and calibration data only.  Nothing
computed from them is prospective validation of v1.1.
"""
from __future__ import annotations

import json
from pathlib import Path

from ...claimcheck_v1.benchmark.harness import Document
from ...claimcheck_v1.benchmark.run import load_split
from ...claimcheck_v1.pipeline import verify_many
from ...claimcheck_v1.spec import canonical, sha256_hex
from ..space import SourceContext

V1 = Path(__file__).resolve().parents[2] / "claimcheck_v1" / "benchmark"
SPLITS = {"dev": V1 / "results" / "dev", "heldout": V1 / "results" / "heldout"}


def documents(split: str) -> list[Document]:
    return load_split(split)


_OVERLAY = json.loads((Path(__file__).with_name("manifest_overlays.json")).read_text(encoding="utf-8"))["row_unit"]


def manifest_v11(doc: Document) -> dict:
    """The frozen v1 manifest plus the development-only ``row_unit`` overlay."""
    extra = _OVERLAY.get(doc.slug)
    return {**doc.manifest, "row_unit": extra} if extra else dict(doc.manifest)


def context(doc: Document) -> SourceContext:
    return SourceContext(doc.text, doc.data, manifest_v11(doc))


def oracle_receipts(doc: Document, proposals: list[dict], origin: str = "development adversary (oracle-predicted, no kernel)") -> list[dict]:
    """v1 receipts for proposals, with the kernel step REPLACED by the untrusted oracle prediction.

    Development analysis only.  The receipts are marked and are never written into an evidence
    bundle.  (The oracle and the kernel have never disagreed; anything that an adversary gets
    through the v1.1 policy is afterwards put to the real kernel.)
    """
    receipts = verify_many([(f"o{i:05d}", p, origin) for i, p in enumerate(proposals)], source_text=doc.text,
                           source_meta={"name": doc.key}, data=doc.data, manifest=doc.manifest, run_lean=False)
    for r in receipts:
        q1 = r.get("q1_mathematics") or {}
        variants = q1.get("variants") or []
        if r.get("reason") != "not_kernel_checked" or not variants:
            continue
        verdicts = [(v.get("predicted_outcome") or {}).get("verdict") for v in variants]
        if any(v is None for v in verdicts):
            continue
        r["oracle_predicted_only"] = True
        grounded = (r.get("q2_correspondence") or {}).get("status") == "GROUNDED"
        if all(v == "consistent" for v in verdicts):
            q1["status"] = "PROVED"
        elif all(v == "inconsistent" for v in verdicts):
            q1["status"] = "REFUTED"
        else:
            q1["conditional"] = {"note": "oracle-predicted conditional"}
            r["reason"] = "ambiguous_convention"
            continue
        r["result"] = q1["status"] if grounded else "UNKNOWN"
        r["reason"] = "checked" if grounded else "binding_not_grounded"
        r["receipt_sha256"] = sha256_hex(canonical({k: v for k, v in r.items() if k != "receipt_sha256"}))
    return receipts


def dump(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=1, ensure_ascii=False), encoding="utf-8")
