"""Generate a standalone, accessibility-minded static HTML and/or JSON report.

Usage:
  python -m independent_eval.reviewer_adoption.workbench.generate_report \\
    --evidence PATH --out report.html --format both
"""

from __future__ import annotations

import argparse
import html
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from .cli_crosscheck import CROSSCHECK_DISCLAIMER, crosscheck_evidence_dir
from .inspect_evidence import INSPECTION_CLASSES, WORKBENCH_DISCLAIMER, inspect_evidence_dir

VALID_FORMATS = ("html", "json", "both")


def _esc(value: object) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def _css() -> str:
    return """
:root {
  --bg: #f7f4ef;
  --ink: #1a1a1a;
  --muted: #4a4a4a;
  --line: #c9c2b6;
  --accent: #0b5f4b;
  --warn-bg: #fff4df;
  --warn-ink: #5c3b00;
  --focus: #0b57d0;
  --card: #fffdf8;
  --mono: "IBM Plex Mono", "Consolas", "Menlo", monospace;
  --sans: "Source Sans 3", "Segoe UI", "Helvetica Neue", sans-serif;
  --serif: "Source Serif 4", "Georgia", serif;
}
* { box-sizing: border-box; }
html { font-size: 112.5%; scroll-behavior: smooth; }
body {
  margin: 0;
  color: var(--ink);
  background:
    radial-gradient(circle at 12% 0%, #e8f2ee 0%, transparent 42%),
    linear-gradient(180deg, #fbf8f2 0%, var(--bg) 48%, #efe9df 100%);
  font-family: var(--sans);
  line-height: 1.55;
}
a { color: var(--accent); }
a:focus-visible, button:focus-visible, summary:focus-visible {
  outline: 3px solid var(--focus);
  outline-offset: 2px;
}
.skip-link {
  position: absolute;
  left: -999px;
  top: 0;
  background: #000;
  color: #fff;
  padding: 0.5rem 1rem;
  z-index: 10;
}
.skip-link:focus { left: 0.5rem; top: 0.5rem; }
header, main, footer {
  max-width: 56rem;
  margin: 0 auto;
  padding: 1.25rem 1.25rem;
}
header { border-bottom: 1px solid var(--line); }
.brand {
  font-family: var(--serif);
  font-size: 1.75rem;
  margin: 0 0 0.35rem;
  letter-spacing: -0.02em;
}
.disclaimer, .warning {
  background: var(--warn-bg);
  color: var(--warn-ink);
  border-left: 4px solid #c47b16;
  padding: 0.85rem 1rem;
  margin: 1rem 0;
}
h2 {
  font-family: var(--serif);
  font-size: 1.35rem;
  margin-top: 2rem;
  border-bottom: 1px solid var(--line);
  padding-bottom: 0.25rem;
}
table {
  width: 100%;
  border-collapse: collapse;
  background: var(--card);
}
caption {
  caption-side: top;
  text-align: left;
  padding: 0.35rem 0 0.55rem;
  color: var(--muted);
  font-size: 0.95rem;
}
th, td {
  text-align: left;
  vertical-align: top;
  padding: 0.55rem 0.65rem;
  border: 1px solid var(--line);
}
th { background: #efe8db; font-weight: 650; }
code, .mono { font-family: var(--mono); font-size: 0.9em; word-break: break-all; }
.meta { color: var(--muted); font-size: 0.95rem; }
details {
  background: var(--card);
  border: 1px solid var(--line);
  padding: 0.65rem 0.85rem;
  margin: 0.65rem 0;
}
summary { cursor: pointer; font-weight: 650; }
.badge {
  display: inline-block;
  padding: 0.1rem 0.45rem;
  border: 1px solid var(--line);
  background: #f0ebe2;
  font-size: 0.85rem;
}
.badge.reported { border-color: #7a8f86; background: #e5f0eb; }
.badge.strength {
  border-color: #6b7280;
  background: #eef1f4;
  font-family: var(--mono);
  font-size: 0.8rem;
}
.badge.strength-computationally_supported { background: #e5f0eb; border-color: #0b5f4b; }
.badge.strength-cryptographic_validity { background: #e8eef8; border-color: #3b5bdb; }
.badge.strength-scientific_adequacy_open,
.badge.strength-empirically_unsupported { background: #fff4df; border-color: #c47b16; }
.badge.strength-rejected_or_failed { background: #fde8e8; border-color: #b42318; }
.badge.strength-unknown_or_ambiguous { background: #f0ebe2; border-color: #6b7280; }
.strength-dl {
  display: grid;
  grid-template-columns: minmax(10rem, 14rem) 1fr;
  gap: 0.35rem 1rem;
  background: var(--card);
  border: 1px solid var(--line);
  padding: 0.85rem 1rem;
  margin: 0.85rem 0 1.25rem;
}
.strength-dl dt {
  font-family: var(--mono);
  font-size: 0.85rem;
  margin: 0;
}
.strength-dl dd { margin: 0; font-variant-numeric: tabular-nums; }
footer { color: var(--muted); border-top: 1px solid var(--line); margin-top: 2rem; }
@media (prefers-reduced-motion: reduce) { html { scroll-behavior: auto; } }
@media (max-width: 640px) {
  html { font-size: 100%; }
  table, thead, tbody, th, td, tr { display: block; }
  th { border-bottom: none; }
  .strength-dl { grid-template-columns: 1fr; }
}
""".strip()


def _strength_summary_dl(summary: dict) -> str:
    items = []
    for cls in INSPECTION_CLASSES:
        count = int(summary.get(cls, 0))
        items.append(
            f"<dt><span class='badge strength strength-{_esc(cls)}'>{_esc(cls)}</span></dt>"
            f"<dd>{count}</dd>"
        )
    return (
        "<dl class='strength-dl' aria-label='Claim strength summary counts'>"
        + "".join(items)
        + "</dl>"
    )


def _cli_crosscheck_section(crosscheck: dict | None) -> str:
    """Render observational CLI cross-check section (or empty string)."""
    if not crosscheck:
        return ""
    claim_rows = []
    for c in crosscheck.get("claim_comparisons") or []:
        claim_rows.append(
            "<tr>"
            f"<td><code>{_esc(c.get('claim_id'))}</code></td>"
            f"<td><span class='badge strength strength-{_esc(c.get('inspection_class'))}'>"
            f"{_esc(c.get('inspection_class'))}</span></td>"
            f"<td>{_esc(c.get('reported_status'))}</td>"
            f"<td><span class='badge'>{_esc(c.get('consistency'))}</span></td>"
            f"<td>{_esc('; '.join(c.get('reasons') or []) or '—')}</td>"
            "</tr>"
        )
    reasons = crosscheck.get("overall_reasons") or []
    reason_lis = "".join(f"<li>{_esc(r)}</li>" for r in reasons) or "<li>None</li>"
    return f"""
    <section id="cli-crosscheck" aria-labelledby="cli-crosscheck-h">
      <h2 id="cli-crosscheck-h">CLI cross-check (observational)</h2>
      <div class="disclaimer" role="note">
        {_esc(crosscheck.get('disclaimer') or CROSSCHECK_DISCLAIMER)}
      </div>
      <p class="meta">
        <span class="badge">observational</span>
        <span class="badge">cli_is_authority = true</span>
        <span class="badge">workbench_issues_accept = false</span>
        · inspection_class is never mutated by this section.
      </p>
      <dl class="strength-dl" aria-label="CLI cross-check summary">
        <dt>overall_classification</dt>
        <dd><span class="badge">{_esc(crosscheck.get('overall_classification'))}</span></dd>
        <dt>cli_verify_attempted</dt>
        <dd>{_esc(crosscheck.get('cli_verify_attempted'))}</dd>
        <dt>cli_verify_ok</dt>
        <dd>{_esc(crosscheck.get('cli_verify_ok'))}</dd>
        <dt>cli_returncode</dt>
        <dd>{_esc(crosscheck.get('cli_returncode'))}</dd>
        <dt>argv</dt>
        <dd class="mono">{_esc(json.dumps(crosscheck.get('argv')))}</dd>
        <dt>certificate_path</dt>
        <dd class="mono">{_esc(crosscheck.get('certificate_path'))}</dd>
      </dl>
      <h3>Overall reasons</h3>
      <ul>{reason_lis}</ul>
      <table>
        <caption>Per-claim consistency of inspection_class vs CLI outcome (observational)</caption>
        <thead>
          <tr>
            <th scope="col">Claim</th>
            <th scope="col">Inspection class</th>
            <th scope="col">Reported status</th>
            <th scope="col">Consistency</th>
            <th scope="col">Reasons</th>
          </tr>
        </thead>
        <tbody>
          {''.join(claim_rows) or '<tr><td colspan="5">No claim comparisons.</td></tr>'}
        </tbody>
      </table>
      <details>
        <summary>CLI stdout tail</summary>
        <pre class="mono" tabindex="0">{_esc(crosscheck.get('stdout_tail') or '(empty)')}</pre>
      </details>
      <details>
        <summary>CLI stderr tail</summary>
        <pre class="mono" tabindex="0">{_esc(crosscheck.get('stderr_tail') or '(empty)')}</pre>
      </details>
    </section>
    """


def render_html(inspection_dict: dict, *, generated_at: str) -> str:
    claims = inspection_dict.get("claims") or []
    assumptions = inspection_dict.get("assumptions") or []
    artifacts = inspection_dict.get("artifacts") or []
    outcomes = inspection_dict.get("outcomes") or []
    warnings = inspection_dict.get("warnings") or []
    authority = inspection_dict.get("reported_authority") or {}
    limitations = inspection_dict.get("limitations_text") or "(No LIMITATIONS.md found in evidence.)"
    strength_summary = inspection_dict.get("claim_strength_summary") or {}
    cli_crosscheck = inspection_dict.get("cli_crosscheck")

    claim_rows = []
    for c in claims:
        strength = c.get("inspection_class") or "unknown_or_ambiguous"
        claim_rows.append(
            "<tr>"
            f"<td><code>{_esc(c.get('id'))}</code></td>"
            f"<td>{_esc(c.get('statement'))}</td>"
            f"<td><span class='badge reported' title='Reported by source evidence'>"
            f"{_esc(c.get('reported_status'))}</span>"
            f"<div class='meta'>source: {_esc(c.get('status_source') or 'n/a')}</div></td>"
            f"<td><span class='badge strength strength-{_esc(strength)}' "
            f"title='Workbench inspection_class only; not authority'>"
            f"{_esc(strength)}</span>"
            f"<div class='meta'>inspection only</div></td>"
            f"<td>{_esc(', '.join(c.get('assumptions') or []) or '—')}</td>"
            "</tr>"
        )

    assumption_rows = []
    for a in assumptions:
        assumption_rows.append(
            "<tr>"
            f"<td><code>{_esc(a.get('id'))}</code></td>"
            f"<td>{_esc(a.get('statement'))}</td>"
            f"<td>{_esc(a.get('rationale') or '—')}</td>"
            "</tr>"
        )

    artifact_rows = []
    for art in artifacts:
        artifact_rows.append(
            "<tr>"
            f"<td><code>{_esc(art.get('id'))}</code></td>"
            f"<td>{_esc(art.get('path') or '—')}</td>"
            f"<td>{_esc(art.get('role') or '—')}</td>"
            f"<td class='mono'>{_esc(art.get('sha256') or '—')}</td>"
            "</tr>"
        )

    outcome_items = [
        f"<li><code>{_esc(json.dumps(o, sort_keys=True))}</code></li>" for o in outcomes
    ]
    warning_html = "".join(f"<p class='warning' role='note'>{_esc(w)}</p>" for w in warnings)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>PCS Offline Reviewer Workbench Report</title>
  <style>{_css()}</style>
</head>
<body>
  <a class="skip-link" href="#main">Skip to main content</a>
  <header>
    <p class="meta">Independent evaluation · Workstream D · Task 15</p>
    <h1 class="brand">PCS Offline Reviewer Workbench</h1>
    <p>Subject: <strong>{_esc(inspection_dict.get('subject') or '(unspecified)')}</strong></p>
    <p class="meta">Generated at {_esc(generated_at)} · issues ACCEPT: <strong>no</strong></p>
    <div class="disclaimer" role="status" aria-live="polite">
      {_esc(inspection_dict.get('disclaimer') or WORKBENCH_DISCLAIMER)}
    </div>
  </header>
  <main id="main">
    <nav class="toc" aria-label="Report sections">
      <h2>Contents</h2>
      <ol>
        <li><a href="#strength">Claim strength summary</a></li>
        <li><a href="#claims">Claims (reported statuses)</a></li>
        <li><a href="#assumptions">Assumptions</a></li>
        <li><a href="#artifacts">Artifact identities</a></li>
        <li><a href="#outcomes">Reported outcomes</a></li>
        <li><a href="#authority">Reported authority fields</a></li>
        <li><a href="#limitations">Limitations</a></li>
        <li><a href="#sources">Source paths</a></li>
        {"<li><a href='#cli-crosscheck'>CLI cross-check (observational)</a></li>" if cli_crosscheck else ""}
      </ol>
    </nav>
    {warning_html}
    <section id="strength" aria-labelledby="strength-h">
      <h2 id="strength-h">Claim strength summary</h2>
      <p class="meta">
        Counts of workbench <code>inspection_class</code> labels derived from
        <code>reported_*</code> fields. Not PCS authority.
      </p>
      {_strength_summary_dl(strength_summary)}
    </section>
    <section id="claims" aria-labelledby="claims-h">
      <h2 id="claims-h">Claims (reported statuses)</h2>
      <p class="meta">Statuses are copied from evidence. This workbench does not decide ACCEPT/PASS.</p>
      <table>
        <caption>Claim inventory with source-reported status and workbench inspection_class</caption>
        <thead>
          <tr>
            <th scope="col">ID</th>
            <th scope="col">Statement</th>
            <th scope="col">Reported status</th>
            <th scope="col">Inspection class</th>
            <th scope="col">Assumptions</th>
          </tr>
        </thead>
        <tbody>
          {''.join(claim_rows) or '<tr><td colspan="5">No claims found.</td></tr>'}
        </tbody>
      </table>
    </section>
    <section id="assumptions" aria-labelledby="assumptions-h">
      <h2 id="assumptions-h">Assumptions</h2>
      <table>
        <caption>Assumptions declared in the certificate or manifest</caption>
        <thead>
          <tr><th scope="col">ID</th><th scope="col">Statement</th><th scope="col">Rationale</th></tr>
        </thead>
        <tbody>
          {''.join(assumption_rows) or '<tr><td colspan="3">No assumptions found.</td></tr>'}
        </tbody>
      </table>
    </section>
    <section id="artifacts" aria-labelledby="artifacts-h">
      <h2 id="artifacts-h">Artifact identities</h2>
      <table>
        <caption>Artifact paths and digests as reported or computed offline</caption>
        <thead>
          <tr><th scope="col">ID</th><th scope="col">Path</th><th scope="col">Role</th><th scope="col">SHA-256</th></tr>
        </thead>
        <tbody>
          {''.join(artifact_rows) or '<tr><td colspan="4">No artifacts found.</td></tr>'}
        </tbody>
      </table>
    </section>
    <section id="outcomes" aria-labelledby="outcomes-h">
      <h2 id="outcomes-h">Reported outcomes</h2>
      <ul>
        {''.join(outcome_items) or '<li>No structured outcomes found.</li>'}
      </ul>
    </section>
    <section id="authority" aria-labelledby="authority-h">
      <h2 id="authority-h">Reported authority fields</h2>
      <p class="meta">Copied from receipts when present. Workbench never sets ACCEPT.</p>
      <pre class="mono" tabindex="0">{_esc(json.dumps(authority, indent=2, sort_keys=True))}</pre>
      <p><span class="badge">workbench_issues_accept = false</span></p>
    </section>
    <section id="limitations" aria-labelledby="limitations-h">
      <h2 id="limitations-h">Limitations</h2>
      <details open>
        <summary>LIMITATIONS.md content</summary>
        <pre tabindex="0">{_esc(limitations)}</pre>
      </details>
    </section>
    <section id="sources" aria-labelledby="sources-h">
      <h2 id="sources-h">Source paths</h2>
      <ul>
        {''.join(f'<li class="mono">{_esc(p)}</li>' for p in (inspection_dict.get('source_paths') or [])) or '<li>None</li>'}
      </ul>
    </section>
    {_cli_crosscheck_section(cli_crosscheck)}
  </main>
  <footer>
    <p>Offline static report · independent_eval/reviewer_adoption/workbench</p>
  </footer>
</body>
</html>
"""


def _resolve_out_paths(out_path: Path, fmt: str) -> tuple[Path | None, Path | None]:
    """Return (html_path, json_path) for the requested format."""
    if fmt == "html":
        html_path = out_path if out_path.suffix.lower() in (".html", ".htm") else out_path.with_suffix(".html")
        return html_path, None
    if fmt == "json":
        if out_path.suffix.lower() == ".json":
            return None, out_path
        # Prefer report.inspection.json when given an .html stem
        if out_path.suffix.lower() in (".html", ".htm"):
            return None, out_path.with_suffix(".inspection.json")
        return None, out_path.with_suffix(".json")
    # both
    if out_path.suffix.lower() in (".html", ".htm"):
        return out_path, out_path.with_suffix(".inspection.json")
    if out_path.suffix.lower() == ".json":
        return out_path.with_suffix(".html"), out_path
    return out_path.with_suffix(".html"), out_path.with_suffix(".inspection.json")


def generate_report(
    evidence_dir: str | Path,
    out_path: str | Path,
    *,
    fmt: str = "both",
    cli_crosscheck: bool = False,
) -> dict[str, Path]:
    if fmt not in VALID_FORMATS:
        raise ValueError(f"unsupported format {fmt!r}; expected one of {VALID_FORMATS}")
    inspection = inspect_evidence_dir(evidence_dir)
    payload = inspection.to_dict()
    if cli_crosscheck:
        # Observational only; does not mutate inspection_class / ACCEPT.
        payload["cli_crosscheck"] = crosscheck_evidence_dir(
            evidence_dir, inspection=inspection
        ).to_dict()
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    html_path, json_path = _resolve_out_paths(Path(out_path), fmt)
    written: dict[str, Path] = {}
    if html_path is not None:
        html_path.parent.mkdir(parents=True, exist_ok=True)
        html_path.write_text(render_html(payload, generated_at=generated_at), encoding="utf-8")
        written["html"] = html_path
    if json_path is not None:
        export = {
            **payload,
            "generated_at": generated_at,
            "report_format": "inspection_json_v1",
        }
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(export, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        written["json"] = json_path
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate an offline PCS reviewer workbench report (inspect-only)."
    )
    parser.add_argument("--evidence", required=True, help="Path to evidence directory")
    parser.add_argument(
        "--out",
        required=True,
        help="Output path (.html and/or .json/.inspection.json depending on --format)",
    )
    parser.add_argument(
        "--format",
        choices=VALID_FORMATS,
        default="both",
        dest="fmt",
        help="Emit html, json, or both (default: both)",
    )
    parser.add_argument(
        "--cli-crosscheck",
        action="store_true",
        help=(
            "Embed observational pcs-verify cross-check JSON/HTML section "
            "(cli_is_authority=true; workbench remains inspect-only)."
        ),
    )
    args = parser.parse_args(argv)
    written = generate_report(
        args.evidence, args.out, fmt=args.fmt, cli_crosscheck=args.cli_crosscheck
    )
    for kind, path in written.items():
        print(f"wrote {kind}: {path}")
    print("workbench_issues_accept=false")
    return 0


if __name__ == "__main__":
    sys.exit(main())
