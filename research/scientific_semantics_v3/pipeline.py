"""Source-sealed experimental review and cache-independent semantic replay.

The unchanged v2/v1 stack owns byte intake and its authenticated cache. New
interpretations read only those snapshots, never the original mutable project.
No imported file can select a checker, executable, policy, reward, or verdict.
"""
from __future__ import annotations

from collections import Counter
import hashlib
import html
import json
import base64
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile

from pcs.jsonio import strict_json_loads
from research.scientific_intake_v1.intake import canonical, _regular, safe_name
from research.scientific_intake_v1.checks import bound_bytes
from research.scientific_understanding_v2 import pipeline as previous
from .semantics import interpret_project
from .checks import execute

FORMAT="pcs-scientific-semantics-package-v3"
MEMBERS={"semantics.json","checks.json","summary.json","dependencies.json","context.json","review.html"}


def context():
    root=Path(__file__).parent
    return {"schema":"scientific-semantics-context-v3","parent":previous.context(),
            "sources":{p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
                       for p in sorted(root.glob("*.py"))},
            "formal":{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((root/"formal").glob("*.lean"))},
            "authority":False,"training_policy":"DENIED_BY_DEFAULT"}


def _write(path,value):Path(path).write_bytes(canonical(value)+b"\n")


def snapshot_artifacts(folder):
    inventory=previous.portable_inventory(Path(folder)/"intake")
    return inventory,{a["path"]:bound_bytes(a) for a in inventory["artifacts"]}


def interpret_snapshots(artifacts):
    # Host-owned temporary paths contain copies of bound bytes; no source tree
    # is reopened during interpretation. They are removed on all normal exits.
    with tempfile.TemporaryDirectory(prefix="pcs-semantics-snapshot-") as td:
        directory=Path(td)
        for name,raw in artifacts.items():
            safe_name(name);path=directory/name;path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes(raw)
        return interpret_project(directory)


def bounded_stage(artifacts,check):
    if len(artifacts)>256 or sum(map(len,artifacts.values()))>16_000_000:raise ValueError("semantic input bound")
    payload=canonical({"artifacts":{n:base64.b64encode(raw).decode("ascii") for n,raw in artifacts.items()},"check":check})
    root=Path(__file__).resolve().parents[2]
    with tempfile.TemporaryDirectory(prefix="pcs-semantic-worker-") as td:
        env={"PATH":"/usr/bin:/bin","PYTHONPATH":str(root),"LANG":"C.UTF-8","TMPDIR":td}
        process=subprocess.Popen([sys.executable,"-m","research.scientific_semantics_v3.worker"],
            stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,cwd=root,env=env,start_new_session=True)
        try:
            out,err=process.communicate(payload,timeout=45)
        except BaseException:
            try:os.killpg(process.pid,signal.SIGKILL)
            except ProcessLookupError:pass
            process.communicate()
            raise
        if process.returncode or len(out)>32*1024**2:raise ValueError("bounded semantic worker failed; no result accepted")
        value=strict_json_loads(out.decode())
        if set(value)!={"semantics","checks"} or type(value["semantics"]) is not dict or type(value["checks"]) is not list:
            raise ValueError("invalid semantic worker result")
        return value["semantics"],value["checks"]


def summary_for(semantics,checks,authorized):
    return {"schema":"pcs-scientific-semantics-summary-v3","artifacts":len(semantics["artifacts"]),
            "claims":len(semantics["claims"]),"symbols":len(semantics["symbols"]),
            "unresolved":len(semantics["unresolved"]),"checks":dict(sorted(Counter(c["status"] for c in checks).items())),
            "authorized_checks":authorized,"scientific_meanings_certified":0,"authority":False,
            "training_examples_admitted":0,"learned_routing":"disabled; deterministic interpretation",
            "researcher_action":"Review source-linked meanings and unresolved assumptions before relying on scientific conclusions."}


def dependency_graph(semantics):
    claims={c["id"] for c in semantics["claims"]};symbols={s["id"] for s in semantics["symbols"]}
    if len(claims)!=len(semantics["claims"]) or len(symbols)!=len(semantics["symbols"]):raise ValueError("duplicate scientific node")
    edges=[]
    for dep in semantics["dependencies"]:
        if dep.get("from_claim") not in claims or dep.get("to_symbol") not in symbols:
            raise ValueError("dangling scientific dependency")
        edges.append({"from":dep["from_claim"],"to":dep["to_symbol"],"relation":"requires_scoped_symbol"})
    for claim in semantics["claims"]:
        edges.append({"from":claim["source"]["artifact_id"],"to":claim["id"],"relation":"byte_bound_interpretation"})
    return {"schema":"scientific-dependencies-v3","nodes":[{"id":c["id"],"kind":c["kind"],"authority":False} for c in semantics["claims"]]
            +[{"id":s["id"],"kind":"scoped_symbol","scope":s["scope"],"symbol":s["symbol"]} for s in semantics["symbols"]],
            "edges":edges,"dependency_completeness":"OPEN; supported symbol references only, not a proof of scientific completeness",
            "authority":False}


def review_html(semantics,checks,summary):
    by_claim={c.get("claim_id"):c for c in checks};items=[]
    escape=lambda x:html.escape(str(x))
    for claim in semantics["claims"]:
        src=claim["source"];result=by_claim.get(claim["id"],{})
        value=claim.get("value",claim.get("rhs","Not resolved"))
        items.append("<article><h3>"+escape(claim["entity"])+"</h3><p>"+escape(claim["quantity_role"])+": "+escape(value)+
                     "</p><p><strong>"+escape(result.get("status","Not checked"))+"</strong>. Scientific meaning needs review.</p>"+
                     "<p>Units: "+escape(claim.get("unit") or "not explicitly stated")+". Scope: "+escape(claim.get("scope","model"))+".</p>"+
                     "<details><summary>Read the exact source</summary><p>"+escape(src["path"])+"; bytes "+str(src["byte_start"])+"–"+str(src["byte_end"])+
                     '</p><a download href="baseline/intake/objects/'+escape(src["sha256"])+'">Download the original file</a><pre>'+escape(src["quote"])+"</pre></details><details><summary>Conditions and open questions</summary><pre>"+
                     escape(json.dumps({"conditions":claim.get("conditions"),"assumptions":claim.get("assumptions"),"domain":claim.get("domain")},indent=2))+
                     "</pre></details><details><summary>Exactly what was checked</summary><pre>"+escape(json.dumps(result,indent=2))+"</pre></details></article>")
    numerical=[c for c in checks if c.get("checker")=="nist-rounded-model-v3"]
    computed="".join("<article><h3>Reproducing the reported fit</h3><pre>"+escape(json.dumps(r,indent=2))+"</pre></article>" for r in numerical)
    unresolved="".join("<article><h3>Needs review</h3><p>"+escape(u.get("reason",u.get("statement","Unsupported interpretation")))+"</p><p>"+escape(u.get("source",{}).get("path","Project"))+"</p><pre>"+escape(u.get("source",{}).get("quote",""))+"</pre></article>" for u in semantics["unresolved"])
    return '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'"><title>PCS source review</title><style>body{font:18px system-ui;line-height:1.5;max-width:65rem;margin:2rem auto;padding:1rem}article{border:1px solid #ccc;border-radius:12px;padding:1rem;margin:1rem 0}pre{white-space:pre-wrap;overflow-wrap:anywhere}summary{cursor:pointer}</style><h1>What do these research files say?</h1><p>PCS organized '+str(summary["artifacts"])+' files and proposed '+str(summary["claims"])+' source-linked statements. Start with the result, then open its source to see where it came from.</p><p>A checked declaration confirms what the file says. A reproduced calculation checks a specific computation. Neither establishes that a scientific conclusion is true. Your files were not used for training.</p><h2>Reproduced computations</h2>'+computed+'<h2>What remains uncertain</h2>'+unresolved+'<h2>Statements to review</h2>'+"".join(items)+"</html>"


def run(source,output,*,check=False,cache_dir=None):
    if type(check) is not bool:raise ValueError("check authorization must be Boolean")
    source=Path(source).absolute();output=Path(output).absolute()
    if output.exists():raise ValueError("refuse evidence overwrite")
    if output.resolve().is_relative_to(source.resolve()):raise ValueError("output cannot be inside source")
    if cache_dir and (Path(cache_dir).resolve().is_relative_to(source.resolve()) or Path(cache_dir).resolve().is_relative_to(output.resolve())):
        raise ValueError("cache must be host-owned outside imported source and evidence")
    output.mkdir(parents=True,mode=0o700)
    previous.run(source,output/"baseline",check=check,cache_dir=cache_dir)
    _,artifacts=snapshot_artifacts(output/"baseline")
    meanings,checks=bounded_stage(artifacts,check)
    summary=summary_for(meanings,checks,check)
    for name,data in [("semantics",meanings),("checks",checks),("summary",summary),("dependencies",dependency_graph(meanings)),("context",context())]:
        _write(output/(name+".json"),data)
    (output/"review.html").write_text(review_html(meanings,checks,summary))
    files={p.relative_to(output).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(output.rglob("*")) if p.is_file()}
    _write(output/"manifest.json",{"format":FORMAT,"files":files,"authority":False})
    return summary


def replay(directory,*,recheck=True,expected_manifest_sha256=None):
    directory=Path(directory).absolute();raw=_regular(directory/"manifest.json",2*1024**2)
    if expected_manifest_sha256 and hashlib.sha256(raw).hexdigest()!=expected_manifest_sha256:raise ValueError("pinned manifest changed")
    manifest=strict_json_loads(raw.decode())
    if manifest.get("format")!=FORMAT or manifest.get("authority") is not False or not MEMBERS<=manifest.get("files",{}).keys() or len(manifest["files"])>360:
        raise ValueError("invalid semantic manifest")
    blobs={};total=0
    for name,sha in manifest["files"].items():
        safe_name(name)
        if name not in MEMBERS and not name.startswith("baseline/"):raise ValueError("unknown package member")
        path=directory/name
        if any(p.is_symlink() for p in [path,*path.parents] if p.is_relative_to(directory)):raise ValueError("symlink evidence path")
        data=_regular(path,64*1024**2);total+=len(data)
        if total>256*1024**2 or hashlib.sha256(data).hexdigest()!=sha:raise ValueError("changed or oversized evidence")
        blobs[name]=data
    parent=previous.replay(directory/"baseline",recheck=recheck,expected_manifest_sha256=manifest["files"].get("baseline/manifest.json"))
    nested=strict_json_loads(blobs["baseline/manifest.json"].decode())
    if {n for n in blobs if n.startswith("baseline/")}!={"baseline/"+n for n in nested["files"]}|{"baseline/manifest.json"}:raise ValueError("nested source census mismatch")
    if context()!=strict_json_loads(blobs["context.json"].decode()):raise ValueError("source or runtime context changed")
    _,artifacts=snapshot_artifacts(directory/"baseline")
    authorized=strict_json_loads(blobs["summary.json"].decode()).get("authorized_checks")
    meanings,fresh=bounded_stage(artifacts,recheck and authorized is True)
    if meanings!=strict_json_loads(blobs["semantics.json"].decode()):raise ValueError("interpretation replay mismatch")
    if dependency_graph(meanings)!=strict_json_loads(blobs["dependencies.json"].decode()):raise ValueError("dependency replay mismatch")
    checks=strict_json_loads(blobs["checks.json"].decode());summary=strict_json_loads(blobs["summary.json"].decode())
    statuses={"UNKNOWN","REFUTED","SOURCE_DECLARATION_CHECKED","SOURCE_REPORT_CHECKED","SCOPED_EQUATION_CHECKED","REPRODUCED_ROUNDED_COMPUTATION"}
    if any(c.get("authority") is not False or c.get("scientific_meaning")!="OPEN" or c.get("status") not in statuses for c in checks):
        raise ValueError("unrecognized check status or fabricated authority")
    if type(summary.get("authorized_checks")) is not bool or summary!=summary_for(meanings,checks,summary["authorized_checks"]):raise ValueError("summary replay mismatch")
    if blobs["review.html"].decode()!=review_html(meanings,checks,summary):raise ValueError("display replay mismatch")
    if not summary["authorized_checks"] and checks:raise ValueError("unauthorized check record")
    ids=[c["id"] for c in checks]
    if len(ids)!=len(set(ids)):raise ValueError("duplicate check record")
    if recheck and summary["authorized_checks"]:
        if previous.stable(fresh)!=previous.stable(checks):raise ValueError("independent computation replay mismatch")
    elif summary["authorized_checks"]:
        expected={"check-"+c["id"] for c in meanings["claims"]}|{"numerical-"+hashlib.sha256(path.encode()+data).hexdigest()[:24] for path,data in artifacts.items() if data.startswith(b"NIST/ITL StRD")}
        if set(ids)!=expected:raise ValueError("missing check record")
    return {"status":"REPLAYED" if recheck and summary["authorized_checks"] else "INTEGRITY_ONLY",
            "replayed_checks":len(checks) if recheck and summary["authorized_checks"] else 0,
            "parent_replay":parent,"cache_used":False,"authority":False,"scientific_meaning":"OPEN",
            "manifest_sha256":hashlib.sha256(raw).hexdigest()}
