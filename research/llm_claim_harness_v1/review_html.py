"""Static, offline review UI for experimental source-linked evidence receipts.

This is a display artifact, not a verification or authorization boundary.
Every externally supplied string is HTML-escaped. No JavaScript/network resources.
"""
from __future__ import annotations

from html import escape
import os
from pathlib import Path

from .core import Source, sha


def render_evidence_review(source: Source, receipt: dict) -> str:
    if receipt.get("schema_version") != "llm-evidence-bridge-v4-research":
        raise ValueError("review UI requires an evidence-v4 receipt")
    if receipt.get("source_sha256") != source.digest:
        raise ValueError("source digest does not match review receipt")
    rows = []
    for claim in receipt.get("claims", []):
        span = claim.get("source_span", {})
        start, end = span.get("start"), span.get("end")
        if type(start) is not int or type(end) is not int or not (0 <= start < end <= len(source.text)):
            raise ValueError("invalid source span in review receipt")
        quote = source.text[start:end]
        if quote != claim.get("source_quote") or sha(quote.encode("utf-8")) != claim.get("source_quote_sha256"):
            raise ValueError("review receipt quote not bound to source")
        deps = []
        for dep in claim.get("declaration_anchors", []):
            s = dep["source_span"]["start"]
            e = dep["source_span"]["end"]
            if type(s) is not int or type(e) is not int or not (0 <= s < e <= start):
                raise ValueError("invalid declaration source span")
            text = source.text[s:e]
            if sha(text.encode("utf-8")) != dep.get("source_quote_sha256"):
                raise ValueError("declaration quote does not match source")
            deps.append(f'<li><code>{escape(dep["name"])}</code> at [{s}, {e}): <code>{escape(text)}</code></li>')
        formal = escape(str(claim.get("formal_status", "NOT_CHECKED")))
        kernel = "yes" if claim.get("kernel_checked") is True else "no"
        rows.append(
            '<article class="claim">'
            f'<h2>{escape(str(claim.get("id", "unnamed")))}</h2>'
            f'<p class="small">Exact source span [{start}, {end})</p>'
            f'<pre>{escape(quote)}</pre>'
            '<h3>Conservative syntactic normalization</h3>'
            f'<pre>{escape(str(claim.get("normalized_assertion", "")))}</pre>'
            f'<p><strong>Formal check:</strong> {formal}; kernel_checked={kernel}</p>'
            '<p><strong>Source meaning:</strong> UNREVIEWED; <strong>Scientific evidence:</strong> NOT ASSESSED</p>'
            '<h3>Original input declarations</h3>'
            f'<ul>{"".join(deps) if deps else "<li>None</li>"}</ul>'
            '</article>'
        )
    content = "".join(rows) if rows else '<p>No grounded equations selected. This does not mean the source contains no claims.</p>'
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<title>PCS Evidence Review — experimental</title>'
        '<style>body{font:16px/1.55 system-ui,sans-serif;max-width:880px;margin:2rem auto;padding:0 1rem;color:#17212e}'
        '.warn{background:#fff2da;border-left:5px solid #b86d08;padding:1rem;border-radius:4px}'
        '.claim{border:1px solid #cad2dd;padding:1.25rem;margin:1rem 0;border-radius:9px}'
        '.small{color:#596679;font-size:.88rem}pre{overflow-wrap:anywhere;white-space:pre-wrap;background:#f4f7fa;padding:.85rem}'
        'code{overflow-wrap:anywhere}h1,h2{line-height:1.2}</style></head><body>'
        '<h1>PCS: source-grounded equation review</h1>'
        '<p class="warn"><strong>Research-only. Not a scientific certification.</strong> '
        'A formal proof checks the normalized arithmetic proposition only. '
        'Prose context, measurements, uncertainty, source authenticity, and empirical validity remain unverified. '
        'A model agreeing with another model does not close these gaps.</p>'
        f'<p class="small">Source SHA-256: <code>{escape(source.digest)}</code></p>'
        f'{content}'
        '<h2>Review checklist</h2><p>Confirm that the selected equation was asserted (not quoted, denied, '
        'hypothetical, conditional, or merely defined), that each input is a supported measurement '
        'with appropriate uncertainty, and that every assumption and empirical inference is justified. '
        'This HTML file records no review decision.</p>'
        '</body></html>'
    )


def write_evidence_review(path: Path, source: Source, receipt: dict) -> None:
    """Explicitly requested private file; refuse output and temp symlink targets."""
    path = Path(path)
    if path.is_symlink():
        raise ValueError("review target must not be a symlink")
    text = render_evidence_review(source, receipt)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    if temp.is_symlink():
        raise ValueError("review temporary target must not be a symlink")
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(temp, path)
