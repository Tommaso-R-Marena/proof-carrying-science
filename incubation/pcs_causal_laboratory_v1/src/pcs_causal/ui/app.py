"""Minimal local Flask workbench for causal queries (offline).

Mathematical authority remains in the checker modules, not this UI.
"""

from __future__ import annotations

import json
from typing import Any

try:
    from flask import Flask, jsonify, request
except ImportError:  # pragma: no cover
    Flask = None  # type: ignore


def create_app() -> "Flask":
    if Flask is None:
        raise RuntimeError("Flask not installed; pip install flask or uv pip install flask")

    app = Flask(__name__)

    @app.get("/")
    def index():
        return INDEX_HTML

    @app.post("/api/backdoor")
    def api_backdoor():
        from pcs_causal.graphs.dag import CausalDAG
        from pcs_causal.identification.backdoor import verify_backdoor_set

        data = request.get_json(force=True)
        g = CausalDAG.from_dict(data["graph"])
        res = verify_backdoor_set(
            g, data["treatment"], data["outcome"], data.get("adjustment_set", [])
        )
        return jsonify(res.to_dict())

    @app.post("/api/dsep")
    def api_dsep():
        from pcs_causal.graphs.dag import CausalDAG
        from pcs_causal.graphs.d_separation import d_separated

        data = request.get_json(force=True)
        g = CausalDAG.from_dict(data["graph"])
        sep = d_separated(g, data["x"], data["y"], data.get("z", []))
        return jsonify({"separated": sep, "authority": "d_separation_recomputed"})

    @app.get("/api/demo/drug")
    def api_drug():
        from pcs_causal.cases.biology_synth import drug_response_confounding_case

        return jsonify(drug_response_confounding_case())

    @app.get("/api/demo/witness")
    def api_witness():
        from pcs_causal.nonident.witness_search import classic_confounding_witness
        from pcs_causal.nonident.witness_verifier import verify_witness

        w = classic_confounding_witness()
        v = verify_witness(w)
        return jsonify(
            {
                "verdict": v.to_dict(),
                "obs_a": w.observational_a().to_dict(),
                "obs_b": w.observational_b().to_dict(),
                "int_a": w.interventional_a().to_dict(),
                "int_b": w.interventional_b().to_dict(),
                "notice": "UI displays checker output; UI is not the authority.",
            }
        )

    return app


def run_app(host: str = "127.0.0.1", port: int = 8765) -> None:
    app = create_app()
    # threaded=True so long witness searches do not block other UI requests
    app.run(host=host, port=port, debug=False, threaded=True)


INDEX_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<title>PCS Causal Laboratory</title>
<style>
:root {
  --bg0: #0f1c17;
  --bg1: #1a3329;
  --ink: #e7f2ea;
  --muted: #9bb5a6;
  --accent: #d4a03c;
  --line: rgba(231,242,234,0.14);
  --danger: #e07a5f;
  --ok: #7cb89a;
}
*{box-sizing:border-box}
body{
  margin:0;font-family:"IBM Plex Sans","Source Sans 3",sans-serif;
  color:var(--ink);
  background:
    radial-gradient(1200px 600px at 10% -10%, #2a4a3a 0%, transparent 55%),
    radial-gradient(900px 500px at 100% 0%, #3a2f18 0%, transparent 50%),
    linear-gradient(160deg, var(--bg0), var(--bg1));
  min-height:100vh;
}
header{padding:2.5rem 1.5rem 1rem;max-width:960px;margin:0 auto}
h1{font-family:"IBM Plex Serif","Source Serif 4",serif;font-weight:600;font-size:clamp(1.8rem,4vw,2.6rem);margin:0 0 .5rem;letter-spacing:-0.02em}
.tag{color:var(--accent);text-transform:uppercase;letter-spacing:.12em;font-size:.75rem}
.lead{color:var(--muted);max-width:40rem;line-height:1.5}
main{max-width:960px;margin:0 auto;padding:1rem 1.5rem 3rem;display:grid;gap:1.25rem}
section{border-top:1px solid var(--line);padding-top:1rem}
h2{font-size:1.1rem;margin:0 0 .5rem}
p,li{color:var(--muted);line-height:1.45}
button{
  background:var(--accent);color:#1a1408;border:0;padding:.65rem 1rem;
  font-weight:600;cursor:pointer;margin-right:.5rem;margin-top:.5rem
}
button:hover{filter:brightness(1.05)}
pre{
  background:rgba(0,0,0,.35);border:1px solid var(--line);
  padding:1rem;overflow:auto;font-size:.82rem;line-height:1.4;color:var(--ink)
}
.notice{border-left:3px solid var(--danger);padding-left:.75rem;color:var(--muted)}
.ok{color:var(--ok)}
</style>
</head>
<body>
<header>
  <div class="tag">Independent incubation · not PCS production authority</div>
  <h1>PCS Causal Laboratory</h1>
  <p class="lead">Local workbench for exact finite identification, non-identifiability witnesses, and assumption-explicit causal queries. The UI only displays checker output.</p>
</header>
<main>
  <section>
    <h2>Scientific honesty</h2>
    <p class="notice">Identification under assumptions ≠ empirical validation. Statistical association ≠ causation. Simulated experiments are not laboratory results.</p>
  </section>
  <section>
    <h2>Demonstrations</h2>
    <button onclick="loadDrug()">Synthetic drug confounding</button>
    <button onclick="loadWitness()">Non-identifiability witness</button>
    <pre id="out">Select a demonstration.</pre>
  </section>
  <section>
    <h2>Backdoor check (JSON graph)</h2>
    <p>Default classic confounding graph; edit freely.</p>
    <textarea id="payload" rows="12" style="width:100%;background:rgba(0,0,0,.35);color:var(--ink);border:1px solid var(--line);padding:.75rem;font-family:ui-monospace,monospace">{
{
  "graph": {"nodes": ["Z","X","Y"], "edges": [["Z","X"],["Z","Y"],["X","Y"]]},
  "treatment": "X",
  "outcome": "Y",
  "adjustment_set": ["Z"]
}
</textarea>
    <button onclick="checkBackdoor()">Verify backdoor set</button>
  </section>
</main>
<script>
async function loadDrug(){
  const r = await fetch('/api/demo/drug');
  document.getElementById('out').textContent = JSON.stringify(await r.json(), null, 2);
}
async function loadWitness(){
  document.getElementById('out').textContent = 'Searching/verifying witness…';
  const r = await fetch('/api/demo/witness');
  document.getElementById('out').textContent = JSON.stringify(await r.json(), null, 2);
}
async function checkBackdoor(){
  const body = document.getElementById('payload').value;
  const r = await fetch('/api/backdoor', {method:'POST', headers:{'Content-Type':'application/json'}, body});
  document.getElementById('out').textContent = JSON.stringify(await r.json(), null, 2);
}
</script>
</body>
</html>
"""
