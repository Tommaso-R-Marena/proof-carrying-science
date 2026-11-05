"""Read-only diagnostics; readiness is not a proof or a model safety verdict."""
import importlib.metadata
import json
from pathlib import Path
import platform
import shutil
import subprocess
import sys

from research.real_model_execution_v2.artifacts import digest,verify
from research.real_model_execution_v2.protocol import VERSIONS,environment


def inspect(tokenizer=None,bundle=None,dependencies=None):
    checks=[]
    def add(name,ok,detail,fix=""):
        checks.append(dict(name=name,ready=bool(ok),detail=detail,next_step="" if ok else fix))
    supported=platform.system()=="Linux" and platform.machine() in ("x86_64","AMD64")
    add("platform",supported,platform.system()+" "+platform.machine(),"Use a Linux x86_64 host for the qualified native workflow.")
    add("python",sys.version_info[:2]==(3,12),platform.python_version(),"Use Python 3.12 with the repository's frozen dependencies.")
    lean_ok=False
    if supported:
        from research.progress_supervisor_v1.authority import TOOLS
        lean=shutil.which("lean")
        try:lean_ok=bool(lean) and all(digest(Path(lean).with_name(n).read_bytes())==sha for n,sha in TOOLS.items())
        except OSError:pass
    add("lean_tools",lean_ok,"Exact Lean/leanchecker/leanc bytes "+("matched" if lean_ok else "not available"),"Run: source scripts/activate_lean_428.sh")
    try:token_ok=importlib.metadata.version("tokenizers")==VERSIONS["tokenizers"]
    except importlib.metadata.PackageNotFoundError:token_ok=False
    add("token_checker",token_ok,"Pinned Rust tokenizer "+("available" if token_ok else "missing or different"),"Install: python -m pip install --no-deps --require-hashes -r research/real_model_execution_v2/requirements-tokenizer.lock")
    for name,path,profile in (("tokenizer_files",tokenizer,"tokenizer"),("model_bundle",bundle,"full")):
        ok=False
        if supported and path is not None:
            try:verify(path,profile);ok=True
            except (OSError,ValueError):pass
        add(name,ok,"Pinned file bytes "+("matched" if ok else "not checked or unavailable"),
            "Fetch a fresh directory: python -m research.real_model_execution_v2 fetch NEW_DIRECTORY"+(" --full" if profile=="full" else ""))
    deps_ok=False
    if dependencies is not None:
        code="import json,importlib.metadata as m;print(json.dumps({n:m.version(n) for n in ('torch','transformers','tokenizers','safetensors')}))"
        try:
            r=subprocess.run([sys.executable,"-c",code],env=environment(dependencies),capture_output=True,timeout=15)
            deps_ok=r.returncode==0 and json.loads(r.stdout)==VERSIONS
        except (ValueError,OSError,subprocess.SubprocessError):pass
    add("model_dependencies",deps_ok,"Inference library versions "+("matched" if deps_ok else "not checked or unavailable"),"Provide --dependencies with the trusted optional inference library directory documented in PR #186.")
    state={c["name"]:c["ready"] for c in checks}
    base=all(state[n] for n in ("platform","python","lean_tools","token_checker"))
    return dict(format="pcs-lab-doctor-v1",checks=checks,ready_for=dict(recorded_replay=base and (tokenizer is None or state["tokenizer_files"]),
               live_model=base and state["model_bundle"] and state["model_dependencies"]),
               decoder_download_needed=tokenizer is None,inference_performed=False,kernel_checked=False,pcs_authority=False)


def human(result):
    lines=["PCS Agent Lab — readiness check (no inference or proof execution)"]
    for c in result["checks"]:
        lines.append(("OK   " if c["ready"] else "NEXT ")+c["name"]+": "+c["detail"])
        if c["next_step"]:lines.append("     "+c["next_step"])
    if result["decoder_download_needed"]:lines.append("Demo/replay will fetch pinned decoder files (~11 MB); no model weights are needed.")
    lines += ["Recorded replay: "+("ready to attempt" if result["ready_for"]["recorded_replay"] else "setup needed"),
              "Live model: "+("ready to attempt" if result["ready_for"]["live_model"] else "setup needed")]
    return "\n".join(lines)
