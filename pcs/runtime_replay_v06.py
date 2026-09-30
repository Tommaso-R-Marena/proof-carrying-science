from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any

from .byte_contract_v06 import (
    parse_certificate_bytes_v06,
    verify_signed_certificate_bytes_v06,
)
from .canonical_json import CanonicalJSONError, canonicalize_jcs, parse_jcs_json
from .environment_replay_v06 import (
    V06EnvironmentReplayError,
    environment_from_binding_v06,
)
from .jsonio import StrictJSONError, strict_json_load
from .verifier_io_v06 import load_public_key_v06


REALIZED_ENVIRONMENT_FORMAT_V06 = "pcs-realized-environment-v1"
RUNTIME_REPLAY_RECEIPT_FORMAT_V06 = "pcs-runtime-replay-receipt-v1"
SIGNED_CERTIFICATE_FILE_V06 = "pcs-signed-certificate.json"
CERTIFICATE_SIGNATURE_FILE_V06 = "pcs-certificate-signature.json"
WORKSPACE_METADATA_FILE_V06 = "pcs-environment-workspace.json"
MAX_CAPTURED_PACKAGES_V06 = 10000
MAX_OUTPUT_FILES_V06 = 2048
MAX_OUTPUT_TOTAL_BYTES_V06 = 512 * 1024 * 1024
MAX_STDIO_CHARS_V06 = 64 * 1024

_NAME_SEP = re.compile(r"[-_.]+")
_VERSION_PART = re.compile(r"\d+")


class V06RuntimeReplayError(ValueError):
    pass


def _sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _sha256_path(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _safe_relative_path(value: str) -> PurePosixPath:
    if not isinstance(value, str) or not value or "\\" in value:
        raise V06RuntimeReplayError(f"unsafe project-relative path: {value!r}")
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or path.as_posix() != value
        or value.endswith("/")
        or any(part in ("", ".", "..") for part in path.parts)
    ):
        raise V06RuntimeReplayError(f"unsafe project-relative path: {value!r}")
    return path


def _workspace_path(root: Path, relative: str) -> Path:
    rel = _safe_relative_path(relative)
    target = root.joinpath(*rel.parts)
    try:
        target.resolve().relative_to(root.resolve())
    except (OSError, ValueError) as exc:
        raise V06RuntimeReplayError(
            f"workspace path escapes replay root: {relative!r}"
        ) from exc
    return target


def _normalized_name(value: str) -> str:
    return _NAME_SEP.sub("-", value).lower()


def _version_tuple(value: str) -> tuple[int, ...]:
    return tuple(int(x) for x in _VERSION_PART.findall(value)[:8])


def _pad_versions(
    a: tuple[int, ...], b: tuple[int, ...]
) -> tuple[tuple[int, ...], tuple[int, ...]]:
    length = max(len(a), len(b))
    return a + (0,) * (length - len(a)), b + (0,) * (length - len(b))


def _version_compare(actual: str, op: str, expected: str) -> bool:
    av = _version_tuple(actual)
    ev = _version_tuple(expected)
    if not av or not ev:
        return actual == expected if op in {"", "=="} else False
    ap, ep = _pad_versions(av, ev)
    if op in {"", "=="}:
        if expected.endswith(".*"):
            prefix = _version_tuple(expected[:-2])
            return av[: len(prefix)] == prefix
        if op == "":
            return av[: len(ev)] == ev
        return ap == ep
    if op == ">=":
        return ap >= ep
    if op == "<=":
        return ap <= ep
    if op == ">":
        return ap > ep
    if op == "<":
        return ap < ep
    if op == "!=":
        return ap != ep
    if op in {"~=", "~"}:
        if ap < ep:
            return False
        prefix_len = max(1, len(ev) - 1)
        return av[:prefix_len] == ev[:prefix_len]
    if op == "^":
        return ap >= ep and av[:1] == ev[:1]
    return False


def _satisfies_version_constraint(actual: str, constraint: str) -> bool:
    text = str(constraint).strip()
    if not text or text == "*":
        return True
    if "||" in text:
        return any(
            _satisfies_version_constraint(actual, part)
            for part in text.split("||")
        )
    for raw in text.split(","):
        token = raw.strip()
        if not token:
            continue
        match = re.match(r"^(>=|<=|==|!=|~=|>|<|\^|~)?\s*(.+?)\s*$", token)
        if not match:
            return False
        if not _version_compare(actual, match.group(1) or "", match.group(2)):
            return False
    return True


def _canonical_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()


def _parse_workflow_contract(node: dict[str, Any]) -> dict[str, Any]:
    contract = node.get("contract")
    if not isinstance(contract, dict):
        raise V06RuntimeReplayError(
            f"workflow node {node.get('id')!r} lacks an executable static contract"
        )
    if contract.get("type") != "external":
        raise V06RuntimeReplayError(
            f"workflow node {node.get('id')!r} is not an external static contract"
        )
    if contract.get("namespace") != "pcs-manifest-workflow-contract-v1":
        raise V06RuntimeReplayError(
            f"workflow node {node.get('id')!r} has unsupported contract namespace"
        )
    proposition = contract.get("proposition")
    if not isinstance(proposition, str):
        raise V06RuntimeReplayError(
            f"workflow node {node.get('id')!r} has non-string proposition"
        )
    try:
        value = parse_jcs_json(proposition)
    except CanonicalJSONError as exc:
        raise V06RuntimeReplayError(
            f"workflow node {node.get('id')!r} proposition is invalid JCS: {exc}"
        ) from exc
    if canonicalize_jcs(value) != proposition or not isinstance(value, dict):
        raise V06RuntimeReplayError(
            f"workflow node {node.get('id')!r} proposition is not canonical JCS"
        )
    if value.get("human_confirmed") is not True:
        raise V06RuntimeReplayError(
            f"workflow node {node.get('id')!r} is not human-confirmed"
        )
    if (
        value.get("static_only") is not True
        or value.get("user_code_executed") is not False
    ):
        raise V06RuntimeReplayError(
            f"workflow node {node.get('id')!r} violates static-discovery invariants"
        )
    return value


def workflow_execution_plan_v06(
    certificate: dict[str, Any],
) -> list[dict[str, Any]]:
    artifacts = {
        item["id"]: item
        for item in certificate.get("artifacts", [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    raw_nodes = certificate.get("workflow", {}).get("nodes", [])
    if not isinstance(raw_nodes, list) or not raw_nodes:
        raise V06RuntimeReplayError(
            "certificate has no executable static workflow nodes"
        )

    nodes: dict[str, dict[str, Any]] = {}
    producers: dict[str, str] = {}
    for node in raw_nodes:
        if not isinstance(node, dict) or not isinstance(node.get("id"), str):
            raise V06RuntimeReplayError("workflow nodes must have string ids")
        node_id = node["id"]
        if node_id in nodes:
            raise V06RuntimeReplayError(f"duplicate workflow node id: {node_id}")
        signed = _parse_workflow_contract(node)
        source_kind = signed.get("source_kind")
        source_path = signed.get("source_path")
        if source_kind not in {"python", "jupyter", "r"}:
            raise V06RuntimeReplayError(
                f"workflow node {node_id!r} source kind {source_kind!r} is not executable"
            )
        if not isinstance(source_path, str):
            raise V06RuntimeReplayError(
                f"workflow node {node_id!r} lacks source_path"
            )
        _safe_relative_path(source_path)
        inputs = list(node.get("inputs", []))
        outputs = list(node.get("outputs", []))
        if any(
            not isinstance(x, str) or x not in artifacts
            for x in inputs + outputs
        ):
            raise V06RuntimeReplayError(
                f"workflow node {node_id!r} references an unknown artifact"
            )
        for output_id in outputs:
            if output_id in producers:
                raise V06RuntimeReplayError(
                    f"workflow output {output_id!r} has multiple producers"
                )
            producers[output_id] = node_id

        matching = [
            artifact_id
            for artifact_id in inputs
            if artifacts[artifact_id].get("source_path") == source_path
        ]
        if len(matching) != 1:
            raise V06RuntimeReplayError(
                f"workflow node {node_id!r} cannot uniquely bind source artifact"
            )
        source_artifact_id = matching[0]
        if source_artifact_id in outputs:
            raise V06RuntimeReplayError(
                f"workflow node {node_id!r} declares its source as an output"
            )
        nodes[node_id] = {
            "id": node_id,
            "source_kind": source_kind,
            "source_path": source_path,
            "source_artifact_id": source_artifact_id,
            "inputs": inputs,
            "outputs": outputs,
        }

    indegree = {node_id: 0 for node_id in nodes}
    outgoing: dict[str, set[str]] = {node_id: set() for node_id in nodes}
    for node_id, node in nodes.items():
        for artifact_id in node["inputs"]:
            producer = producers.get(artifact_id)
            if producer is not None and producer != node_id:
                if node_id not in outgoing[producer]:
                    outgoing[producer].add(node_id)
                    indegree[node_id] += 1

    ready = sorted(
        node_id for node_id, degree in indegree.items() if degree == 0
    )
    ordered: list[dict[str, Any]] = []
    while ready:
        node_id = ready.pop(0)
        ordered.append(nodes[node_id])
        for target in sorted(outgoing[node_id]):
            indegree[target] -= 1
            if indegree[target] == 0:
                ready.append(target)
                ready.sort()
    if len(ordered) != len(nodes):
        raise V06RuntimeReplayError("workflow execution graph is cyclic")

    for node in ordered:
        contracts = []
        for output_id in node["outputs"]:
            source_path = artifacts[output_id].get("source_path")
            if not isinstance(source_path, str):
                raise V06RuntimeReplayError(
                    f"workflow output artifact {output_id!r} lacks source_path"
                )
            _safe_relative_path(source_path)
            contracts.append(
                {
                    "artifact_id": output_id,
                    "source_path": source_path,
                    "sha256": artifacts[output_id].get("sha256"),
                    "size": artifacts[output_id].get("size"),
                }
            )
        node["output_contracts"] = contracts
    return ordered


def _node_command_v06(node: dict[str, Any], index: int) -> list[str]:
    source = node["source_path"]
    kind = node["source_kind"]
    if kind == "python":
        return ["python", source]
    if kind == "r":
        return ["Rscript", source]
    if kind == "jupyter":
        return [
            "python",
            "-m",
            "jupyter",
            "nbconvert",
            "--to",
            "notebook",
            "--execute",
            source,
            "--output",
            f"/tmp/pcs-executed-{index}.ipynb",
            "--ExecutePreprocessor.timeout=-1",
        ]
    raise V06RuntimeReplayError(
        f"unsupported workflow source kind: {kind!r}"
    )


def _digest_pinned_image(value: str) -> bool:
    if not isinstance(value, str) or not value:
        return False
    if value.startswith("sha256:") and len(value) == 71:
        return True
    return bool(re.search(r"@sha256:[0-9a-fA-F]{64}$", value))


def select_replay_image_v06(
    environment: dict[str, Any],
    requested_image: str | None,
) -> str:
    if requested_image:
        if not _digest_pinned_image(requested_image):
            raise V06RuntimeReplayError(
                "sandbox execution image must be content-addressed by sha256 digest"
            )
        return requested_image
    refs = sorted(
        {
            stage["reference"]
            for container in environment.get("containers", [])
            if isinstance(container, dict)
            for stage in container.get("stages", [])
            if isinstance(stage, dict)
            and stage.get("digest_pinned") is True
            and stage.get("dynamic") is False
            and isinstance(stage.get("reference"), str)
        }
    )
    if len(refs) != 1:
        raise V06RuntimeReplayError(
            "cannot choose one deterministic OCI execution image from the signed "
            "contract; pass --image with a local sha256-pinned image"
        )
    return refs[0]


def select_oci_runtime_v06(requested: str = "auto") -> str:
    if requested not in {"auto", "docker", "podman"}:
        raise V06RuntimeReplayError(
            f"unsupported sandbox runtime: {requested!r}"
        )
    candidates = ("docker", "podman") if requested == "auto" else (requested,)
    for name in candidates:
        path = shutil.which(name)
        if path:
            return path
    raise V06RuntimeReplayError(
        "no OCI sandbox runtime found; install Docker or Podman. "
        "PCS does not fall back to unsandboxed execution."
    )


def _inspect_image_v06(runtime: str, image: str) -> dict[str, Any]:
    proc = subprocess.run(
        [runtime, "image", "inspect", image],
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        raise V06RuntimeReplayError(
            "execution image is not available locally; PCS uses pull=never: "
            + proc.stderr.strip()[:MAX_STDIO_CHARS_V06]
        )
    try:
        value = json.loads(proc.stdout)
        row = value[0]
    except (json.JSONDecodeError, IndexError, TypeError) as exc:
        raise V06RuntimeReplayError(
            "OCI runtime returned malformed image-inspection JSON"
        ) from exc
    if not isinstance(row, dict):
        raise V06RuntimeReplayError(
            "OCI image inspection root is not an object"
        )
    return {
        "requested": image,
        "image_id": row.get("Id") or row.get("ID"),
        "repo_digests": sorted(
            str(x)
            for x in (row.get("RepoDigests") or [])
            if isinstance(x, str)
        ),
        "os": row.get("Os") or row.get("OsVersion"),
        "architecture": row.get("Architecture") or row.get("Arch"),
    }


def sandbox_command_v06(
    *,
    runtime: str,
    image: str,
    workspace: Path,
    command: list[str],
    memory: str,
    cpus: float,
    pids_limit: int,
) -> list[str]:
    env = {
        "HOME": "/tmp/pcs-home",
        "TZ": "UTC",
        "LANG": "C",
        "LC_ALL": "C",
        "PYTHONHASHSEED": "0",
        "PYTHONUTF8": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
        "SOURCE_DATE_EPOCH": "0",
        "OMP_NUM_THREADS": "1",
        "OPENBLAS_NUM_THREADS": "1",
        "MKL_NUM_THREADS": "1",
        "NUMEXPR_NUM_THREADS": "1",
        "MPLBACKEND": "Agg",
    }
    out = [
        runtime,
        "run",
        "--rm",
        "--pull=never",
        "--network=none",
        "--read-only",
        "--cap-drop=ALL",
        "--security-opt",
        "no-new-privileges:true",
        "--pids-limit",
        str(pids_limit),
        "--memory",
        memory,
        "--cpus",
        str(cpus),
        "--hostname",
        "pcs-replay",
        "--tmpfs",
        "/tmp:rw,nosuid,nodev,size=256m",
        "-v",
        f"{workspace}:/workspace:rw",
        "-w",
        "/workspace",
    ]
    for key, value in sorted(env.items()):
        out.extend(["-e", f"{key}={value}"])
    out.append(image)
    out.extend(command)
    return out


def _run_oci_command_v06(
    *,
    runtime: str,
    image: str,
    workspace: Path,
    command: list[str],
    timeout_seconds: int,
    memory: str,
    cpus: float,
    pids_limit: int,
    allow_failure: bool = False,
) -> subprocess.CompletedProcess[str]:
    full = sandbox_command_v06(
        runtime=runtime,
        image=image,
        workspace=workspace,
        command=command,
        memory=memory,
        cpus=cpus,
        pids_limit=pids_limit,
    )
    try:
        proc = subprocess.run(
            full,
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        raise V06RuntimeReplayError(
            f"sandboxed replay command timed out after {timeout_seconds}s: "
            f"{command!r}"
        ) from exc
    if proc.returncode != 0 and not allow_failure:
        raise V06RuntimeReplayError(
            f"sandboxed replay command failed ({proc.returncode}): "
            f"{command!r}; stderr={proc.stderr[:MAX_STDIO_CHARS_V06]!r}"
        )
    return proc


_PYTHON_PROBE = r'''
import hashlib
import importlib.metadata as md
import json
import os
import platform
import sys

def sha(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()

packages=[]
for d in md.distributions():
    name=d.metadata.get("Name") or getattr(d,"name","")
    if not name:
        continue
    packages.append({
        "name":str(name),
        "version":str(d.version),
        "requires":sorted(str(x) for x in (d.requires or [])),
    })
packages.sort(key=lambda x:(x["name"].lower(),x["version"],x["requires"]))
os_release={}
try:
    with open("/etc/os-release",encoding="utf-8") as f:
        for line in f:
            if "=" in line:
                k,v=line.rstrip().split("=",1)
                os_release[k]=v.strip().strip('"')
except OSError:
    pass
exe=os.path.realpath(sys.executable)
print(json.dumps({
    "version":platform.python_version(),
    "implementation":platform.python_implementation(),
    "executable":exe,
    "executable_sha256":sha(exe),
    "system":platform.system(),
    "release":platform.release(),
    "architecture":platform.machine(),
    "os_release":os_release,
    "packages":packages,
},sort_keys=True,separators=(",",":")))
'''.strip()

_R_PROBE = (
    'ip <- installed.packages()[,c("Package","Version")]; '
    'for (i in seq_len(nrow(ip))) '
    'cat(ip[i,1], "\\t", ip[i,2], "\\n", sep="")'
)


def _parse_r_packages(text: str) -> list[dict[str, str]]:
    out = []
    for line in text.splitlines():
        if "\t" not in line:
            continue
        name, version = line.split("\t", 1)
        if name and version:
            out.append({"name": name, "version": version})
    return sorted(
        out,
        key=lambda x: (_normalized_name(x["name"]), x["version"]),
    )[:MAX_CAPTURED_PACKAGES_V06]


def _probe_realized_environment_v06(
    *,
    runtime: str,
    image: str,
    image_info: dict[str, Any],
    workspace: Path,
    timeout_seconds: int,
    memory: str,
    cpus: float,
    pids_limit: int,
) -> dict[str, Any]:
    python_proc = _run_oci_command_v06(
        runtime=runtime,
        image=image,
        workspace=workspace,
        command=["python", "-c", _PYTHON_PROBE],
        timeout_seconds=timeout_seconds,
        memory=memory,
        cpus=cpus,
        pids_limit=pids_limit,
        allow_failure=True,
    )
    python_info = None
    if python_proc.returncode == 0:
        try:
            python_info = json.loads(python_proc.stdout)
        except json.JSONDecodeError as exc:
            raise V06RuntimeReplayError(
                "Python environment probe returned invalid JSON"
            ) from exc
        packages = python_info.get("packages", [])
        if (
            not isinstance(packages, list)
            or len(packages) > MAX_CAPTURED_PACKAGES_V06
        ):
            raise V06RuntimeReplayError(
                "Python environment probe package set exceeds limit"
            )

    r_proc = _run_oci_command_v06(
        runtime=runtime,
        image=image,
        workspace=workspace,
        command=["Rscript", "-e", _R_PROBE],
        timeout_seconds=timeout_seconds,
        memory=memory,
        cpus=cpus,
        pids_limit=pids_limit,
        allow_failure=True,
    )
    r_packages = (
        _parse_r_packages(r_proc.stdout)
        if r_proc.returncode == 0
        else None
    )

    conda_proc = _run_oci_command_v06(
        runtime=runtime,
        image=image,
        workspace=workspace,
        command=["conda", "list", "--json"],
        timeout_seconds=timeout_seconds,
        memory=memory,
        cpus=cpus,
        pids_limit=pids_limit,
        allow_failure=True,
    )
    conda_packages = None
    if conda_proc.returncode == 0:
        try:
            conda_value = json.loads(conda_proc.stdout)
        except json.JSONDecodeError as exc:
            raise V06RuntimeReplayError(
                "Conda environment probe returned invalid JSON"
            ) from exc
        if (
            not isinstance(conda_value, list)
            or len(conda_value) > MAX_CAPTURED_PACKAGES_V06
        ):
            raise V06RuntimeReplayError(
                "Conda environment probe package set exceeds limit"
            )
        conda_packages = sorted(
            [
                {
                    "name": str(x.get("name")),
                    "version": str(x.get("version")),
                }
                for x in conda_value
                if isinstance(x, dict)
                and x.get("name")
                and x.get("version")
            ],
            key=lambda x: (_normalized_name(x["name"]), x["version"]),
        )

    tree = {
        "python": (python_info or {}).get("packages"),
        "r": r_packages,
        "conda": conda_packages,
    }
    realized = {
        "format": REALIZED_ENVIRONMENT_FORMAT_V06,
        "container": image_info,
        "os": {
            "system": (python_info or {}).get("system")
            or image_info.get("os"),
            "release": (python_info or {}).get("release"),
            "architecture": (python_info or {}).get("architecture")
            or image_info.get("architecture"),
            "os_release": (python_info or {}).get("os_release"),
        },
        "python": python_info,
        "r": {"packages": r_packages}
        if r_packages is not None
        else None,
        "conda": {"packages": conda_packages}
        if conda_packages is not None
        else None,
        "dependency_tree_fingerprint": _canonical_sha256(tree),
    }
    realized["realized_environment_sha256"] = _canonical_sha256(realized)
    return realized


def _dependency_map(
    packages: list[dict[str, Any]] | None,
) -> dict[str, str]:
    out: dict[str, str] = {}
    for row in packages or []:
        if not isinstance(row, dict):
            continue
        name, version = row.get("name"), row.get("version")
        if isinstance(name, str) and isinstance(version, str):
            out[_normalized_name(name)] = version
    return out


def compare_realized_environment_v06(
    signed: dict[str, Any],
    realized: dict[str, Any],
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    mismatches: list[str] = []

    py = (
        realized.get("python")
        if isinstance(realized.get("python"), dict)
        else None
    )
    actual_python_version = py.get("version") if py else None
    for row in signed.get("python", {}).get(
        "interpreter_constraints", []
    ):
        constraint = row.get("value") if isinstance(row, dict) else None
        if not isinstance(constraint, str):
            continue
        match = (
            isinstance(actual_python_version, str)
            and _satisfies_version_constraint(
                actual_python_version, constraint
            )
        )
        checks.append(
            {
                "kind": "python_interpreter_constraint",
                "expected": constraint,
                "actual": actual_python_version,
                "enforced": True,
                "match": bool(match),
            }
        )
        if not match:
            mismatches.append(
                f"Python interpreter {actual_python_version!r} "
                f"does not satisfy {constraint!r}"
            )

    ecosystem_specs = [
        (
            "python",
            signed.get("python", {}).get("dependencies", []),
            (py or {}).get("packages"),
        ),
        (
            "r",
            signed.get("r", {}).get("dependencies", []),
            (realized.get("r") or {}).get("packages")
            if isinstance(realized.get("r"), dict)
            else None,
        ),
        (
            "conda",
            signed.get("conda", {}).get("dependencies", []),
            (realized.get("conda") or {}).get("packages")
            if isinstance(realized.get("conda"), dict)
            else None,
        ),
    ]

    expected_projection: list[str] = []
    actual_projection: list[str] = []
    for ecosystem, declared, installed in ecosystem_specs:
        installed_map = _dependency_map(installed)
        for dep in declared if isinstance(declared, list) else []:
            if (
                not isinstance(dep, dict)
                or not isinstance(dep.get("name"), str)
            ):
                continue
            name = _normalized_name(dep["name"])
            source_kind = str(dep.get("source_kind", ""))
            optional = (
                source_kind.startswith("pyproject_optional:")
                or source_kind == "pipfile_lock:develop"
            )
            actual = installed_map.get(name)
            exact = (
                dep.get("exact_pin") is True
                and isinstance(dep.get("version"), str)
            )
            enforced = not optional
            if exact:
                match = actual == dep["version"]
                if enforced:
                    expected_projection.append(
                        f"{ecosystem}:{name}=={dep['version']}"
                    )
                    actual_projection.append(
                        f"{ecosystem}:{name}=={actual}"
                    )
            else:
                match = actual is not None
            checks.append(
                {
                    "kind": f"{ecosystem}_dependency",
                    "name": dep["name"],
                    "expected_version": dep.get("version"),
                    "actual_version": actual,
                    "exact_pin": exact,
                    "source_kind": source_kind,
                    "enforced": enforced,
                    "match": bool(match),
                }
            )
            if enforced and not match:
                mismatches.append(
                    f"{ecosystem} dependency {dep['name']!r} "
                    f"expected {dep.get('version')!r}, realized {actual!r}"
                )

    expected_projection = sorted(set(expected_projection))
    actual_projection = sorted(set(actual_projection))
    projection = {
        "expected_sha256": _canonical_sha256(expected_projection),
        "realized_sha256": _canonical_sha256(actual_projection),
        "expected_entries": len(expected_projection),
        "match": expected_projection == actual_projection,
        "enforced": bool(expected_projection),
    }
    if projection["enforced"] and not projection["match"]:
        mismatches.append(
            "exact dependency projection fingerprint differs from signed contract"
        )

    runtime_expectations = signed.get("runtime_expectations")
    if not isinstance(runtime_expectations, dict):
        runtime_expectations = {}

    expected_binary = runtime_expectations.get(
        "python_interpreter_sha256"
    )
    actual_binary = (py or {}).get("executable_sha256")
    checks.append(
        {
            "kind": "python_interpreter_binary_sha256",
            "expected": expected_binary,
            "actual": actual_binary,
            "enforced": isinstance(expected_binary, str),
            "match": (
                actual_binary == expected_binary
                if isinstance(expected_binary, str)
                else None
            ),
            "status": "compared"
            if isinstance(expected_binary, str)
            else "not_declared",
        }
    )
    if (
        isinstance(expected_binary, str)
        and actual_binary != expected_binary
    ):
        mismatches.append(
            "Python interpreter binary SHA-256 differs from signed expectation"
        )

    expected_os = runtime_expectations.get("os")
    expected_arch = runtime_expectations.get("architecture")
    actual_os = realized.get("os", {}).get("system")
    actual_arch = realized.get("os", {}).get("architecture")
    for kind, expected, actual in (
        ("os", expected_os, actual_os),
        ("architecture", expected_arch, actual_arch),
    ):
        checks.append(
            {
                "kind": kind,
                "expected": expected,
                "actual": actual,
                "enforced": isinstance(expected, str),
                "match": (
                    actual == expected
                    if isinstance(expected, str)
                    else None
                ),
                "status": "compared"
                if isinstance(expected, str)
                else "not_declared",
            }
        )
        if isinstance(expected, str) and actual != expected:
            mismatches.append(
                f"{kind} differs from signed expectation"
            )

    expected_image = runtime_expectations.get(
        "container_image_digest"
    )
    image_info = realized.get("container", {})
    repo_digests = (
        image_info.get("repo_digests", [])
        if isinstance(image_info, dict)
        else []
    )
    image_id = (
        image_info.get("image_id")
        if isinstance(image_info, dict)
        else None
    )
    image_matches = None
    if isinstance(expected_image, str):
        image_matches = (
            expected_image == image_id
            or expected_image in repo_digests
            or any(
                str(x).endswith(expected_image)
                for x in repo_digests
            )
        )
        if not image_matches:
            mismatches.append(
                "container image digest differs from signed expectation"
            )
    checks.append(
        {
            "kind": "container_image_digest",
            "expected": expected_image,
            "actual_image_id": image_id,
            "actual_repo_digests": repo_digests,
            "enforced": isinstance(expected_image, str),
            "match": image_matches,
            "status": "compared"
            if isinstance(expected_image, str)
            else "not_declared",
            "signed_container_bases": [
                stage.get("reference")
                for container in signed.get("containers", [])
                if isinstance(container, dict)
                for stage in container.get("stages", [])
                if isinstance(stage, dict)
                and stage.get("digest_pinned") is True
            ],
        }
    )

    expected_tree = runtime_expectations.get(
        "dependency_tree_fingerprint"
    )
    actual_tree = realized.get("dependency_tree_fingerprint")
    checks.append(
        {
            "kind": "full_dependency_tree_fingerprint",
            "expected": expected_tree,
            "actual": actual_tree,
            "enforced": isinstance(expected_tree, str),
            "match": (
                actual_tree == expected_tree
                if isinstance(expected_tree, str)
                else None
            ),
            "status": "compared"
            if isinstance(expected_tree, str)
            else "not_declared",
        }
    )
    if (
        isinstance(expected_tree, str)
        and actual_tree != expected_tree
    ):
        mismatches.append(
            "full dependency-tree fingerprint differs from signed expectation"
        )

    enforced = [
        row for row in checks if row.get("enforced") is True
    ]
    return {
        "valid": not mismatches,
        "errors": mismatches,
        "checks": checks,
        "exact_dependency_projection": projection,
        "enforced_checks": len(enforced),
        "advisory_or_undeclared_checks": len(checks) - len(enforced),
    }


def _load_verified_workspace_v06(
    workspace: Path,
    public_key_path: str | Path,
    expected_fingerprint: str | None,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    if not workspace.is_dir() or workspace.is_symlink():
        raise V06RuntimeReplayError(
            f"prepared replay workspace is not a regular directory: {workspace}"
        )
    try:
        metadata = strict_json_load(
            workspace / WORKSPACE_METADATA_FILE_V06
        )
    except (OSError, StrictJSONError) as exc:
        raise V06RuntimeReplayError(
            f"invalid replay workspace metadata: {exc}"
        ) from exc
    if (
        not isinstance(metadata, dict)
        or metadata.get("format")
        != "pcs-environment-workspace-v1"
    ):
        raise V06RuntimeReplayError(
            "unsupported replay workspace metadata format"
        )

    cert_name = metadata.get(
        "signed_certificate", SIGNED_CERTIFICATE_FILE_V06
    )
    sig_name = metadata.get(
        "certificate_signature", CERTIFICATE_SIGNATURE_FILE_V06
    )
    if not isinstance(cert_name, str) or not isinstance(sig_name, str):
        raise V06RuntimeReplayError(
            "workspace signed-certificate metadata is malformed"
        )
    cert_path = _workspace_path(workspace, cert_name)
    sig_path = _workspace_path(workspace, sig_name)
    if not cert_path.is_file() or not sig_path.is_file():
        raise V06RuntimeReplayError(
            "prepared workspace predates executable replay support; "
            "prepare it again so exact signed certificate bytes are embedded"
        )
    cert_bytes = cert_path.read_bytes()
    sig_bytes = sig_path.read_bytes()
    if (
        metadata.get("signed_certificate_sha256")
        != _sha256_bytes(cert_bytes)
    ):
        raise V06RuntimeReplayError(
            "embedded signed certificate hash differs from workspace metadata"
        )
    if (
        metadata.get("certificate_signature_sha256")
        != _sha256_bytes(sig_bytes)
    ):
        raise V06RuntimeReplayError(
            "embedded certificate signature hash differs from workspace metadata"
        )

    public_key = load_public_key_v06(public_key_path)
    verified = verify_signed_certificate_bytes_v06(
        cert_bytes,
        sig_bytes,
        public_key,
        expected_fingerprint=expected_fingerprint,
    )
    if not verified.get("valid"):
        raise V06RuntimeReplayError(
            "embedded certificate signature verification failed: "
            + "; ".join(
                str(x) for x in verified.get("errors", [])
            )
        )
    if (
        verified.get("certificate_semantic_hash")
        != metadata.get("certificate_semantic_hash")
    ):
        raise V06RuntimeReplayError(
            "workspace certificate semantic hash binding failed"
        )
    if (
        verified.get("certificate_integrity_hash")
        != metadata.get("certificate_integrity_hash")
    ):
        raise V06RuntimeReplayError(
            "workspace certificate integrity hash binding failed"
        )
    if (
        metadata.get("public_key_fingerprint")
        != verified.get("public_key_fingerprint")
    ):
        raise V06RuntimeReplayError(
            "workspace producer fingerprint binding failed"
        )

    certificate = parse_certificate_bytes_v06(cert_bytes)
    binding = certificate.get("environment")
    if not isinstance(binding, dict):
        raise V06RuntimeReplayError(
            "signed certificate lacks an environment contract"
        )
    try:
        environment = environment_from_binding_v06(binding)
    except V06EnvironmentReplayError as exc:
        raise V06RuntimeReplayError(str(exc)) from exc

    materialized = metadata.get("materialized_artifacts")
    if not isinstance(materialized, list):
        raise V06RuntimeReplayError(
            "workspace materialized_artifacts is missing"
        )
    certificate_artifacts = {
        x["id"]: x
        for x in certificate.get("artifacts", [])
        if isinstance(x, dict) and isinstance(x.get("id"), str)
    }
    seen: set[str] = set()
    for row in materialized:
        if not isinstance(row, dict):
            raise V06RuntimeReplayError(
                "workspace artifact metadata must be objects"
            )
        artifact_id = row.get("artifact_id")
        source_path = row.get("source_path")
        if (
            artifact_id in seen
            or artifact_id not in certificate_artifacts
        ):
            raise V06RuntimeReplayError(
                "workspace artifact identity set is inconsistent"
            )
        seen.add(artifact_id)
        cert_artifact = certificate_artifacts[artifact_id]
        if cert_artifact.get("source_path") != source_path:
            raise V06RuntimeReplayError(
                f"workspace source_path binding failed for {artifact_id!r}"
            )
        target = _workspace_path(workspace, source_path)
        if not target.is_file() or target.is_symlink():
            raise V06RuntimeReplayError(
                f"workspace artifact missing or symlinked: {source_path!r}"
            )
        digest = _sha256_path(target)
        if (
            digest != cert_artifact.get("sha256")
            or digest != row.get("sha256")
        ):
            raise V06RuntimeReplayError(
                f"workspace artifact hash mismatch before execution: "
                f"{artifact_id!r}"
            )
    return metadata, certificate, environment


def _copy_project_artifacts_v06(
    workspace: Path,
    run_root: Path,
    metadata: dict[str, Any],
    output_ids: set[str],
) -> dict[str, dict[str, Any]]:
    baseline: dict[str, dict[str, Any]] = {}
    for row in metadata["materialized_artifacts"]:
        artifact_id = row["artifact_id"]
        rel = row["source_path"]
        source = _workspace_path(workspace, rel)
        target = _workspace_path(run_root, rel)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        if artifact_id not in output_ids:
            baseline[artifact_id] = {
                "source_path": rel,
                "sha256": _sha256_path(target),
                "size": target.stat().st_size,
            }
    for row in metadata["materialized_artifacts"]:
        if row["artifact_id"] in output_ids:
            target = _workspace_path(
                run_root, row["source_path"]
            )
            if target.exists():
                target.unlink()
    return baseline


def _project_file_inventory(
    root: Path,
) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise V06RuntimeReplayError(
                "sandbox produced a symlink, which PCS refuses to follow: "
                f"{path}"
            )
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        out[rel] = {
            "size": path.stat().st_size,
            "sha256": _sha256_path(path),
        }
        if len(out) > MAX_OUTPUT_FILES_V06:
            raise V06RuntimeReplayError(
                "sandbox file-count limit exceeded"
            )
    return out


def _verify_run_outputs_v06(
    *,
    run_root: Path,
    plan: list[dict[str, Any]],
    baseline_inputs: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[str]]:
    errors: list[str] = []
    outputs: list[dict[str, Any]] = []
    output_paths: set[str] = set()
    total = 0
    for node in plan:
        for expected in node.get("output_contracts", []):
            rel = expected["source_path"]
            output_paths.add(rel)
            path = _workspace_path(run_root, rel)
            if not path.is_file() or path.is_symlink():
                outputs.append(
                    {
                        **expected,
                        "produced": False,
                        "actual_sha256": None,
                        "actual_size": None,
                        "match": False,
                    }
                )
                errors.append(
                    "declared workflow output was not regenerated: "
                    f"{rel!r}"
                )
                continue
            size = path.stat().st_size
            total += size
            if total > MAX_OUTPUT_TOTAL_BYTES_V06:
                raise V06RuntimeReplayError(
                    "regenerated workflow outputs exceed byte limit"
                )
            digest = _sha256_path(path)
            match = digest == expected.get("sha256")
            outputs.append(
                {
                    **expected,
                    "produced": True,
                    "actual_sha256": digest,
                    "actual_size": size,
                    "match": match,
                }
            )
            if not match:
                errors.append(
                    "regenerated workflow output hash differs from "
                    f"signed artifact: {rel!r}"
                )

    for original in baseline_inputs.values():
        path = _workspace_path(
            run_root, original["source_path"]
        )
        if not path.is_file() or path.is_symlink():
            errors.append(
                "signed non-output artifact was removed or replaced: "
                f"{original['source_path']!r}"
            )
            continue
        if (
            _sha256_path(path) != original["sha256"]
            or path.stat().st_size != original["size"]
        ):
            errors.append(
                "signed non-output artifact was mutated during replay: "
                f"{original['source_path']!r}"
            )

    declared_paths = {
        row["source_path"] for row in baseline_inputs.values()
    } | output_paths
    actual_files = _project_file_inventory(run_root)
    unexpected = sorted(set(actual_files) - declared_paths)
    if unexpected:
        errors.append(
            "sandbox created undeclared workspace files: "
            + ", ".join(repr(x) for x in unexpected[:16])
        )
    return sorted(
        outputs,
        key=lambda x: (x["source_path"], x["artifact_id"]),
    ), errors


def _execute_once_v06(
    *,
    workspace: Path,
    metadata: dict[str, Any],
    certificate: dict[str, Any],
    environment: dict[str, Any],
    plan: list[dict[str, Any]],
    runtime: str,
    image: str,
    image_info: dict[str, Any],
    timeout_seconds: int,
    memory: str,
    cpus: float,
    pids_limit: int,
) -> dict[str, Any]:
    output_ids = {
        row["artifact_id"]
        for node in plan
        for row in node.get("output_contracts", [])
    }
    with tempfile.TemporaryDirectory(
        prefix="pcs-v06-runtime-replay-"
    ) as tmp:
        run_root = Path(tmp)
        baseline_inputs = _copy_project_artifacts_v06(
            workspace, run_root, metadata, output_ids
        )
        node_results = []
        for index, node in enumerate(plan, start=1):
            command = _node_command_v06(node, index)
            proc = _run_oci_command_v06(
                runtime=runtime,
                image=image,
                workspace=run_root,
                command=command,
                timeout_seconds=timeout_seconds,
                memory=memory,
                cpus=cpus,
                pids_limit=pids_limit,
            )
            node_results.append(
                {
                    "node_id": node["id"],
                    "source_path": node["source_path"],
                    "source_kind": node["source_kind"],
                    "command": command,
                    "exit_code": proc.returncode,
                    "stdout_sha256": _sha256_bytes(
                        proc.stdout.encode(
                            "utf-8", errors="replace"
                        )
                    ),
                    "stderr_sha256": _sha256_bytes(
                        proc.stderr.encode(
                            "utf-8", errors="replace"
                        )
                    ),
                    "stdout_excerpt": proc.stdout[:4096],
                    "stderr_excerpt": proc.stderr[:4096],
                }
            )

        realized = _probe_realized_environment_v06(
            runtime=runtime,
            image=image,
            image_info=image_info,
            workspace=run_root,
            timeout_seconds=timeout_seconds,
            memory=memory,
            cpus=cpus,
            pids_limit=pids_limit,
        )
        comparison = compare_realized_environment_v06(
            environment, realized
        )
        outputs, output_errors = _verify_run_outputs_v06(
            run_root=run_root,
            plan=plan,
            baseline_inputs=baseline_inputs,
        )
        errors = [*comparison["errors"], *output_errors]
        return {
            "valid": not errors,
            "errors": errors,
            "nodes": node_results,
            "realized_environment": realized,
            "contract_comparison": comparison,
            "outputs": outputs,
        }


def _determinism_projection(
    run: dict[str, Any],
) -> dict[str, Any]:
    return {
        "realized_environment_sha256": run[
            "realized_environment"
        ]["realized_environment_sha256"],
        "outputs": [
            {
                "artifact_id": row["artifact_id"],
                "source_path": row["source_path"],
                "actual_sha256": row["actual_sha256"],
                "actual_size": row["actual_size"],
            }
            for row in run["outputs"]
        ],
    }


def execute_prepared_replay_workspace_v06(
    workspace: str | Path,
    public_key_path: str | Path,
    *,
    expected_fingerprint: str | None = None,
    image: str | None = None,
    sandbox_runtime: str = "auto",
    runs: int = 2,
    timeout_seconds: int = 300,
    memory: str = "2g",
    cpus: float = 2.0,
    pids_limit: int = 256,
) -> dict[str, Any]:
    if runs < 2 or runs > 5:
        raise V06RuntimeReplayError(
            "deterministic replay requires between 2 and 5 "
            "independent sandbox runs"
        )
    if timeout_seconds < 1 or timeout_seconds > 86400:
        raise V06RuntimeReplayError(
            "timeout_seconds must be in [1, 86400]"
        )
    if cpus <= 0 or cpus > 64:
        raise V06RuntimeReplayError(
            "cpus must be in (0, 64]"
        )
    if pids_limit < 16 or pids_limit > 32768:
        raise V06RuntimeReplayError(
            "pids_limit must be in [16, 32768]"
        )

    root = Path(workspace).resolve()
    metadata, certificate, environment = (
        _load_verified_workspace_v06(
            root, public_key_path, expected_fingerprint
        )
    )
    plan = workflow_execution_plan_v06(certificate)
    runtime = select_oci_runtime_v06(sandbox_runtime)
    selected_image = select_replay_image_v06(
        environment, image
    )
    image_info = _inspect_image_v06(runtime, selected_image)

    run_results = [
        _execute_once_v06(
            workspace=root,
            metadata=metadata,
            certificate=certificate,
            environment=environment,
            plan=plan,
            runtime=runtime,
            image=selected_image,
            image_info=image_info,
            timeout_seconds=timeout_seconds,
            memory=memory,
            cpus=cpus,
            pids_limit=pids_limit,
        )
        for _ in range(runs)
    ]
    projections = [
        _determinism_projection(run) for run in run_results
    ]
    deterministic = all(
        value == projections[0]
        for value in projections[1:]
    )
    errors = [
        f"run {index}: {error}"
        for index, run in enumerate(run_results, start=1)
        for error in run["errors"]
    ]
    if not deterministic:
        errors.append(
            "independent sandbox runs produced different "
            "output/environment fingerprints"
        )

    return {
        "format": RUNTIME_REPLAY_RECEIPT_FORMAT_V06,
        "valid": not errors,
        "errors": errors,
        "workspace_format": metadata.get("format"),
        "bundle_sha256": metadata.get("bundle_sha256"),
        "certificate_semantic_hash": certificate.get(
            "semantic_hash"
        ),
        "certificate_integrity_hash": certificate.get(
            "integrity_hash"
        ),
        "producer_public_key_fingerprint": metadata.get(
            "public_key_fingerprint"
        ),
        "sandbox": {
            "backend": Path(runtime).name,
            "image_requested": selected_image,
            "image_inspection": image_info,
            "network": "none",
            "pull_policy": "never",
            "root_filesystem_read_only": True,
            "capabilities_dropped": "ALL",
            "no_new_privileges": True,
            "memory": memory,
            "cpus": cpus,
            "pids_limit": pids_limit,
            "timeout_seconds_per_command": timeout_seconds,
        },
        "determinism": {
            "required_runs": runs,
            "identical_realized_environment_and_outputs": deterministic,
            "projection_sha256": [
                _canonical_sha256(x) for x in projections
            ],
        },
        "runs": run_results,
    }


def write_runtime_replay_receipt_v06(
    receipt: dict[str, Any],
    output: str | Path,
    *,
    overwrite: bool = False,
) -> Path:
    path = Path(output).resolve()
    if path.exists() and not overwrite:
        raise V06RuntimeReplayError(
            "refusing to overwrite existing runtime replay receipt: "
            f"{path}"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            receipt,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    return path
