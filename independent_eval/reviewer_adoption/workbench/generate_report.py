"""Generate a standalone, accessibility-minded static HTML report.

Usage:
  python -m independent_eval.reviewer_adoption.workbench.generate_report \\
    --evidence PATH --out report.html
"""

from __future__ import annotations

import argparse
import html
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from .inspect_evidence import WORKBENCH_DISCLAIMER, inspect_evidence_dir


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
footer { color: var(--muted); border-top: 1px solid var(--line); margin-top: 2rem; }
@media (prefers-reduced-motion: reduce) { html { scroll-behavior: auto; } }
@media (max-width: 640px) {
  html { font-size: 100%; }
  table, thead, tbody, th, td, tr { display: block; }
  th { border-bottom: none; }
}
""".strip()


def render_html(inspection_dict: dict, *, generated_at: str) -> str:
    claims = inspection_dict.get("claims") or []
    assumptions = inspection_dict.get("assumptions") or []
    artifacts = inspection_dict.get("artifacts") or []
    outcomes = inspection_dict.get("outcomes") or []
    warnings = inspection_dict.get("warnings") or []
    authority = inspection_dict.get("reported_authority") or {}
    limitations = inspection_dict.get("limitations_text") or "(No LIMITATIONS.md found in evidence.)"

    claim_rows = []
    for c in claims:
        claim_rows.append(
            "<tr>"
            f"<td><code>{_esc(c.get('id'))}</code></td>"
            f"<td>{_esc(c.get('statement'))}</td>"
            f"<td><span class='badge reported' title='Reported by source evidence'>"
            f"{_esc(c.get('reported_status'))}</span>"
            f"<div class='meta'>source: {_esc(c.get('status_source') or 'n/a')}</div></td>"
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
        <li><a href="#claims">Claims (reported statuses)</a></li>
        <li><a href="#assumptions">Assumptions</a></li>
        <li><a href="#artifacts">Artifact identities</a></li>
        <li><a href="#outcomes">Reported outcomes</a></li>
        <li><a href="#authority">Reported authority fields</a></li>
        <li><a href="#limitations">Limitations</a></li>
        <li><a href="#sources">Source paths</a></li>
      </ol>
    </nav>
    {warning_html}
    <section id="claims" aria-labelledby="claims-h">
      <h2 id="claims-h">Claims (reported statuses)</h2>
      <p class="meta">Statuses are copied from evidence. This workbench does not decide ACCEPT/PASS.</p>
      <table>
        <caption class="meta">Claim inventory with source-reported status only</caption>
        <thead>
          <tr><th scope="col">ID</th><th scope="col">Statement</th><th scope="col">Reported status</th><th scope="col">Assumptions</th></tr>
        </thead>
        <tbody>
          {''.join(claim_rows) or '<tr><td colspan="4">No claims found.</td></tr>'}
        </tbody>
      </table>
    </section>
    <section id="assumptions" aria-labelledby="assumptions-h">
      <h2 id="assumptions-h">Assumptions</h2>
      <table>
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
  </main>
  <footer>
    <p>Offline static report · independent_eval/reviewer_adoption/workbench</p>
  </footer>
</body>
</html>
"""


def generate_report(evidence_dir: str | Path, out_path: str | Path) -> Path:
    inspection = inspect_evidence_dir(evidence_dir)
    payload = inspection.to_dict()
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    html_text = render_html(payload, generated_at=generated_at)
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html_text, encoding="utf-8")
    companion = out.with_suffix(".inspection.json")
    companion.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate an offline PCS reviewer workbench HTML report (inspect-only)."
    )
    parser.add_argument("--evidence", required=True, help="Path to evidence directory")
    parser.add_argument("--out", required=True, help="Output HTML path")
    args = parser.parse_args(argv)
    path = generate_report(args.evidence, args.out)
    print(f"wrote {path}")
    print(f"wrote {path.with_suffix('.inspection.json')}")
    print("workbench_issues_accept=false")
    return 0


if __name__ == "__main__":
    sys.exit(main())
