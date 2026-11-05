from __future__ import annotations
import html
from pathlib import Path
from typing import Any


def _e(x: Any) -> str:
    return html.escape(str(x))


def render_html(cert: dict) -> str:
    claims=''.join(
        f"<tr><td><code>{_e(c.get('id'))}</code></td><td>{_e(c.get('statement'))}</td><td>{_e(c.get('kind'))}</td><td><strong>{_e(c.get('assessment',{}).get('status'))}</strong></td><td>{_e(', '.join(c.get('assumptions',[])) or '—')}</td></tr>"
        for c in cert.get('claims',[])
    )
    evidence=''.join(
        f"<tr><td><code>{_e(x.get('id'))}</code></td><td>{_e(x.get('kind'))}</td><td>{_e(x.get('outcome'))}</td><td>{_e(x.get('checker'))}</td><td>{_e(', '.join(x.get('claim_ids',[])))}</td></tr>"
        for x in cert.get('evidence',[])
    )
    artifacts=''.join(
        f"<tr><td><code>{_e(a.get('id'))}</code></td><td>{_e(a.get('role'))}</td><td><code>{_e(a.get('sha256'))}</code></td><td>{_e(a.get('path'))}</td></tr>"
        for a in cert.get('artifacts',[])
    )
    assumptions=''.join(
        f"<li><code>{_e(a.get('id'))}</code>: {_e(a.get('statement'))}</li>" for a in cert.get('assumptions',[])
    ) or '<li>None declared.</li>'
    return f'''<!doctype html>
<html><head><meta charset="utf-8"><title>PCS Assurance Report</title>
<style>
body{{font-family:system-ui,-apple-system,sans-serif;max-width:1100px;margin:40px auto;padding:0 24px;line-height:1.45;color:#171717}}
h1,h2{{letter-spacing:-.02em}} table{{border-collapse:collapse;width:100%;margin:12px 0 28px}} th,td{{border:1px solid #ddd;padding:8px;vertical-align:top;text-align:left}} th{{background:#f5f5f5}} code{{font-family:ui-monospace,monospace;font-size:.9em;word-break:break-all}} .notice{{padding:12px 14px;background:#f5f5f5;border-left:4px solid #777}} .meta{{display:grid;grid-template-columns:180px 1fr;gap:4px 14px}}
</style></head><body>
<h1>Proof-Carrying Science Assurance Report</h1>
<div class="notice"><strong>Scope:</strong> {_e(cert.get('mission_scope'))}. This report does not by itself establish biological, chemical, clinical, or regulatory validity.</div>
<h2>Certificate</h2><div class="meta">
<div>Subject</div><div>{_e(cert.get('subject'))}</div>
<div>Specification</div><div>{_e(cert.get('spec_version'))}</div>
<div>Checker</div><div>{_e(cert.get('checker_version'))}</div>
<div>Generated</div><div>{_e(cert.get('generated_at'))}</div>
<div>Semantic hash</div><div><code>{_e(cert.get('semantic_hash'))}</code></div>
<div>Integrity hash</div><div><code>{_e(cert.get('integrity_hash'))}</code></div>
</div>
<h2>Claims</h2><table><thead><tr><th>ID</th><th>Claim</th><th>Class</th><th>Assessment</th><th>Assumptions</th></tr></thead><tbody>{claims}</tbody></table>
<h2>Assumptions</h2><ul>{assumptions}</ul>
<h2>Evidence</h2><table><thead><tr><th>ID</th><th>Kind</th><th>Outcome</th><th>Checker</th><th>Claims</th></tr></thead><tbody>{evidence}</tbody></table>
<h2>Artifacts</h2><table><thead><tr><th>ID</th><th>Role</th><th>SHA-256</th><th>Packaged path</th></tr></thead><tbody>{artifacts}</tbody></table>
</body></html>'''


def write_html(cert: dict, path: str | Path) -> Path:
    p=Path(path); p.write_text(render_html(cert),encoding='utf-8'); return p
