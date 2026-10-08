#!/usr/bin/env python3
"""Reproduce the real PCS/CertiForge adapter and bounded control demo locally.

Requires a separately retained, public CertiForge checkout and its
actual Rust binary. Writes only a new output directory, with no credentials.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pcs.certiforge_adapter_v1 import FORMAT, MEMBERS, evaluate, research_claim_graph
from pcs.control_monitor_v1 import ControlMonitor, consistent_audit


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def run(args, **kwargs):
    process = subprocess.run(list(map(str, args)), capture_output=True, text=True, timeout=180, **kwargs)
    if process.returncode:
        raise RuntimeError(f"required command failed: {args[0]} (exit {process.returncode})")
    return process.stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkout", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    checkout = args.checkout.resolve(strict=True)
    source_sha = run(["git", "-C", checkout, "rev-parse", "HEAD"]).strip()
    if run(["git", "-C", checkout, "status", "--porcelain"]).strip():
        raise RuntimeError("commit the verified CertiForge source before binding demo evidence")
    binary = checkout / "target/debug/certiforge"
    binary_sha = digest(binary.read_bytes())
    args.output.mkdir(parents=True, exist_ok=False)
    output = args.output.resolve()
    original = output / "input.certir"
    original.write_text("fn proposed(x: u8, y: u8) -> u8 { add(and(x, y), xor(x, y)) }\n")
    optimized = output / "optimized.certir"
    search = json.loads(run([binary, "optimize", original, "--seed", "42", "--out", optimized]))
    environment = dict(os.environ, SOURCE_DATE_EPOCH="0", CERTIFORGE_GIT_COMMIT=source_sha)
    package = output / "package"
    run([binary, "package", "build", original, "--optimized", optimized, "--out", package, "--seed", "42"], env=environment)
    proposal = {"format": FORMAT, "claim_id": "or-optimization", "source": {
        "repository": "Tommaso-R-Marena/certiforge", "commit": source_sha, "disclosure": "public"},
        "artifacts": [{"id": str(i), "path": name, "sha256": digest((package/name).read_bytes())}
                      for i, name in enumerate(sorted(MEMBERS))],
        "cost_objective": {"metric": "CERTIR_AST_NODE_COUNT", "require_improvement": True}}
    pins = {"checker": binary, "checker_sha256": binary_sha, "checker_source_commit": source_sha}
    positive = evaluate(proposal, package, **pins)
    assert positive["state"] == "CHECKED_EXHAUSTIVE", positive
    assert positive["pcs_authority"] is False and positive["lean_kernel_checked"] is False
    # Rebind both producer proposal and manifest to a malicious optimized program.
    # Hash checking alone passes; the independent exhaustive checker must reject it.
    malicious = "fn proposed(x: u8, y: u8) -> u8 { x }\n".encode()
    (package / "optimized.certir").write_bytes(malicious)
    manifest = json.loads((package / "manifest.json").read_text())
    manifest["hashes"]["optimized.certir"] = digest(malicious)
    (package / "manifest.json").write_text(json.dumps(manifest, sort_keys=True, indent=2)+"\n")
    bad_proposal = json.loads(json.dumps(proposal))
    for entry in bad_proposal["artifacts"]:
        entry["sha256"] = digest((package / entry["path"]).read_bytes())
    negative = evaluate(bad_proposal, package, **pins)
    assert negative["state"] == "REJECTED", negative
    # Restore the actual valid demo bundle, with deterministic producer metadata.
    (package / "optimized.certir").write_bytes(optimized.read_bytes())
    run([binary, "package", "build", original, "--optimized", optimized, "--out", package, "--seed", "42"], env=environment)
    assert evaluate(proposal, package, **pins) == positive
    graph = research_claim_graph(proposal, positive, package)
    assert graph["claim_ir"]["claims"][0]["closure_state"] == "BLOCKED"
    effect_file = output / "authorized-result.json"
    def effect(value):
        with effect_file.open("x") as file:
            json.dump({"value": value}, file, sort_keys=True)
    monitor = ControlMonitor({"format": "pcs-control-policy-v1", "operation": "write_result",
                              "max_actions": 1, "max_value": 255}, effect)
    action = {"nonce": "demo-1", "operation": "write_result", "value": 42, "policy_sha256": monitor.policy_sha256}
    attacks = [dict(action, operation="delete"), dict(action, approved=True), dict(action, policy_sha256="0"*64)]
    for attack in attacks:
        assert monitor.submit(attack)["state"].startswith("REJECTED")
        assert not effect_file.exists()
    assert monitor.submit(action)["state"] == "EXECUTED"
    assert monitor.submit(action)["state"] == "REJECTED_REPLAY"
    monitor.revoke()
    assert monitor.submit(dict(action, nonce="after-revocation"))["state"] == "REJECTED_REVOKED"
    assert json.loads(effect_file.read_text()) == {"value": 42}
    assert consistent_audit(monitor.audit, monitor.policy_sha256)
    core_sha = run(["git", "-C", ROOT, "rev-parse", "HEAD"]).strip()
    report = {"format": "pcs-integrated-demo-v1", "core_commit": core_sha, "certiforge_commit": source_sha,
              "checker_sha256": binary_sha, "seed": 42, "source_date_epoch": 0,
              "optimization": positive, "malicious_rebound_optimization": negative,
              "optimizer_weighted_cost": {"original": search["original_cost"], "best": search["best"]["static_cost"]},
              "control": {"policy_sha256": monitor.policy_sha256, "audit": monitor.audit, "actual_effect_count": 1},
              "formal_promotion": False,
              "limitations": ["No AST-bound Lean certificate or Rust/Lean refinement", "External compiler/build correspondence trusted",
                  "No native executable guarantee", "Proposal-only monitor assumes exclusive trusted effect interface and faithful logging",
                  "No claim of general AI alignment", "Private CertiForge component requires separate disclosure clearance"]}
    (output / "proposal.json").write_text(json.dumps(proposal, sort_keys=True, indent=2)+"\n")
    (output / "result.json").write_text(json.dumps(report, sort_keys=True, indent=2)+"\n")
    (output / "claim-graph.json").write_text(json.dumps(graph, sort_keys=True, indent=2)+"\n")
    # A local, no-network evidence view; untrusted data is inserted as text only.
    payload = json.dumps({"result": report, "graph": graph}, sort_keys=True).replace("<", "\\u003c")
    viewer = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>PCS scoped optimization evidence</title><style>
body{font:17px system-ui;margin:0;background:#edf2f4;color:#163641}main{max-width:1100px;margin:auto;padding:24px}h1{font-size:clamp(25px,5vw,42px)}
.boundary{padding:18px;background:#fff1dc;border-left:5px solid #b87515}.columns{display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-top:20px}
button{display:block;width:100%;text-align:left;padding:13px;margin:7px 0;background:white;border:1px solid #aac0c8;border-radius:6px;cursor:pointer;color:#163641}
button:focus{outline:3px solid #347cbd}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:13px;background:white;padding:15px}section{min-width:0}@media(max-width:700px){.columns{grid-template-columns:1fr}}
</style><main><h1>Inspect a checked optimization</h1><p>The optimizer proposes a cheaper program. A separate, pinned Rust checker replays every supported input and rejects a deliberately incorrect candidate.</p>
<div class="boundary"><strong>Formal authority remains blocked.</strong> This package result is computational evidence. Rust/Lean refinement, certificate checking, intended specification and native execution remain unresolved.</div>
<p id="summary"></p><div class="columns"><section><h2>Claims, artifacts and obligations</h2><div id="nodes"></div></section><section><h2>Selected evidence</h2><pre id="detail"></pre></section></div></main>
<script>const data=PAYLOAD;const detail=document.getElementById('detail');const show=x=>detail.textContent=JSON.stringify(x,null,2);
document.getElementById('summary').textContent='Checked '+data.result.optimization.domain_size+' input pairs; AST nodes '+data.result.optimization.cost.original+' → '+data.result.optimization.cost.optimized+'. One authorized file write; malicious optimization rejected.';
for(const node of data.graph.obligation_graph.nodes){const b=document.createElement('button');b.textContent=node.type+' · '+node.id+' · '+node.status;b.addEventListener('click',()=>show(node));document.getElementById('nodes').appendChild(b)}
const b=document.createElement('button');b.textContent='Complete checker and control evidence';b.addEventListener('click',()=>show(data.result));document.getElementById('nodes').prepend(b);show(data.result);
</script></html>'''.replace('PAYLOAD', payload)
    (output / "evidence.html").write_text(viewer)
    print(json.dumps({"state": "LOCAL_COMPUTATIONAL_DEMO_PASSED", "domain_size": positive["domain_size"],
                      "cost": positive["cost"], "formal_promotion": False, "output": str(output)}, indent=2))


if __name__ == "__main__":
    main()
