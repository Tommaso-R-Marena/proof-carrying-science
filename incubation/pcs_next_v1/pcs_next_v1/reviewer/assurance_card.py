"""Human-readable Assurance Card export (JSON + static HTML)."""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

from ..core.canonical import canonicalize


def build_card(report: dict[str, Any], *, claims: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {
        "format": "pcs-next-assurance-card-v1",
        "project_id": report.get("project_id"),
        "claims": claims or [],
        "technical_verification": report.get("statuses", {}).get("computational_replay"),
        "formal": report.get("statuses", {}).get("formal"),
        "independent": report.get("statuses", {}).get("independent"),
        "scientific_validation": report.get("external_lab_validation"),
        "policy_hash": report.get("policy_hash"),
        "lock_hash": report.get("lock_hash"),
        "bundle_hash": report.get("bundle_hash"),
        "unresolved_questions": report.get("unresolved_questions", []),
        "disclaimer": (
            "Technical verification statuses must not be read as clinical, biological, "
            "or external-lab scientific approval."
        ),
    }


def render_html(card: dict[str, Any]) -> str:
    def block(title: str, body: Any, *, tone: str = "neutral") -> str:
        return (
            f'<section class="block tone-{html.escape(tone)}">'
            f"<h2>{html.escape(title)}</h2>"
            f"<pre>{html.escape(json.dumps(body, indent=2, sort_keys=True))}</pre>"
            f"</section>"
        )

    sci = card.get("scientific_validation") or {}
    sci_tone = "open" if (sci.get("status") == "OPEN") else "neutral"
    tech = card.get("technical_verification") or {}
    tech_tone = "tech" if tech.get("status") in {"COMPUTATIONALLY_TESTED", "INDEPENDENTLY_REPRODUCED"} else "neutral"
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>PCS Next Assurance Card — {html.escape(str(card.get('project_id')))}</title>
<style>
:root {{
  --bg0:#0f1c17; --bg1:#1a2e24; --ink:#e8f0ea; --muted:#9db5a8;
  --tech:#3d7a5c; --warn:#a67c2a; --open:#3a5f8a; --danger:#8a3a3a;
  --serif:"Iowan Old Style","Palatino Linotype",Palatino,serif;
  --sans:"Avenir Next","Segoe UI",sans-serif;
}}
body{{margin:0;font-family:var(--sans);color:var(--ink);
background:radial-gradient(1200px 600px at 10% -10%,#243d32,transparent),
linear-gradient(160deg,var(--bg0),var(--bg1));min-height:100vh;}}
main{{max-width:920px;margin:0 auto;padding:2.5rem 1.25rem 4rem;}}
h1{{font-family:var(--serif);font-weight:600;font-size:clamp(1.8rem,4vw,2.6rem);margin:0 0 .5rem;}}
.lead{{color:var(--muted);max-width:40rem;line-height:1.5;}}
.disclaimer{{border-left:3px solid var(--warn);padding:.75rem 1rem;margin:1.5rem 0;color:var(--muted);}}
.block{{margin:1.25rem 0;padding:1rem 1.1rem;background:rgba(255,255,255,.03);
border:1px solid rgba(255,255,255,.08);}}
.block h2{{font-size:.95rem;letter-spacing:.04em;text-transform:uppercase;margin:0 0 .75rem;color:var(--muted);}}
.tone-tech{{border-color:rgba(61,122,92,.55);}}
.tone-open{{border-color:rgba(58,95,138,.55);}}
pre{{white-space:pre-wrap;word-break:break-word;margin:0;font-size:.85rem;line-height:1.45;}}
.ids{{font-family:ui-monospace,monospace;font-size:.8rem;color:var(--muted);}}
</style>
</head>
<body>
<main>
  <h1>Proof-Carrying Science</h1>
  <p class="lead">Assurance Card for project <strong>{html.escape(str(card.get('project_id')))}</strong>.
  Technical verification and scientific validation are shown separately.</p>
  <p class="disclaimer">{html.escape(card.get('disclaimer',''))}</p>
  {block('Technical verification', card.get('technical_verification'), tone=tech_tone)}
  {block('Formal status', card.get('formal'))}
  {block('Independent reconstruction', card.get('independent'))}
  {block('Scientific validation (external)', card.get('scientific_validation'), tone=sci_tone)}
  {block('Unresolved questions', card.get('unresolved_questions'))}
  <p class="ids">policy={html.escape(str(card.get('policy_hash')))}<br/>
  lock={html.escape(str(card.get('lock_hash')))}<br/>
  bundle={html.escape(str(card.get('bundle_hash')))}</p>
</main>
</body>
</html>
"""


def export_card(report: dict[str, Any], out_dir: str | Path, *, claims: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    card = build_card(report, claims=claims)
    (out / "assurance_card.json").write_bytes(canonicalize(card) + b"\n")
    (out / "assurance_card.html").write_text(render_html(card), encoding="utf-8")
    return card
