from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from collections import deque
from pathlib import Path, PurePosixPath
from typing import Any, Callable

from .byte_contract_v06 import parse_certificate_bytes_v06, verify_signed_certificate_bytes_v06
from .canonical_json import CanonicalJSONError, canonicalize_jcs, parse_jcs_json
from .environment_replay_v06 import environment_from_binding_v06
from .jsonio import strict_json_load
from .verifier_io_v06 import load_public_key_v06


SANDBOX_REPLAY_PLAN_FORMAT_V06 = "pcs-sandboxed-replay-plan-v1"
REALIZED_ENVIRONMENT_FORMAT_V06 = "pcs-realized-environment-v1"
SANDBOX_REPLAY_RECEIPT_FORMAT_V06 = "pcs-sandboxed-replay-receipt-v1"
WORKFLOW_CONTRACT_NAMESPACE_V06 = "pcs-manifest-workflow-contract-v1"
MAX_LOG_BYTES_V06 = 64 * 1024
MAX_PACKAGES_V06 = 5000

_FIXED_ENV = {
    "HOME": "/tmp",
    "LANG": "C.UTF-8",
    "LC_ALL": "C.UTF-8",
    "OMP_NUM_THREADS": "1",
    "OPENBLAS_NUM_THREADS": "1",
    "MKL_NUM_THREADS": "1",
    "NUMEXPR_NUM_THREADS": "1",
    "PYTHONHASHSEED": "0",
    "PYTHONDONTWRITEBYTECODE": "1",
    "PYTHONNOUSERSITE": "1",
    "SOURCE_DATE_EPOCH": "0",
    "TZ": "UTC",
}

_PY_PROBE = r"""
import hashlib, importlib.metadata as md, json, platform, sys
def digest(p):
    try:
        h=hashlib.sha256()
        with open(p,"rb") as f:
            for b in iter(lambda:f.read(1048576),b""): h.update(b)
        return h.hexdigest()
    except Exception: return None
pkgs=[]
for d in md.distributions():
    n=d.metadata.get("Name") or getattr(d,"name",None)
    if n: pkgs.append({"name":str(n),"version":str(d.version),"requires":sorted(str(x) for x in (d.requires or []))[:256]})
pkgs.sort(key=lambda x:(x["name"].lower().replace("_","-"),x["version"]))
print(json.dumps({"implementation":platform.python_implementation(),"version":platform.python_version(),
"executable":sys.executable,"executable_sha256":digest(sys.executable),"packages":pkgs[:5000],
"packages_truncated":len(pkgs)>5000},sort_keys=True,separators=(",",":")))
"""


class V06SandboxReplayError(ValueError):
    pass


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _semantic(value: Any) -> str:
    return _sha(canonicalize_jcs(value).encode("utf-8"))


def _path(value: str) -> PurePosixPath:
    if not isinstance(value, str) or not value or "\\" in value:
        raise V06SandboxReplayError(f"unsafe project-relative path: {value!r}")
    p = PurePosixPath(value)
    if p.is_absolute() or p.as_posix() != value or any(x in ("", ".", "..") for x in p.parts):
        raise V06SandboxReplayError(f"unsafe project-relative path: {value!r}")
    return p


def _workflow_contract(node: dict[str, Any]) -> dict[str, Any] | None:
    c = node.get("contract")
    if not (isinstance(c, dict) and c.get("type") == "external" and
            c.get("namespace") == WORKFLOW_CONTRACT_NAMESPACE_V06):
        return None
    raw = c.get("proposition")
    if not isinstance(raw, str):
        raise V06SandboxReplayError(f"workflow node {node.get('id')!r} lacks proposition")
    try:
        value = parse_jcs_json(raw)
    except CanonicalJSONError as exc:
        raise V06SandboxReplayError(f"invalid workflow proposition: {exc}") from exc
    if not isinstance(value, dict) or canonicalize_jcs(value) != raw:
        raise V06SandboxReplayError("workflow proposition is not canonical JCS")
    if value.get("human_confirmed") is not True or value.get("static_only") is not True:
        raise V06SandboxReplayError("workflow proposition is not confirmed static analysis")
    if value.get("source_kind") not in {"python", "jupyter", "r"}:
        raise V06SandboxReplayError("workflow source kind is not executable")
    return value


def _artifacts(cert: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out = {}
    paths = set()
    for a in cert.get("artifacts", []):
        if not isinstance(a, dict) or not isinstance(a.get("id"), str):
            continue
        if not isinstance(a.get("source_path"), str):
            continue
        _path(a["source_path"])
        if a["id"] in out or a["source_path"] in paths:
            raise V06SandboxReplayError("duplicate signed artifact id/source_path")
        paths.add(a["source_path"])
        out[a["id"]] = a
    return out


def _toposort(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id = {n["id"]: n for n in nodes}
    if len(by_id) != len(nodes):
        raise V06SandboxReplayError("duplicate workflow node id")
    producer = {}
    for n in nodes:
        for a in n["output_ids"]:
            if a in producer:
                raise V06SandboxReplayError(f"multiple producers for {a!r}")
            producer[a] = n["id"]
    edges = {n["id"]: set() for n in nodes}
    indeg = {n["id"]: 0 for n in nodes}
    for n in nodes:
        for a in n["inputs"]:
            p = producer.get(a)
            if p and p != n["id"] and n["id"] not in edges[p]:
                edges[p].add(n["id"]); indeg[n["id"]] += 1
    q = deque(sorted(k for k, v in indeg.items() if v == 0)); order = []
    while q:
        x = q.popleft(); order.append(x)
        for y in sorted(edges[x]):
            indeg[y] -= 1
            if indeg[y] == 0: q.append(y)
    if len(order) != len(nodes):
        raise V06SandboxReplayError("workflow graph is cyclic")
    return [by_id[x] for x in order]


def _norm_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _exact_pins(env: dict[str, Any]) -> dict[str, dict[str, str]]:
    out = {"python": {}, "r": {}, "conda": {}}
    for eco in out:
        sec = env.get(eco, {})
        for dep in sec.get("dependencies", []) if isinstance(sec, dict) else []:
            if not isinstance(dep, dict) or dep.get("exact_pin") is not True:
                continue
            n, v = dep.get("name"), dep.get("version")
            if isinstance(n, str) and isinstance(v, str):
                key = _norm_name(n)
                prior = out[eco].get(key)
                if prior is not None and prior != v:
                    raise V06SandboxReplayError(f"conflicting signed exact pins for {eco}:{key}")
                out[eco][key] = v
    return out


def build_sandbox_replay_plan_v06(cert: dict[str, Any], env: dict[str, Any]) -> dict[str, Any] | None:
    arts = _artifacts(cert); nodes = []
    for n in cert.get("workflow", {}).get("nodes", []):
        if not isinstance(n, dict): continue
        c = _workflow_contract(n)
        if c is None: continue
        outputs = []
        for aid in n.get("outputs", []):
            a = arts.get(aid)
            if a is None: raise V06SandboxReplayError(f"unknown workflow output {aid!r}")
            outputs.append({"artifact_id": aid, "source_path": a["source_path"],
                            "sha256": a["sha256"], "size": a.get("size")})
        if not outputs: continue
        source = c.get("source_path")
        source_id = next((aid for aid in n.get("inputs", [])
                          if aid in arts and arts[aid]["source_path"] == source), None)
        if source_id is None:
            raise V06SandboxReplayError(f"workflow source {source!r} is not a signed input")
        nodes.append({"id": n["id"], "source_kind": c["source_kind"], "source_path": source,
                      "source_artifact_id": source_id, "inputs": list(n.get("inputs", [])),
                      "output_ids": [x["artifact_id"] for x in outputs], "outputs": outputs,
                      "dependency_claim_mode": c.get("dependency_claim_mode")})
    if not nodes: return None
    nodes = _toposort(nodes)
    output_ids = {x for n in nodes for x in n["output_ids"]}
    plan = {
        "format": SANDBOX_REPLAY_PLAN_FORMAT_V06,
        "environment_semantic_sha256": env.get("semantic_sha256"),
        "nodes": nodes,
        "signed_output_artifact_ids": sorted(output_ids),
        "signed_exact_dependencies": _exact_pins(env),
        "exact_output_namespace_claimed": all(n["dependency_claim_mode"] == "exact_resolved_set" for n in nodes),
        "sandbox_policy": {
            "network": "none", "root_filesystem": "read_only", "capabilities": "drop_all",
            "no_new_privileges": True, "preexisting_outputs_removed": True,
            "fixed_environment": dict(_FIXED_ENV), "wall_clock_virtualized": False,
            "entropy_source_virtualized": False,
            "determinism_scope": "clean signed inputs + fixed process environment + no network + fixed resource limits + exact output hashes; kernel time/entropy remain explicit TCB",
        },
    }
    plan["semantic_sha256"] = _semantic(plan)
    return plan


def write_sandbox_replay_plan_v06(plan: dict[str, Any], output: str | Path, *, overwrite: bool = False) -> Path:
    path = Path(output).resolve()
    if path.exists() and not overwrite:
        raise V06SandboxReplayError(f"refusing to overwrite sandbox replay plan: {path}")
    path.write_text(json.dumps(plan, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def _version_tuple(v: str) -> tuple[int, ...] | None:
    m = re.match(r"^\s*(\d+(?:\.\d+)*)", v)
    return tuple(int(x) for x in m.group(1).split(".")) if m else None


def _constraint(realized: str | None, spec: str) -> str:
    if not realized: return "mismatch"
    if re.fullmatch(r"\d+(?:\.\d+){1,2}", spec.strip()):
        want = _version_tuple(spec); got = _version_tuple(realized)
        return "match" if got and want and got[:len(want)] == want else "mismatch"
    for part in [x.strip() for x in spec.split(",") if x.strip()]:
        m = re.match(r"^(==|>=|<=|>|<)\s*(\d+(?:\.\d+)*)$", part)
        if not m: return "unsupported_constraint"
        op, wanted = m.groups(); a, b = _version_tuple(realized), _version_tuple(wanted)
        if a is None or b is None: return "unsupported_constraint"
        width = max(len(a), len(b)); a += (0,) * (width-len(a)); b += (0,) * (width-len(b))
        cmpv = (a > b) - (a < b)
        if not {"==":cmpv==0,">=":cmpv>=0,"<=":cmpv<=0,">":cmpv>0,"<":cmpv<0}[op]:
            return "mismatch"
    return "match"


def compare_realized_environment_v06(env: dict[str, Any], realized: dict[str, Any],
                                     *, container_status: dict[str, Any]) -> dict[str, Any]:
    pins = _exact_pins(env); rows = []; loose = []; ok = True
    maps = {}
    for eco in ("python", "r", "conda"):
        maps[eco] = {_norm_name(x["name"]): x["version"] for x in realized.get(eco, {}).get("packages", [])
                     if isinstance(x, dict) and isinstance(x.get("name"), str) and isinstance(x.get("version"), str)}
        for name, expected in sorted(pins[eco].items()):
            got = maps[eco].get(name); status = "match" if got == expected else ("missing" if got is None else "version_mismatch")
            rows.append({"ecosystem": eco, "name": name, "expected": expected, "realized": got, "status": status})
            ok = ok and status == "match"
        section = env.get(eco, {})
        for dep in section.get("dependencies", []) if isinstance(section, dict) else []:
            if not isinstance(dep, dict) or dep.get("exact_pin") is True or not isinstance(dep.get("name"), str):
                continue
            name = _norm_name(dep["name"]); got = maps[eco].get(name)
            status = "present_spec_not_exactly_enforced" if got is not None else "missing"
            loose.append({"ecosystem": eco, "name": name, "declared": dep.get("raw"),
                          "realized": got, "status": status})
            ok = ok and got is not None
    interps = []
    for eco in ("python", "r"):
        got = realized.get(eco, {}).get("version")
        for item in env.get(eco, {}).get("interpreter_constraints", []):
            if isinstance(item, dict) and isinstance(item.get("value"), str):
                status = _constraint(got, item["value"]); ok = ok and status == "match"
                interps.append({"ecosystem": eco, "constraint": item["value"], "realized": got, "status": status})
    signed_containers = env.get("containers", [])
    if signed_containers:
        ok = ok and container_status.get("status") in {"derived_from_signed_contract", "image_digest_matches_signed_reference"}
    out = {
        "signed_exact_packages": rows,
        "signed_non_exact_dependencies": loose,
        "interpreter_constraints": interps,
        "container": container_status,
        "interpreter_binary_hash": {"status": "observed_not_signed",
            "python_sha256": realized.get("python", {}).get("executable_sha256"),
            "r_sha256": realized.get("r", {}).get("executable_sha256")},
        "os_architecture": {"status": "observed_not_signed", "value": realized.get("platform")},
        "container_image_digest": {"status": "observed_not_signed", "value": realized.get("container_image")},
        "dependency_tree_fingerprint": {"status": "observed_not_signed", "sha256": realized.get("dependency_tree_sha256")},
        "enforceable_contract_match": bool(ok),
    }
    out["semantic_sha256"] = _semantic(out)
    return out


def _run(argv: list[str], timeout: int) -> subprocess.CompletedProcess[bytes]:
    try:
        return subprocess.run(argv, capture_output=True, check=False, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise V06SandboxReplayError(f"OCI runtime command failed: {exc}") from exc


class _OciBackend:
    def __init__(self, *, runtime: str, sandbox_root: Path, signed_environment: dict[str, Any],
                 image: str | None, timeout_seconds: int, memory: str, cpus: float):
        names = ("docker", "podman") if runtime == "auto" else (runtime,)
        self.runtime = next((shutil.which(x) for x in names if x in {"docker","podman"} and shutil.which(x)), None)
        if not self.runtime:
            raise V06SandboxReplayError("sandbox execution requires Docker or Podman; no unsandboxed fallback is permitted")
        self.runtime_name = Path(self.runtime).name; self.root = sandbox_root; self.env = signed_environment
        self.image_ref = image; self.timeout = timeout_seconds; self.memory = memory; self.cpus = cpus
        self.built_image = False; self.image_meta: dict[str, Any] = {}

    def inspect(self) -> dict[str, Any]:
        p = _run([self.runtime, "image", "inspect", self.image_ref], self.timeout)
        if p.returncode: raise V06SandboxReplayError("cannot inspect OCI image: " + p.stderr.decode(errors="replace")[:4096])
        item = json.loads(p.stdout.decode())[0]
        return {"image_id": item.get("Id"), "repo_digests": sorted(item.get("RepoDigests") or []),
                "os": item.get("Os"), "architecture": item.get("Architecture")}

    def prepare_image(self, plan: dict[str, Any]) -> dict[str, Any]:
        containers = self.env.get("containers", [])
        if self.image_ref and containers:
            raise V06SandboxReplayError(
                "a signed container contract must be rebuilt offline from its signed "
                "Dockerfile; --image is only accepted when no container was signed"
            )
        if not self.image_ref:
            if len(containers) != 1 or not containers[0].get("all_base_images_digest_pinned"):
                raise V06SandboxReplayError("automatic replay requires one signed container with digest-pinned base(s), or explicit --image")
            for stage in containers[0].get("stages", []):
                reference = stage.get("reference") if isinstance(stage, dict) else None
                if not isinstance(reference, str) or "@sha256:" not in reference:
                    raise V06SandboxReplayError("signed container stage is not digest-pinned")
                local = _run([self.runtime, "image", "inspect", reference], self.timeout)
                if local.returncode != 0:
                    raise V06SandboxReplayError(
                        "signed base image is not already present locally; PCS refuses "
                        "a registry pull during deterministic replay: " + reference
                    )
            cf = self.root / _path(containers[0]["source_path"])
            text = cf.read_text(encoding="utf-8")
            if re.search(r"(?im)^\s*(ADD\s|#\s*syntax=)", text) or re.search(r"(?im)^\s*RUN\s+.*--network=(host|default)", text):
                raise V06SandboxReplayError("container file uses a construct disallowed by offline sandbox reconstruction")
            if re.search(r"(?im)^\s*RUN\s+.*--mount=type=(secret|ssh)\b", text):
                raise V06SandboxReplayError("secret/SSH build mounts are forbidden during replay")
            aliases=[]; stage_count=0
            for raw in text.splitlines():
                line=raw.strip()
                fm=re.match(r"(?i)^FROM\s+(?:--platform=\S+\s+)?\S+(?:\s+AS\s+([A-Za-z0-9_.-]+))?", line)
                if fm:
                    if fm.group(1): aliases.append(fm.group(1))
                    stage_count += 1
                cm=re.match(r"(?i)^COPY\s+--from=([^\s]+)", line)
                if cm:
                    ref=cm.group(1)
                    if not ((ref.isdigit() and int(ref) < stage_count) or ref in aliases):
                        raise V06SandboxReplayError(
                            "external COPY --from image is forbidden during offline replay: " + ref
                        )
            tag = "pcs-replay-" + plan["semantic_sha256"][:20]
            pull = "--pull=false" if self.runtime_name == "docker" else "--pull=never"
            p = _run([self.runtime,"build","--network=none","--no-cache",pull,"-t",tag,"-f",str(cf),str(self.root)], self.timeout)
            if p.returncode: raise V06SandboxReplayError("offline OCI build failed: " + p.stderr.decode(errors="replace")[:4096])
            self.image_ref = tag; self.built_image = True
        self.image_meta = self.inspect(); return self.image_meta

    def command(self, args: list[str]) -> dict[str, Any]:
        mount = f"type=bind,src={self.root},dst=/workspace"
        cmd = [self.runtime,"run","--rm","--network=none","--read-only","--cap-drop=ALL",
               "--security-opt=no-new-privileges","--pids-limit=256","--memory",self.memory,
               "--cpus",str(self.cpus),"--tmpfs","/tmp:rw,noexec,nosuid,nodev,size=256m",
               "--mount",mount,"--workdir","/workspace"]
        if hasattr(os,"getuid"): cmd += ["--user", f"{os.getuid()}:{os.getgid()}"]
        for k,v in sorted(_FIXED_ENV.items()): cmd += ["--env",f"{k}={v}"]
        p = _run(cmd + [self.image_ref] + args, self.timeout)
        so, se = p.stdout[:MAX_LOG_BYTES_V06], p.stderr[:MAX_LOG_BYTES_V06]
        return {"command": args, "exit_code": p.returncode, "stdout": so.decode(errors="replace"),
                "stderr": se.decode(errors="replace"), "stdout_sha256": _sha(p.stdout),
                "stderr_sha256": _sha(p.stderr), "stdout_truncated": len(p.stdout)>len(so),
                "stderr_truncated": len(p.stderr)>len(se)}

    def python(self) -> str:
        for x in ("python","python3"):
            if self.command([x,"-c","import sys"])["exit_code"] == 0: return x
        raise V06SandboxReplayError("replay image has no Python interpreter")

    def execute_node(self, node: dict[str, Any]) -> dict[str, Any]:
        src = "/workspace/" + node["source_path"]
        if node["source_kind"] == "python":
            return self.command([self.python(),"-B",src])
        if node["source_kind"] == "jupyter":
            return self.command([self.python(),"-B","-m","jupyter","nbconvert","--to","notebook","--execute",src,"--output","/tmp/pcs.ipynb"])
        return self.command(["Rscript","--vanilla",src])

    def capture_environment(self) -> dict[str, Any]:
        try:
            pyexe = self.python()
        except V06SandboxReplayError:
            pyexe = None
        if pyexe is None:
            pyv = {"available": False, "version": None, "executable_sha256": None, "packages": []}
        else:
            py = self.command([pyexe,"-I","-B","-c",_PY_PROBE])
            if py["exit_code"]: raise V06SandboxReplayError("Python environment probe failed")
            pyv = json.loads(py["stdout"])
        rp = self.command(["sh","-c","command -v Rscript >/dev/null && Rscript --vanilla -e 'cat(as.character(getRversion()))' || true"])
        rv = rp["stdout"].strip() or None
        rpk = self.command(["sh","-c","command -v Rscript >/dev/null || exit 0; Rscript --vanilla -e 'p<-installed.packages()[,c(\"Package\",\"Version\"),drop=FALSE]; write.table(p,sep=\"\\t\",row.names=FALSE,col.names=FALSE,quote=FALSE)'"])
        rpackages=[]
        for line in rpk["stdout"].splitlines()[:MAX_PACKAGES_V06]:
            parts=line.split("\t",1)
            if len(parts)==2: rpackages.append({"name":parts[0],"version":parts[1]})
        rhash = self.command(["sh","-c","p=$(command -v Rscript 2>/dev/null || true); test -n \"$p\" && (sha256sum \"$p\" 2>/dev/null || shasum -a 256 \"$p\" 2>/dev/null) | head -n1 || true"])["stdout"]
        rm = re.search(r"\b([0-9a-fA-F]{64})\b", rhash)
        con = self.command(["sh","-c","command -v conda >/dev/null && conda list --json || printf '[]'"])
        try: conda_raw = json.loads(con["stdout"])
        except json.JSONDecodeError: conda_raw = []
        conda = [{"name":x.get("name"),"version":x.get("version")} for x in conda_raw[:MAX_PACKAGES_V06] if isinstance(x,dict)]
        plat = self.command(["sh","-c","uname -srm; cat /etc/os-release 2>/dev/null || true"])["stdout"][:16384]
        tree = {"python": pyv.get("packages", []), "r": rpackages, "conda": conda}
        value = {"format": REALIZED_ENVIRONMENT_FORMAT_V06, "python": pyv,
                 "r": {"version": rv, "packages": rpackages, "executable_sha256": rm.group(1).lower() if rm else None},
                 "conda": {"packages": conda}, "platform": {"probe": plat,
                 "image_os": self.image_meta.get("os"), "image_architecture": self.image_meta.get("architecture")},
                 "container_image": self.image_meta, "dependency_tree_sha256": _semantic(tree)}
        value["semantic_sha256"] = _semantic(value); return value

    def close(self) -> None:
        if self.built_image and self.image_ref:
            _run([self.runtime,"image","rm","--force",self.image_ref], min(self.timeout,60))


def _container_status(env: dict[str, Any], backend: Any, image_arg: str | None) -> dict[str, Any]:
    if not env.get("containers"): return {"status": "not_declared"}
    if backend.built_image:
        return {"status": "derived_from_signed_contract", "realized_image": backend.image_meta, "offline_build": True}
    signed = {s["reference"].split("@",1)[1] for c in env.get("containers",[]) for s in c.get("stages",[])
              if isinstance(s,dict) and isinstance(s.get("reference"),str) and "@sha256:" in s["reference"]}
    realized = {x.split("@",1)[1] for x in backend.image_meta.get("repo_digests",[]) if "@sha256:" in x}
    return {"status": "image_digest_matches_signed_reference" if signed & realized else "image_not_bound_to_signed_reference",
            "signed_digests": sorted(signed), "realized_image": backend.image_meta, "offline_build": False}


def execute_prepared_replay_workspace_v06(
    workspace: str | Path, output: str | Path, public_key_path: str | Path, *,
    expected_fingerprint: str | None = None, runtime: str = "auto", image: str | None = None,
    timeout_seconds: int = 300, memory: str = "2g", cpus: float = 1.0,
    _backend_factory: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    root = Path(workspace).resolve(); dest = Path(output).resolve()
    if not root.is_dir() or root.is_symlink():
        raise V06SandboxReplayError("workspace must be a regular directory")
    if dest.exists():
        raise V06SandboxReplayError(f"output already exists: {dest}")
    try:
        dest.relative_to(root)
    except ValueError:
        pass
    else:
        raise V06SandboxReplayError(
            "execution output must not be created inside the prepared workspace"
        )
    if not isinstance(timeout_seconds, int) or not (1 <= timeout_seconds <= 86400):
        raise V06SandboxReplayError("timeout_seconds must be an integer from 1 to 86400")
    if not isinstance(cpus, (int, float)) or not (0 < float(cpus) <= 64):
        raise V06SandboxReplayError("cpus must be greater than 0 and at most 64")
    if not isinstance(memory, str) or not re.fullmatch(
        r"[1-9][0-9]*(?:[kKmMgGtT](?:[bB])?)?", memory
    ):
        raise V06SandboxReplayError(
            "memory must be a positive Docker/Podman size such as 512m or 2g"
        )
    meta = strict_json_load(root / "pcs-environment-workspace.json")
    if not isinstance(meta, dict) or meta.get("format") != "pcs-environment-workspace-v1":
        raise V06SandboxReplayError("unsupported prepared workspace")

    def bound_file(name_key: str, hash_key: str) -> bytes:
        relative = meta.get(name_key)
        expected = meta.get(hash_key)
        if not isinstance(relative, str) or not isinstance(expected, str):
            raise V06SandboxReplayError(f"prepared workspace lacks bound {name_key}")
        p = root / _path(relative)
        if not p.is_file() or p.is_symlink():
            raise V06SandboxReplayError(f"{name_key} is missing or unsafe")
        raw = p.read_bytes()
        if _sha(raw) != expected:
            raise V06SandboxReplayError(f"{name_key} hash mismatch")
        return raw

    cert_raw = bound_file("signed_certificate","signed_certificate_sha256")
    sig_raw = bound_file("signed_certificate_signature","signed_certificate_signature_sha256")
    key = load_public_key_v06(public_key_path)
    verified = verify_signed_certificate_bytes_v06(cert_raw,sig_raw,key,expected_fingerprint=expected_fingerprint)
    if not verified.get("valid"): raise V06SandboxReplayError("signed certificate verification failed: " + "; ".join(verified.get("errors",[])))
    cert = parse_certificate_bytes_v06(cert_raw)
    env = environment_from_binding_v06(cert["environment"])
    env_raw = bound_file("signed_environment_contract","signed_environment_contract_sha256")
    if env_raw != canonicalize_jcs(env).encode() + b"\n": raise V06SandboxReplayError("signed environment copy differs from certificate")
    if meta.get("sandbox_execution_available") is not True:
        raise V06SandboxReplayError("prepared workspace has no output-producing static workflow execution plan")
    plan_relative = meta.get("sandbox_execution_plan")
    if not isinstance(plan_relative, str):
        raise V06SandboxReplayError("prepared workspace lacks sandbox execution plan")
    plan_path = root / _path(plan_relative)
    plan = strict_json_load(plan_path)
    if plan_path.is_symlink() or _sha(plan_path.read_bytes()) != meta.get("sandbox_execution_plan_sha256"):
        raise V06SandboxReplayError("sandbox plan hash mismatch")
    fresh = build_sandbox_replay_plan_v06(cert,env)
    if fresh is None or canonicalize_jcs(fresh) != canonicalize_jcs(plan):
        raise V06SandboxReplayError("sandbox plan differs from signed certificate/environment")

    staging = dest.with_name(dest.name + ".pcs-staging")
    if staging.exists(): raise V06SandboxReplayError(f"staging output already exists: {staging}")
    staging.mkdir(parents=True)
    temp = Path(tempfile.mkdtemp(prefix="pcs-v06-replay-")); sandbox = temp / "workspace"; sandbox.mkdir()
    backend = None
    try:
        arts = _artifacts(cert); materialized = {}
        rows = meta.get("materialized_artifacts")
        if not isinstance(rows, list):
            raise V06SandboxReplayError(
                "prepared workspace materialized_artifacts must be an array"
            )
        recorded = {}
        for row in rows:
            if not isinstance(row, dict) or not isinstance(row.get("artifact_id"), str):
                raise V06SandboxReplayError(
                    "prepared workspace contains an invalid artifact-ledger row"
                )
            aid = row["artifact_id"]
            if aid in recorded:
                raise V06SandboxReplayError(
                    f"prepared workspace contains duplicate artifact-ledger id {aid!r}"
                )
            recorded[aid] = row
        if set(recorded) != set(arts):
            raise V06SandboxReplayError(
                "prepared workspace artifact ledger differs from signed certificate"
            )
        for aid,a in arts.items():
            p = root / _path(a["source_path"]); raw = p.read_bytes()
            if p.is_symlink() or _sha(raw) != a["sha256"]: raise V06SandboxReplayError(f"signed artifact drift: {a['source_path']}")
            if aid not in recorded or recorded[aid]["sha256"] != a["sha256"]: raise V06SandboxReplayError(f"workspace metadata drift: {aid}")
            q = sandbox / _path(a["source_path"]); q.parent.mkdir(parents=True,exist_ok=True); q.write_bytes(raw)
            materialized[aid] = {"source_path":a["source_path"],"sha256":a["sha256"],"size":len(raw)}
        output_ids = set(plan["signed_output_artifact_ids"]); removed=[]
        for n in plan["nodes"]:
            for o in n["outputs"]:
                p=sandbox/_path(o["source_path"]); existed=p.exists()
                if existed: p.unlink()
                removed.append({"artifact_id":o["artifact_id"],"source_path":o["source_path"],"preexisting_signed_output_removed":existed})
        factory = _backend_factory or _OciBackend
        backend = factory(runtime=runtime,sandbox_root=sandbox,signed_environment=env,image=image,
                          timeout_seconds=timeout_seconds,memory=memory,cpus=cpus)
        backend.prepare_image(plan); runs=[]
        for n in plan["nodes"]:
            r=backend.execute_node(n); runs.append({"node_id":n["id"],**r})
            if r["exit_code"] != 0: break
        realized=backend.capture_environment()
        cstatus=_container_status(env,backend,image)
        comparison=compare_realized_environment_v06(env,realized,container_status=cstatus)
        unsafe_links=sorted(
            p.relative_to(sandbox).as_posix()
            for p in sandbox.rglob("*")
            if p.is_symlink()
        )
        outputs=[]
        for n in plan["nodes"]:
            for o in n["outputs"]:
                p=sandbox/_path(o["source_path"])
                if p.is_symlink():
                    status="unsafe_symlink"; digest=None; size=None
                elif not p.is_file():
                    status="missing"; digest=None; size=None
                else:
                    raw=p.read_bytes(); digest=_sha(raw); size=len(raw)
                    status="match" if digest==o["sha256"] and (o.get("size") is None or size==o["size"]) else "mismatch"
                outputs.append({**o,"realized_sha256":digest,"realized_size":size,"status":status})
        mutations=[]
        for aid,item in materialized.items():
            if aid in output_ids: continue
            p=sandbox/_path(item["source_path"])
            if p.is_symlink() or not p.is_file() or _sha(p.read_bytes()) != item["sha256"]:
                mutations.append({"artifact_id":aid,"source_path":item["source_path"],"status":"mutated_or_missing"})
        known={x["source_path"] for x in materialized.values()}
        extras=sorted(
            p.relative_to(sandbox).as_posix()
            for p in sandbox.rglob("*")
            if not p.is_symlink()
            and p.is_file()
            and p.relative_to(sandbox).as_posix() not in known
        )
        nodes_ok=len(runs)==len(plan["nodes"]) and all(x["exit_code"]==0 for x in runs)
        outputs_ok=len(outputs)==len(output_ids) and all(x["status"]=="match" for x in outputs)
        namespace_ok=not plan["exact_output_namespace_claimed"] or not extras
        filesystem_safe=not unsafe_links
        valid=nodes_ok and outputs_ok and not mutations and namespace_ok and filesystem_safe and comparison["enforceable_contract_match"]
        realized_path=staging/"pcs-realized-environment.json"
        realized_path.write_text(json.dumps(realized,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        for o in outputs:
            p=sandbox/_path(o["source_path"])
            if not p.is_symlink() and p.is_file():
                q=staging/"outputs"/_path(o["source_path"]); q.parent.mkdir(parents=True,exist_ok=True); q.write_bytes(p.read_bytes())
        receipt={"format":SANDBOX_REPLAY_RECEIPT_FORMAT_V06,"valid":valid,"bundle_sha256":meta.get("bundle_sha256"),
                 "certificate_semantic_hash":cert.get("semantic_hash"),"certificate_integrity_hash":cert.get("integrity_hash"),
                 "producer_public_key_fingerprint":verified.get("public_key_fingerprint"),
                 "environment_semantic_sha256":env.get("semantic_sha256"),"sandbox_replay_plan_sha256":plan.get("semantic_sha256"),
                 "sandbox_runtime":getattr(backend,"runtime_name",runtime),"sandbox_policy":plan["sandbox_policy"],
                 "preexisting_outputs":removed,"workflow_execution":runs,"workflow_outputs":outputs,
                 "non_output_artifact_mutations":mutations,"unsafe_symlinks":unsafe_links,"extra_files":extras,"environment_comparison":comparison,
                 "realized_environment_sha256":_sha(realized_path.read_bytes()),
                 "verdict":{"all_nodes_exited_zero":nodes_ok,"all_signed_outputs_reproduced_exactly":outputs_ok,
                 "signed_non_outputs_unchanged":not mutations,"exact_output_namespace_satisfied":namespace_ok,
                 "filesystem_contains_no_symlinks":filesystem_safe,
                 "enforceable_environment_contract_match":comparison["enforceable_contract_match"]},
                 "trust_boundary":"OCI runtime/host kernel/language introspection/SHA-256 remain trusted; unsigned realized fields are observations, not retroactive producer promises."}
        receipt["semantic_sha256"]=_semantic(receipt)
        (staging/"pcs-replay-execution.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        staging.replace(dest)
        return {"valid":valid,"format":SANDBOX_REPLAY_RECEIPT_FORMAT_V06,"output":str(dest),
                "realized_environment":str(dest/"pcs-realized-environment.json"),
                "execution_receipt":str(dest/"pcs-replay-execution.json"),"workflow_nodes_executed":len(runs),
                "workflow_outputs_checked":len(outputs),"environment_contract_match":comparison["enforceable_contract_match"]}
    except Exception:
        shutil.rmtree(staging,ignore_errors=True); raise
    finally:
        if backend is not None:
            try: backend.close()
            except Exception: pass
        shutil.rmtree(temp,ignore_errors=True)
