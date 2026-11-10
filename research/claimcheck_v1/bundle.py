"""Write a self-contained, replayable evidence bundle and a readable HTML report."""
from __future__ import annotations

import html
import json
from pathlib import Path

from . import AUTHORITY, VERSION
from .lean import CHECKER_PATH, checker_sha256
from .spec import canonical, sha256_hex

BUNDLE_SCHEMA = "pcs-claimcheck-bundle-v1"


def write_bundle(out: Path, *, source_text: str, data: bytes, manifest: dict, receipts: list[dict],
                 source_name: str = "source.txt", data_name: str = "data.csv", extra: dict | None = None) -> dict:
    """Persist everything needed to replay the receipts without this package."""
    out.mkdir(parents=True, exist_ok=True)
    (out / "source.txt").write_text(source_text, encoding="utf-8", newline="")
    (out / "data.csv").write_bytes(data)
    (out / "manifest.json").write_bytes(canonical(manifest))
    (out / "ClaimCheck.lean").write_bytes(CHECKER_PATH.read_bytes())
    (out / "receipts.json").write_text(json.dumps(receipts, indent=1, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    (out / "report.html").write_text(render_report(receipts, source_name=source_name, data_name=data_name), encoding="utf-8")
    files = {}
    for path in sorted(p for p in out.rglob("*") if p.is_file() and p.name != "bundle.json"):
        files[path.relative_to(out).as_posix()] = {"sha256": sha256_hex(path.read_bytes()), "bytes": path.stat().st_size}
    index = {
        "schema": BUNDLE_SCHEMA, "version": VERSION, "authority": AUTHORITY,
        "checker_sha256": checker_sha256(), "toolchain": "leanprover/lean4:v4.28.0",
        "original_names": {"source": source_name, "data": data_name},
        "counts": {k: sum(1 for r in receipts if r["result"] == k) for k in ("PROVED", "REFUTED", "UNKNOWN")},
        "files": files,
        "replay": "python replay_independent.py <this directory>   # needs Python 3.11+ and Lean 4.28.0 only",
    }
    if extra:
        index["extra"] = extra
    (out / "bundle.json").write_text(json.dumps(index, indent=1, sort_keys=True), encoding="utf-8")
    return index


_BADGE = {"PROVED": "#1b6e3c", "REFUTED": "#a12626", "UNKNOWN": "#6b5b00"}


def _e(x) -> str:
    return html.escape(str(x), quote=True)


def render_report(receipts: list[dict], *, source_name: str, data_name: str) -> str:
    """Static, script-free HTML.  Every string from a paper, dataset or model is escaped."""
    parts = [
        "<!doctype html><html lang=en><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>",
        "<title>ClaimCheck report</title>",
        "<style>body{font:16px/1.5 system-ui,sans-serif;max-width:60rem;margin:2rem auto;padding:0 1rem;color:#1a1a1a}"
        "h1{font-size:1.5rem}h2{font-size:1.1rem;margin:0}article{border:1px solid #ccc;border-radius:8px;padding:1rem;margin:1rem 0}"
        ".b{display:inline-block;color:#fff;border-radius:4px;padding:.1rem .5rem;font-weight:700;font-size:.85rem}"
        "blockquote{margin:.5rem 0;padding:.25rem .75rem;border-left:4px solid #999;background:#f6f6f6}"
        "dt{font-weight:700;margin-top:.6rem}dd{margin:0}code{background:#f0f0f0;padding:0 .2rem}small{color:#555}"
        "ul{margin:.2rem 0 .2rem 1.2rem;padding:0}</style>",
        "<h1>ClaimCheck report</h1>",
        f"<p>Paper text: <code>{_e(source_name)}</code>. Data file: <code>{_e(data_name)}</code>. "
        "Research tool; no production PCS authority.</p>",
        "<p>Each statement gets three separate answers. <b>1 — the arithmetic</b>: decided by the Lean kernel on the exact "
        "bytes of the data file. <b>2 — the link to the paper</b>: which mechanical source checks passed. "
        "<b>3 — the science</b>: never assessed here.</p>",
    ]
    for r in receipts:
        res = r["result"]
        q1, q2, q3 = r.get("q1_mathematics", {}), r.get("q2_correspondence", {}), r.get("q3_interpretation", {})
        parts.append(f"<article><h2><span class=b style='background:{_BADGE[res]}'>{_e(res)}</span> {_e(r['claim_id'])}</h2>")
        if "quote" in q2:
            parts.append(f"<blockquote>{_e(q2['quote']['text'])}</blockquote>")
        if "claim" in r:
            parts.append(f"<p><b>Reading that was checked:</b> {_e(r['claim']['reading'])}</p>")
        parts.append(f"<p>{_e(r.get('message', ''))}</p><p><small>{_e(r.get('scope', ''))}</small></p><dl>")
        parts.append(f"<dt>1 — Is the arithmetic right? {_e(q1.get('status', 'UNKNOWN'))}</dt><dd>")
        for v in q1.get("variants", []):
            po = v["predicted_outcome"]
            lean = v.get("lean", {})
            if po.get("defined"):
                parts.append(
                    f"Statistic <code>{_e(v['stat'])}</code>: exact value ≈ {_e(format(po['approximate_in_reported_units'], '.10g'))} "
                    f"from {_e(po['rows_used'])} rows ({_e(po['rows_skipped_as_missing'])} skipped as missing) — "
                    f"{_e(v['status'])}; Lean kernel accepted: {_e(lean.get('kernel_accepted'))}"
                    + (f" in {_e(lean.get('seconds'))} s" if lean.get("kernel_accepted") else f" ({_e(lean.get('detail'))})")
                    + (f"; assumes {_e(v['assumption'])}" if v.get("assumption") else "") + ".<br>")
            else:
                parts.append(f"Statistic <code>{_e(v['stat'])}</code> is undefined here: {_e(po.get('explanation'))}<br>")
        if q1.get("assumptions"):
            parts.append("Assumptions:<ul>" + "".join(f"<li>{_e(a)}</li>" for a in q1["assumptions"]) + "</ul>")
        if q1.get("conditional"):
            c = q1["conditional"]
            parts.append(f"<b>Conditional:</b> proved if the {_e(c['proved_if'])}; refuted if the {_e(c['refuted_if'])}.")
        parts.append(f"</dd><dt>2 — Is it linked to the paper and the data? {_e(q2.get('status', 'NOT_CHECKED'))}</dt><dd>")
        for a in q2.get("checks", {}).get("binding_anchors", []):
            parts.append(f"“{_e(a['binds'])}” — " + (f"named in the sentence as “{_e(a['anchored_by'])}”" if a["anchored_by"] else "<b>not named in the sentence</b>") + "<br>")
        for f in q2.get("failures", []):
            parts.append(f"<b>Failed:</b> {_e(f)}<br>")
        parts.append("Whether the sentence really means this reading: <b>UNREVIEWED</b> (a person must confirm).")
        parts.append(f"</dd><dt>3 — Does it support the scientific interpretation? {_e(q3.get('status'))}</dt><dd><ul>")
        parts.extend(f"<li>{_e(o)}</li>" for o in q3.get("open_obligations", []))
        terms = q3.get("interpretive_wording_in_sentence") or []
        if terms:
            parts.append(f"<li>The sentence uses interpretive wording ({_e(', '.join(terms))}); none of that was checked.</li>")
        parts.append(f"</ul></dd></dl><small>proposed by: {_e(r.get('proposal_origin'))} · receipt {_e(r.get('receipt_sha256', '')[:16])}</small></article>")
    parts.append("</html>")
    return "\n".join(parts)
