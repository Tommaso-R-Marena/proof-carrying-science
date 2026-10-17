"""Static HTML renderer for the Assurance Card (a11y basics included)."""
from __future__ import annotations

import html
import json
from typing import Any

LIMITATIONS_BANNER = (
    "LIMITATIONS: A computational PASS from pcs verify is not empirical or "
    "scientific adequacy. This Assurance Card never certifies science, clinical "
    "validity, regulatory acceptance, or external-lab completion."
)


def _esc(value: object) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def _css() -> str:
    return """
:root {
  --bg: #f3f6f4;
  --ink: #15201c;
  --muted: #3f4f48;
  --line: #b7c4bd;
  --accent: #0d5c4d;
  --warn-bg: #fff6e8;
  --warn-ink: #5a3a00;
  --auth-bg: #e8f1ee;
  --focus: #0b57d0;
  --panel: #fcfdfc;
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
    radial-gradient(circle at 8% 0%, #dcece6 0%, transparent 40%),
    linear-gradient(180deg, #f8fbf9 0%, var(--bg) 50%, #e7eee9 100%);
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
  max-width: 58rem;
  margin: 0 auto;
  padding: 1.25rem 1.25rem;
}
header { border-bottom: 1px solid var(--line); }
.brand {
  font-family: var(--serif);
  font-size: 1.8rem;
  margin: 0 0 0.35rem;
  letter-spacing: -0.02em;
}
.banner, .disclaimer, .warning {
  background: var(--warn-bg);
  color: var(--warn-ink);
  border-left: 4px solid #c47b16;
  padding: 0.85rem 1rem;
  margin: 1rem 0;
}
.banner { font-weight: 650; }
.authority {
  background: var(--auth-bg);
  border-left: 4px solid var(--accent);
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
  background: var(--panel);
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
th { background: #e4ece8; font-weight: 650; }
code, .mono { font-family: var(--mono); font-size: 0.9em; word-break: break-all; }
.meta { color: var(--muted); font-size: 0.95rem; }
details {
  background: var(--panel);
  border: 1px solid var(--line);
  padding: 0.65rem 0.85rem;
  margin: 0.65rem 0;
}
summary { cursor: pointer; font-weight: 650; }
.badge {
  display: inline-block;
  padding: 0.1rem 0.45rem;
  border: 1px solid var(--line);
  background: #eef3f0;
  font-size: 0.85rem;
}
.badge.strength { font-family: var(--mono); font-size: 0.8rem; }
.badge.strength-computationally_supported { background: #e5f0eb; border-color: #0b5f4b; }
.badge.strength-cryptographic_validity { background: #e8eef8; border-color: #3b5bdb; }
.badge.strength-scientific_adequacy_open { background: #fff4df; border-color: #c47b16; }
.badge.strength-rejected_or_failed { background: #fde8e8; border-color: #b42318; }
.badge.strength-unknown_or_ambiguous { background: #eef1f4; border-color: #6b7280; }
.strength-dl {
  display: grid;
  grid-template-columns: minmax(10rem, 16rem) 1fr;
  gap: 0.35rem 1rem;
  background: var(--panel);
  border: 1px solid var(--line);
  padding: 0.85rem 1rem;
  margin: 0.85rem 0 1.25rem;
}
.strength-dl dt { font-family: var(--mono); font-size: 0.85rem; margin: 0; }
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


def render_assurance_card_html(card: dict[str, Any]) -> str:
    """Render a complete static HTML Assurance Card document."""
    inspection = card.get("inspection") or {}
    authority = card.get("authority") or {}
    provenance = card.get("provenance") or {}
    summary = inspection.get("claim_strength_summary") or {}
    claims = inspection.get("claims") or []
    assumptions = inspection.get("assumptions") or []
    artifacts = inspection.get("artifacts") or []
    warnings = inspection.get("warnings") or []
    limitations = (
        inspection.get("limitations_text")
        or "(No LIMITATIONS.md found in evidence.)"
    )
    banner = card.get("limitations_banner") or LIMITATIONS_BANNER

    claim_rows = []
    for c in claims:
        strength = c.get("inspection_class") or "unknown_or_ambiguous"
        claim_rows.append(
            "<tr>"
            f"<td><code>{_esc(c.get('id'))}</code></td>"
            f"<td>{_esc(c.get('statement'))}</td>"
            f"<td><span class='badge'>{_esc(c.get('reported_status'))}</span>"
            f"<div class='meta'>source: {_esc(c.get('status_source') or 'n/a')}</div></td>"
            f"<td><span class='badge strength strength-{_esc(strength)}'>"
            f"{_esc(strength)}</span>"
            f"<div class='meta'>inspection only · not authority</div></td>"
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
            f"<td class='mono'>{_esc(art.get('sha256') or '—')}</td>"
            "</tr>"
        )

    strength_items = []
    for cls, count in summary.items():
        strength_items.append(
            f"<dt><span class='badge strength strength-{_esc(cls)}'>{_esc(cls)}</span></dt>"
            f"<dd>{int(count)}</dd>"
        )

    warning_html = "".join(f"<p class='warning' role='note'>{_esc(w)}</p>" for w in warnings)
    input_hashes = provenance.get("input_sha256") or {}
    hash_lis = "".join(
        f"<li><code>{_esc(p)}</code> · <span class='mono'>{_esc(h)}</span></li>"
        for p, h in input_hashes.items()
    ) or "<li>None</li>"

    lane_consistency = card.get("lane_consistency") or {}

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>PCS Offline Assurance Card</title>
  <style>{_css()}</style>
</head>
<body>
  <a class="skip-link" href="#main">Skip to main content</a>
  <header>
    <p class="meta">Independent evaluation · Workstream F · Offline Assurance Card</p>
    <h1 class="brand">PCS Assurance Card</h1>
    <p>Subject: <strong>{_esc(inspection.get('subject') or '(unspecified)')}</strong></p>
    <p class="meta">
      Generated at {_esc(provenance.get('generated_at_utc') or '')}
      · card_issues_accept: <strong>false</strong>
      · inspection_is_not_authority: <strong>true</strong>
    </p>
    <div class="banner" role="status" aria-live="polite" id="limitations-banner">
      {_esc(banner)}
    </div>
    <div class="disclaimer" role="note">
      {_esc(card.get('disclaimer') or LIMITATIONS_BANNER)}
    </div>
  </header>
  <main id="main">
    <nav class="toc" aria-label="Card sections">
      <h2>Contents</h2>
      <ol>
        <li><a href="#authority">Authority lane (pcs verify)</a></li>
        <li><a href="#inspection">Inspection lane (non-authority)</a></li>
        <li><a href="#claims">Claims</a></li>
        <li><a href="#assumptions">Assumptions</a></li>
        <li><a href="#artifacts">Artifacts</a></li>
        <li><a href="#provenance">Provenance</a></li>
        <li><a href="#limitations">Limitations text</a></li>
        <li><a href="#consistency">Lane consistency</a></li>
      </ol>
    </nav>
    {warning_html}

    <section id="authority" aria-labelledby="authority-h">
      <h2 id="authority-h">Authority lane (CLI)</h2>
      <div class="authority" role="region" aria-label="Authority lane summary">
        {_esc(authority.get('disclaimer') or '')}
      </div>
      <dl class="strength-dl" aria-label="Authority lane fields">
        <dt>cli_is_authority</dt><dd>{_esc(authority.get('cli_is_authority'))}</dd>
        <dt>ok</dt><dd>{_esc(authority.get('ok'))}</dd>
        <dt>returncode</dt><dd>{_esc(authority.get('returncode'))}</dd>
        <dt>duration_seconds</dt><dd>{_esc(authority.get('duration_seconds'))}</dd>
        <dt>attempted</dt><dd>{_esc(authority.get('attempted'))}</dd>
        <dt>skipped</dt><dd>{_esc(authority.get('skipped'))}</dd>
        <dt>argv</dt><dd class="mono">{_esc(json.dumps(authority.get('argv')))}</dd>
        <dt>certificate_path</dt>
        <dd class="mono">{_esc(authority.get('certificate_path'))}</dd>
      </dl>
      <details>
        <summary>CLI stdout tail</summary>
        <pre class="mono" tabindex="0">{_esc(authority.get('stdout_tail') or '(empty)')}</pre>
      </details>
      <details>
        <summary>CLI stderr tail</summary>
        <pre class="mono" tabindex="0">{_esc(authority.get('stderr_tail') or '(empty)')}</pre>
      </details>
    </section>

    <section id="inspection" aria-labelledby="inspection-h">
      <h2 id="inspection-h">Inspection lane (non-authority)</h2>
      <p class="meta">
        <span class="badge">card_issues_accept = false</span>
        <span class="badge">inspection_is_not_authority = true</span>
      </p>
      <div class="disclaimer" role="note">{_esc(inspection.get('disclaimer') or '')}</div>
      <h3>Claim strength summary</h3>
      <dl class="strength-dl" aria-label="Claim strength summary counts">
        {''.join(strength_items) or '<dt>none</dt><dd>0</dd>'}
      </dl>
    </section>

    <section id="claims" aria-labelledby="claims-h">
      <h2 id="claims-h">Claims</h2>
      <table>
        <caption>Reported claim statuses with inspection_class (non-authority)</caption>
        <thead>
          <tr>
            <th scope="col">Claim</th>
            <th scope="col">Statement</th>
            <th scope="col">Reported status</th>
            <th scope="col">Inspection class</th>
          </tr>
        </thead>
        <tbody>
          {''.join(claim_rows) or '<tr><td colspan="4">No claims found.</td></tr>'}
        </tbody>
      </table>
    </section>

    <section id="assumptions" aria-labelledby="assumptions-h">
      <h2 id="assumptions-h">Assumptions</h2>
      <table>
        <caption>Assumptions copied from certificate</caption>
        <thead>
          <tr>
            <th scope="col">ID</th>
            <th scope="col">Statement</th>
            <th scope="col">Rationale</th>
          </tr>
        </thead>
        <tbody>
          {''.join(assumption_rows) or '<tr><td colspan="3">No assumptions found.</td></tr>'}
        </tbody>
      </table>
    </section>

    <section id="artifacts" aria-labelledby="artifacts-h">
      <h2 id="artifacts-h">Artifacts</h2>
      <table>
        <caption>Artifact identities and sha256 digests</caption>
        <thead>
          <tr>
            <th scope="col">ID</th>
            <th scope="col">Path</th>
            <th scope="col">SHA-256</th>
          </tr>
        </thead>
        <tbody>
          {''.join(artifact_rows) or '<tr><td colspan="3">No artifacts found.</td></tr>'}
        </tbody>
      </table>
    </section>

    <section id="provenance" aria-labelledby="provenance-h">
      <h2 id="provenance-h">Provenance</h2>
      <dl class="strength-dl" aria-label="Provenance fields">
        <dt>generated_at_utc</dt><dd>{_esc(provenance.get('generated_at_utc'))}</dd>
        <dt>git_head</dt><dd class="mono">{_esc(provenance.get('git_head') or 'n/a')}</dd>
        <dt>python_version</dt><dd>{_esc(provenance.get('python_version'))}</dd>
        <dt>card_version</dt><dd>{_esc(provenance.get('card_version'))}</dd>
        <dt>tool_versions</dt>
        <dd class="mono">{_esc(json.dumps(provenance.get('tool_versions') or {}, sort_keys=True))}</dd>
      </dl>
      <h3>Input file hashes</h3>
      <ul>{hash_lis}</ul>
    </section>

    <section id="limitations" aria-labelledby="limitations-h">
      <h2 id="limitations-h">Limitations text</h2>
      <pre tabindex="0">{_esc(limitations)}</pre>
    </section>

    <section id="consistency" aria-labelledby="consistency-h">
      <h2 id="consistency-h">Lane consistency (observational)</h2>
      <p class="meta">
        Observational comparison of authority-lane ok vs inspection_class values.
        Inspection classes are never mutated by this comparison.
      </p>
      <dl class="strength-dl" aria-label="Lane consistency">
        <dt>overall</dt>
        <dd><span class="badge">{_esc(lane_consistency.get('overall') or 'inconclusive')}</span></dd>
      </dl>
      <ul>
        {''.join(f'<li>{_esc(r)}</li>' for r in (lane_consistency.get('reasons') or [])) or '<li>None</li>'}
      </ul>
    </section>
  </main>
  <footer>
    <p>
      PCS Assurance Card · offline · single-process · no network · verify only
      (no Mathlib / Lean rebuild). Non-claims: no clinical validity, no external
      lab completion, no security proof, no merge recommendation.
    </p>
  </footer>
</body>
</html>
"""
