from __future__ import annotations

import hashlib
import json
import re
import shlex
import tomllib
from pathlib import Path
from typing import Any


ENVIRONMENT_CAPTURE_FORMAT_V06 = "pcs-environment-capture-v1"
ENVIRONMENT_CONTRACT_NAMESPACE_V06 = "pcs-manifest-environment-contract-v1"
ENVIRONMENT_REPLAY_PLAN_FORMAT_V06 = "pcs-environment-replay-plan-v1"
MAX_ENVIRONMENT_SOURCE_BYTES_V06 = 8 * 1024 * 1024
MAX_DEPENDENCY_RECORDS_V06 = 1000
MAX_CONTAINER_STAGES_V06 = 64
MAX_UNRESOLVED_V06 = 256

_REQUIREMENT_NAME = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9_.-]*)")
_EXACT_PIN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*\s*==\s*[^;\s]+")
_PYTHON_VERSION_TOKEN = re.compile(r"(?i)(?:python[- ]?)?([0-9]+(?:\.[0-9]+){1,2})")
_FROM = re.compile(r"(?i)^FROM\s+(?:--platform=\S+\s+)?(\S+)(?:\s+AS\s+\S+)?\s*$")
_SAFE_ENV_FILES = {
    "pyproject.toml",
    "poetry.lock",
    "uv.lock",
    "Pipfile",
    "Pipfile.lock",
    "requirements.txt",
    "requirements-dev.txt",
    "requirements.lock",
    "constraints.txt",
    ".python-version",
    "runtime.txt",
    "environment.yml",
    "environment.yaml",
    "conda-lock.yml",
    "conda-lock.yaml",
    "renv.lock",
    "DESCRIPTION",
    "Dockerfile",
    "Containerfile",
    "flake.nix",
    "flake.lock",
}


class V06EnvironmentCaptureError(ValueError):
    pass


def _bounded(path: Path) -> bool:
    try:
        return path.is_file() and path.stat().st_size <= MAX_ENVIRONMENT_SOURCE_BYTES_V06
    except OSError:
        return False


def _safe_text(path: Path) -> str | None:
    if not _bounded(path):
        return None
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def _source_record(item: dict[str, Any], kind: str) -> dict[str, Any]:
    return {
        "artifact_id": item["artifact_id"],
        "path": item["path"],
        "kind": kind,
        "sha256": item["sha256"],
        "size": item["size"],
    }


def _dependency_record(
    *,
    ecosystem: str,
    name: str | None,
    raw: str,
    source_path: str,
    source_kind: str,
    exact_pin: bool = False,
    hash_pinned: bool = False,
    version: str | None = None,
) -> dict[str, Any]:
    return {
        "ecosystem": ecosystem,
        "name": name,
        "raw": raw[:512],
        "source_path": source_path,
        "source_kind": source_kind,
        "exact_pin": bool(exact_pin),
        "hash_pinned": bool(hash_pinned),
        "version": version,
    }


def _requirements(
    text: str,
    *,
    source_path: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    records: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    logical: list[str] = []
    carry = ""
    for raw in text.splitlines():
        line = raw.rstrip()
        if carry:
            line = carry + line.lstrip()
        if line.endswith("\\"):
            carry = line[:-1] + " "
            continue
        carry = ""
        logical.append(line)
    if carry:
        logical.append(carry)

    for line_no, raw in enumerate(logical, start=1):
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith(("-r ", "--requirement ", "-c ", "--constraint ")):
            unresolved.append(
                {
                    "type": "nested_requirement_reference",
                    "source_path": source_path,
                    "line": line_no,
                    "raw": stripped[:512],
                }
            )
            continue
        if stripped.startswith(("-e ", "--editable ")):
            unresolved.append(
                {
                    "type": "editable_requirement",
                    "source_path": source_path,
                    "line": line_no,
                    "raw": stripped[:512],
                }
            )
            continue
        if stripped.startswith(("--index-url", "--extra-index-url", "--find-links")):
            unresolved.append(
                {
                    "type": "package_index_option",
                    "source_path": source_path,
                    "line": line_no,
                    "raw": stripped[:512],
                }
            )
            continue
        if "://" in stripped or stripped.startswith(("git+", "hg+", "svn+", "bzr+")):
            unresolved.append(
                {
                    "type": "direct_or_vcs_requirement",
                    "source_path": source_path,
                    "line": line_no,
                    "raw": stripped[:512],
                }
            )
        requirement_part = stripped.split(" --hash=", 1)[0].strip()
        match = _REQUIREMENT_NAME.match(requirement_part)
        name = match.group(1) if match else None
        exact = bool(_EXACT_PIN.match(requirement_part))
        hashes = "--hash=sha256:" in stripped
        version = None
        if exact:
            version = requirement_part.split("==", 1)[1].split(";", 1)[0].strip()
        records.append(
            _dependency_record(
                ecosystem="python",
                name=name,
                raw=stripped,
                source_path=source_path,
                source_kind="requirements",
                exact_pin=exact,
                hash_pinned=hashes,
                version=version,
            )
        )
        if len(records) >= MAX_DEPENDENCY_RECORDS_V06:
            unresolved.append(
                {
                    "type": "dependency_record_limit",
                    "source_path": source_path,
                    "limit": MAX_DEPENDENCY_RECORDS_V06,
                }
            )
            break
    return records, unresolved


def _pep508_name(raw: str) -> str | None:
    match = _REQUIREMENT_NAME.match(raw)
    return match.group(1) if match else None


def _parse_pyproject(
    text: str,
    *,
    source_path: str,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    declarations: dict[str, Any] = {
        "requires_python": [],
        "build_backend": None,
    }
    deps: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    try:
        obj = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        return declarations, deps, [
            {
                "type": "pyproject_parse_error",
                "source_path": source_path,
                "detail": str(exc)[:512],
            }
        ]

    project = obj.get("project")
    if isinstance(project, dict):
        requires_python = project.get("requires-python")
        if isinstance(requires_python, str):
            declarations["requires_python"].append(
                {"source_path": source_path, "value": requires_python}
            )
        for raw in project.get("dependencies", []) if isinstance(project.get("dependencies"), list) else []:
            if not isinstance(raw, str):
                continue
            deps.append(
                _dependency_record(
                    ecosystem="python",
                    name=_pep508_name(raw),
                    raw=raw,
                    source_path=source_path,
                    source_kind="pyproject_pep621",
                    exact_pin=bool(_EXACT_PIN.match(raw)),
                    version=(
                        raw.split("==", 1)[1].split(";", 1)[0].strip()
                        if "==" in raw
                        else None
                    ),
                )
            )
        optional = project.get("optional-dependencies")
        if isinstance(optional, dict):
            for group, values in sorted(optional.items()):
                if not isinstance(values, list):
                    continue
                for raw in values:
                    if isinstance(raw, str):
                        deps.append(
                            _dependency_record(
                                ecosystem="python",
                                name=_pep508_name(raw),
                                raw=raw,
                                source_path=source_path,
                                source_kind=f"pyproject_optional:{group}",
                                exact_pin=bool(_EXACT_PIN.match(raw)),
                                version=(
                                    raw.split("==", 1)[1].split(";", 1)[0].strip()
                                    if "==" in raw
                                    else None
                                ),
                            )
                        )

    build_system = obj.get("build-system")
    if isinstance(build_system, dict):
        backend = build_system.get("build-backend")
        if isinstance(backend, str):
            declarations["build_backend"] = backend

    poetry = obj.get("tool", {}).get("poetry") if isinstance(obj.get("tool"), dict) else None
    if isinstance(poetry, dict):
        poetry_deps = poetry.get("dependencies")
        if isinstance(poetry_deps, dict):
            for name, spec in sorted(poetry_deps.items()):
                if str(name).lower() == "python":
                    declarations["requires_python"].append(
                        {"source_path": source_path, "value": str(spec)}
                    )
                    continue
                if isinstance(spec, str):
                    raw = f"{name}{spec if spec.startswith(('=', '<', '>', '~', '^')) else ' '+spec}"
                    deps.append(
                        _dependency_record(
                            ecosystem="python",
                            name=str(name),
                            raw=raw,
                            source_path=source_path,
                            source_kind="poetry_declared",
                            exact_pin=str(spec).startswith("=="),
                            version=(str(spec)[2:] if str(spec).startswith("==") else None),
                        )
                    )
                elif isinstance(spec, dict):
                    version = spec.get("version")
                    deps.append(
                        _dependency_record(
                            ecosystem="python",
                            name=str(name),
                            raw=json.dumps(spec, sort_keys=True, separators=(",", ":")),
                            source_path=source_path,
                            source_kind="poetry_declared",
                            exact_pin=isinstance(version, str) and version.startswith("=="),
                            version=(version[2:] if isinstance(version, str) and version.startswith("==") else None),
                        )
                    )

    if len(deps) > MAX_DEPENDENCY_RECORDS_V06:
        deps = deps[:MAX_DEPENDENCY_RECORDS_V06]
        unresolved.append(
            {
                "type": "dependency_record_limit",
                "source_path": source_path,
                "limit": MAX_DEPENDENCY_RECORDS_V06,
            }
        )
    return declarations, deps, unresolved


def _lock_packages_toml(
    text: str,
    *,
    source_path: str,
    lock_kind: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    try:
        obj = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        return [], [
            {
                "type": "lockfile_parse_error",
                "source_path": source_path,
                "detail": str(exc)[:512],
            }
        ]
    packages = obj.get("package")
    if not isinstance(packages, list):
        return [], []
    out = []
    for pkg in packages[:MAX_DEPENDENCY_RECORDS_V06]:
        if not isinstance(pkg, dict):
            continue
        name, version = pkg.get("name"), pkg.get("version")
        if isinstance(name, str):
            out.append(
                _dependency_record(
                    ecosystem="python",
                    name=name,
                    raw=f"{name}=={version}" if isinstance(version, str) else name,
                    source_path=source_path,
                    source_kind=lock_kind,
                    exact_pin=isinstance(version, str),
                    hash_pinned=bool(pkg.get("files") or pkg.get("sdist") or pkg.get("wheels")),
                    version=version if isinstance(version, str) else None,
                )
            )
    unresolved = []
    if len(packages) > MAX_DEPENDENCY_RECORDS_V06:
        unresolved.append(
            {
                "type": "dependency_record_limit",
                "source_path": source_path,
                "limit": MAX_DEPENDENCY_RECORDS_V06,
            }
        )
    return out, unresolved


def _pipfile_lock(
    text: str,
    *,
    source_path: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    try:
        obj = json.loads(text)
    except json.JSONDecodeError as exc:
        return [], [
            {
                "type": "lockfile_parse_error",
                "source_path": source_path,
                "detail": str(exc)[:512],
            }
        ]
    out = []
    for section in ("default", "develop"):
        values = obj.get(section)
        if not isinstance(values, dict):
            continue
        for name, spec in sorted(values.items()):
            if len(out) >= MAX_DEPENDENCY_RECORDS_V06:
                break
            if isinstance(spec, str):
                version = spec[2:] if spec.startswith("==") else None
                hashes = False
                raw = spec
            elif isinstance(spec, dict):
                version_raw = spec.get("version")
                version = version_raw[2:] if isinstance(version_raw, str) and version_raw.startswith("==") else None
                hashes = bool(spec.get("hashes"))
                raw = json.dumps(spec, sort_keys=True, separators=(",", ":"))
            else:
                continue
            out.append(
                _dependency_record(
                    ecosystem="python",
                    name=name,
                    raw=raw,
                    source_path=source_path,
                    source_kind=f"pipfile_lock:{section}",
                    exact_pin=version is not None,
                    hash_pinned=hashes,
                    version=version,
                )
            )
    return out, []


def _renv_lock(
    text: str,
    *,
    source_path: str,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    try:
        obj = json.loads(text)
    except json.JSONDecodeError as exc:
        return {}, [], [
            {
                "type": "renv_parse_error",
                "source_path": source_path,
                "detail": str(exc)[:512],
            }
        ]
    r_version = None
    r = obj.get("R")
    if isinstance(r, dict) and isinstance(r.get("Version"), str):
        r_version = r["Version"]
    packages = obj.get("Packages")
    out = []
    if isinstance(packages, dict):
        for name, spec in sorted(packages.items()):
            if len(out) >= MAX_DEPENDENCY_RECORDS_V06:
                break
            version = spec.get("Version") if isinstance(spec, dict) else None
            source = spec.get("Source") if isinstance(spec, dict) else None
            repository = spec.get("Repository") if isinstance(spec, dict) else None
            raw = {
                "Version": version,
                "Source": source,
                "Repository": repository,
            }
            out.append(
                _dependency_record(
                    ecosystem="r",
                    name=name,
                    raw=json.dumps(raw, sort_keys=True, separators=(",", ":")),
                    source_path=source_path,
                    source_kind="renv_lock",
                    exact_pin=isinstance(version, str),
                    version=version if isinstance(version, str) else None,
                )
            )
    return {"version": r_version}, out, []


def _description(
    text: str,
    *,
    source_path: str,
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, str]],
]:
    fields: dict[str, str] = {}
    current = None
    for raw in text.splitlines():
        if raw.startswith((" ", "\t")) and current:
            fields[current] += " " + raw.strip()
            continue
        if ":" not in raw:
            continue
        key, value = raw.split(":", 1)
        current = key.strip()
        fields[current] = value.strip()
    deps = []
    r_versions: list[dict[str, str]] = []
    depends_value = fields.get("Depends", "")
    for part in depends_value.split(","):
        dep = part.strip()
        if dep.startswith("R ") or dep.startswith("R("):
            match = re.search(r"R\s*\(([^\)]+)\)", dep)
            if match:
                r_versions.append(
                    {
                        "source_path": source_path,
                        "value": match.group(1).strip(),
                    }
                )
    for field in ("Depends", "Imports", "Suggests", "LinkingTo"):
        value = fields.get(field)
        if not value:
            continue
        for raw in value.split(","):
            dep = raw.strip()
            if not dep:
                continue
            if dep.startswith("R "):
                continue
            match = _REQUIREMENT_NAME.match(dep)
            name = match.group(1) if match else None
            version_match = re.search(r"\(\s*==\s*([^\)]+)\)", dep)
            deps.append(
                _dependency_record(
                    ecosystem="r",
                    name=name,
                    raw=dep,
                    source_path=source_path,
                    source_kind=f"description:{field.lower()}",
                    exact_pin=bool(version_match),
                    version=version_match.group(1).strip() if version_match else None,
                )
            )
    unresolved = []
    if len(deps) > MAX_DEPENDENCY_RECORDS_V06:
        deps = deps[:MAX_DEPENDENCY_RECORDS_V06]
        unresolved.append(
            {
                "type": "dependency_record_limit",
                "source_path": source_path,
                "limit": MAX_DEPENDENCY_RECORDS_V06,
            }
        )
    return deps, unresolved, r_versions


def _python_version_text(text: str, *, source_path: str) -> list[dict[str, str]]:
    values = []
    for raw in text.splitlines():
        value = raw.strip()
        if not value or value.startswith("#"):
            continue
        match = _PYTHON_VERSION_TOKEN.search(value)
        if match:
            values.append({"source_path": source_path, "value": match.group(1)})
            break
    return values


def _conda_environment(
    text: str,
    *,
    source_path: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, str]]]:
    deps: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    py_versions: list[dict[str, str]] = []
    in_dependencies = False
    in_pip = False
    base_indent = None
    for line_no, raw in enumerate(text.splitlines(), start=1):
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip())
        if stripped == "dependencies:":
            in_dependencies = True
            base_indent = indent
            continue
        if not in_dependencies:
            continue
        if base_indent is not None and indent <= base_indent and not stripped.startswith("-"):
            in_dependencies = False
            continue
        if stripped in ("- pip:", "pip:"):
            in_pip = True
            continue
        if not stripped.startswith("-"):
            continue
        value = stripped[1:].strip()
        if not value:
            continue
        if in_pip and indent > (base_indent or 0):
            match = _REQUIREMENT_NAME.match(value)
            deps.append(
                _dependency_record(
                    ecosystem="python",
                    name=match.group(1) if match else None,
                    raw=value,
                    source_path=source_path,
                    source_kind="conda_environment:pip",
                    exact_pin=bool(_EXACT_PIN.match(value)),
                    version=(value.split("==", 1)[1] if "==" in value else None),
                )
            )
        else:
            in_pip = False
            name = re.split(r"[=<> ]", value, 1)[0]
            version = None
            exact = False
            if "=" in value and not any(op in value for op in (">", "<", "~", "!")):
                parts = value.split("=")
                if len(parts) >= 2 and parts[1]:
                    version = parts[1]
                    exact = True
            deps.append(
                _dependency_record(
                    ecosystem="conda",
                    name=name,
                    raw=value,
                    source_path=source_path,
                    source_kind="conda_environment",
                    exact_pin=exact,
                    version=version,
                )
            )
            if name.lower() == "python" and version:
                py_versions.append({"source_path": source_path, "value": version})
        if len(deps) >= MAX_DEPENDENCY_RECORDS_V06:
            unresolved.append(
                {
                    "type": "dependency_record_limit",
                    "source_path": source_path,
                    "limit": MAX_DEPENDENCY_RECORDS_V06,
                }
            )
            break
    return deps, unresolved, py_versions


def _dockerfile(text: str, *, source_path: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    logical = []
    carry = ""
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if carry:
            line = carry + line
        if line.endswith("\\"):
            carry = line[:-1] + " "
            continue
        carry = ""
        logical.append(line)
    stages = []
    package_commands = []
    unresolved = []
    for line_no, line in enumerate(logical, start=1):
        match = _FROM.match(line)
        if match:
            ref = match.group(1)
            dynamic = "$" in ref
            digest_pinned = "@sha256:" in ref and not dynamic
            tag = None
            if not digest_pinned and ":" in ref.rsplit("/", 1)[-1]:
                tag = ref.rsplit(":", 1)[-1]
            stages.append(
                {
                    "reference": ref,
                    "digest_pinned": digest_pinned,
                    "tag": tag,
                    "dynamic": dynamic,
                }
            )
            if dynamic:
                unresolved.append(
                    {
                        "type": "dynamic_container_base",
                        "source_path": source_path,
                        "line": line_no,
                        "reference": ref[:512],
                    }
                )
        upper = line.upper()
        if upper.startswith("RUN ") and any(
            token in line
            for token in (
                "pip install",
                "uv sync",
                "poetry install",
                "apt-get install",
                "apt install",
                "conda install",
                "mamba install",
                "renv::restore",
            )
        ):
            package_commands.append(line[:512])
    if len(stages) > MAX_CONTAINER_STAGES_V06:
        unresolved.append(
            {
                "type": "container_stage_limit",
                "source_path": source_path,
                "limit": MAX_CONTAINER_STAGES_V06,
            }
        )
        stages = stages[:MAX_CONTAINER_STAGES_V06]
    return {
        "source_path": source_path,
        "stages": stages,
        "all_base_images_digest_pinned": bool(stages)
        and all(stage["digest_pinned"] for stage in stages),
        "package_install_commands": package_commands[:64],
    }, unresolved


def _lock_kind(path: str) -> str | None:
    name = Path(path).name
    if name == "uv.lock":
        return "uv_lock"
    if name == "poetry.lock":
        return "poetry_lock"
    if name == "Pipfile.lock":
        return "pipfile_lock"
    if name in ("conda-lock.yml", "conda-lock.yaml"):
        return "conda_lock"
    if name == "renv.lock":
        return "renv_lock"
    if name == "flake.lock":
        return "nix_flake_lock"
    if name in ("requirements.lock",):
        return "requirements_lock"
    return None


def _hermeticity(
    *,
    sources: list[dict[str, Any]],
    dependencies: list[dict[str, Any]],
    containers: list[dict[str, Any]],
) -> str:
    kinds = {source["kind"] for source in sources}
    if containers and all(c["all_base_images_digest_pinned"] for c in containers):
        if kinds & {"uv_lock", "poetry_lock", "pipfile_lock", "conda_lock", "renv_lock", "nix_flake_lock"}:
            return "strongly_pinned"
        return "container_base_pinned"
    if kinds & {"conda_lock", "nix_flake_lock"}:
        return "strongly_pinned"
    if kinds & {"uv_lock", "poetry_lock", "pipfile_lock", "renv_lock"}:
        return "locked_application_dependencies"
    reqs = [d for d in dependencies if d["source_kind"] in {"requirements", "requirements_lock"}]
    if reqs and all(d["exact_pin"] and d["hash_pinned"] for d in reqs):
        return "hash_pinned_dependencies"
    if dependencies:
        return "declared_dependencies"
    return "environment_unspecified"


def _replay_plan(
    *,
    sources: list[dict[str, Any]],
    hermeticity: str,
    containers: list[dict[str, Any]],
) -> dict[str, Any]:
    by_kind: dict[str, list[str]] = {}
    for source in sources:
        by_kind.setdefault(source["kind"], []).append(source["path"])
    steps: list[dict[str, Any]] = []
    tools: set[str] = set()

    if containers:
        for container in containers:
            tools.add("docker-or-compatible-oci-builder")
            steps.append(
                {
                    "kind": "container_build",
                    "source_path": container["source_path"],
                    "command_template": (
                        f"docker build -f {shlex.quote(container['source_path'])} ."
                    ),
                    "network_required": True,
                    "executes_project_build_instructions": True,
                }
            )
    elif by_kind.get("nix_flake_lock") and any(source["path"] == "flake.nix" for source in sources):
        tools.add("nix")
        steps.append(
            {
                "kind": "nix_flake",
                "source_path": "flake.nix",
                "command_template": "nix develop --offline",
                "network_required": False,
                "executes_project_build_instructions": True,
            }
        )
    elif by_kind.get("conda_lock"):
        tools.add("conda-lock-compatible-installer")
        lock = sorted(by_kind["conda_lock"])[0]
        steps.append(
            {
                "kind": "conda_lock",
                "source_path": lock,
                "command_template": f"conda-lock install {shlex.quote(lock)}",
                "network_required": True,
                "executes_project_build_instructions": False,
            }
        )
    elif by_kind.get("uv_lock") and any(source["path"] == "pyproject.toml" for source in sources):
        tools.add("uv")
        steps.append(
            {
                "kind": "uv_sync",
                "source_path": "uv.lock",
                "command_template": "uv sync --frozen",
                "network_required": True,
                "executes_project_build_instructions": True,
            }
        )
    elif by_kind.get("poetry_lock") and any(source["path"] == "pyproject.toml" for source in sources):
        tools.add("poetry")
        steps.append(
            {
                "kind": "poetry_install",
                "source_path": "poetry.lock",
                "command_template": "poetry install --sync",
                "network_required": True,
                "executes_project_build_instructions": True,
            }
        )
    elif by_kind.get("pipfile_lock"):
        tools.add("pipenv")
        steps.append(
            {
                "kind": "pipenv_sync",
                "source_path": sorted(by_kind["pipfile_lock"])[0],
                "command_template": "pipenv sync",
                "network_required": True,
                "executes_project_build_instructions": False,
            }
        )
    else:
        req_sources = sorted(
            source["path"]
            for source in sources
            if source["kind"] in {"requirements", "requirements_lock"}
        )
        if req_sources:
            tools.add("python")
            first = req_sources[0]
            use_hashes = hermeticity == "hash_pinned_dependencies"
            steps.append(
                {
                    "kind": "pip_install",
                    "source_path": first,
                    "command_template": (
                        f"python -m pip install {'--require-hashes ' if use_hashes else ''}"
                        f"-r {shlex.quote(first)}"
                    ),
                    "network_required": True,
                    "executes_project_build_instructions": True,
                }
            )

    if by_kind.get("renv_lock") and not any(step["kind"] == "container_build" for step in steps):
        tools.add("R+renv")
        steps.append(
            {
                "kind": "renv_restore",
                "source_path": sorted(by_kind["renv_lock"])[0],
                "command_template": "R -e 'renv::restore(prompt = FALSE)'",
                "network_required": True,
                "executes_project_build_instructions": True,
            }
        )

    if by_kind.get("conda_environment") and not any(
        step["kind"] in {"container_build", "conda_lock"} for step in steps
    ):
        tools.add("conda-or-mamba")
        env_file = sorted(by_kind["conda_environment"])[0]
        steps.append(
            {
                "kind": "conda_environment",
                "source_path": env_file,
                "command_template": f"conda env create -f {shlex.quote(env_file)}",
                "network_required": True,
                "executes_project_build_instructions": False,
            }
        )

    return {
        "format": ENVIRONMENT_REPLAY_PLAN_FORMAT_V06,
        "hermeticity": hermeticity,
        "required_tools": sorted(tools),
        "steps": steps,
        "automatic_execution_permitted_by_pcs": False,
        "reason": (
            "PCS emits a reconstruction plan but does not execute environment or project "
            "installation/build commands during verification."
        ),
    }


def capture_environment_v06(
    project_root: str | Path,
    inventory: list[dict[str, Any]],
) -> dict[str, Any]:
    root = Path(project_root).resolve()
    inventory_by_path = {item["path"]: item for item in inventory}
    sources: list[dict[str, Any]] = []
    dependencies: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    python_requires: list[dict[str, str]] = []
    r_versions: list[dict[str, str]] = []
    containers: list[dict[str, Any]] = []

    def add_source(path: str, kind: str) -> dict[str, Any] | None:
        item = inventory_by_path.get(path)
        if item is None:
            return None
        if not any(existing["artifact_id"] == item["artifact_id"] for existing in sources):
            sources.append(_source_record(item, kind))
        return item

    candidate_paths = sorted(
        path
        for path in inventory_by_path
        if Path(path).name in _SAFE_ENV_FILES
        or Path(path).name.startswith("requirements")
        and Path(path).suffix.lower() in {".txt", ".in"}
    )

    for rel in candidate_paths:
        item = inventory_by_path[rel]
        path = root / rel
        name = Path(rel).name
        text = _safe_text(path)
        if text is None:
            unresolved.append(
                {
                    "type": "environment_source_unreadable_or_too_large",
                    "source_path": rel,
                    "limit": MAX_ENVIRONMENT_SOURCE_BYTES_V06,
                }
            )
            continue

        if name == "pyproject.toml":
            add_source(rel, "pyproject")
            decl, deps, issues = _parse_pyproject(text, source_path=rel)
            python_requires.extend(decl["requires_python"])
            dependencies.extend(deps)
            unresolved.extend(issues)
        elif name.startswith("requirements") and Path(rel).suffix.lower() in {".txt", ".in", ".lock"}:
            kind = "requirements_lock" if name.endswith(".lock") else "requirements"
            add_source(rel, kind)
            deps, issues = _requirements(text, source_path=rel)
            dependencies.extend(deps)
            unresolved.extend(issues)
        elif name in (".python-version", "runtime.txt"):
            add_source(rel, "python_version")
            python_requires.extend(_python_version_text(text, source_path=rel))
        elif name in ("uv.lock", "poetry.lock"):
            kind = _lock_kind(rel) or "python_lock"
            add_source(rel, kind)
            deps, issues = _lock_packages_toml(text, source_path=rel, lock_kind=kind)
            dependencies.extend(deps)
            unresolved.extend(issues)
        elif name == "Pipfile.lock":
            add_source(rel, "pipfile_lock")
            deps, issues = _pipfile_lock(text, source_path=rel)
            dependencies.extend(deps)
            unresolved.extend(issues)
        elif name == "Pipfile":
            add_source(rel, "pipfile")
            try:
                obj = tomllib.loads(text)
                requires = obj.get("requires")
                if isinstance(requires, dict):
                    py = requires.get("python_version") or requires.get("python_full_version")
                    if isinstance(py, str):
                        python_requires.append({"source_path": rel, "value": py})
            except tomllib.TOMLDecodeError as exc:
                unresolved.append(
                    {
                        "type": "pipfile_parse_error",
                        "source_path": rel,
                        "detail": str(exc)[:512],
                    }
                )
        elif name in ("environment.yml", "environment.yaml"):
            add_source(rel, "conda_environment")
            deps, issues, py = _conda_environment(text, source_path=rel)
            dependencies.extend(deps)
            unresolved.extend(issues)
            python_requires.extend(py)
        elif name in ("conda-lock.yml", "conda-lock.yaml"):
            add_source(rel, "conda_lock")
        elif name == "renv.lock":
            add_source(rel, "renv_lock")
            r_decl, deps, issues = _renv_lock(text, source_path=rel)
            if isinstance(r_decl.get("version"), str):
                r_versions.append({"source_path": rel, "value": r_decl["version"]})
            dependencies.extend(deps)
            unresolved.extend(issues)
        elif name == "DESCRIPTION":
            add_source(rel, "r_description")
            deps, issues, r_declared = _description(text, source_path=rel)
            dependencies.extend(deps)
            unresolved.extend(issues)
            r_versions.extend(r_declared)
        elif name in ("Dockerfile", "Containerfile"):
            add_source(rel, "containerfile")
            container, issues = _dockerfile(text, source_path=rel)
            containers.append(container)
            unresolved.extend(issues)
        elif name == "flake.nix":
            add_source(rel, "nix_flake")
        elif name == "flake.lock":
            add_source(rel, "nix_flake_lock")

    # Add environment lockfiles even when their internals are intentionally opaque.
    for rel in candidate_paths:
        kind = _lock_kind(rel)
        if kind and rel in inventory_by_path:
            add_source(rel, kind)

    dependencies = dependencies[:MAX_DEPENDENCY_RECORDS_V06]
    unresolved = unresolved[:MAX_UNRESOLVED_V06]
    sources.sort(key=lambda x: (x["path"], x["kind"]))
    dependencies.sort(
        key=lambda x: (
            x["ecosystem"],
            x["name"] or "",
            x["source_path"],
            x["raw"],
        )
    )
    python_requires = sorted(
        {json.dumps(x, sort_keys=True): x for x in python_requires}.values(),
        key=lambda x: (x["source_path"], x["value"]),
    )
    r_versions = sorted(
        {json.dumps(x, sort_keys=True): x for x in r_versions}.values(),
        key=lambda x: (x["source_path"], x["value"]),
    )

    hermeticity = _hermeticity(
        sources=sources,
        dependencies=dependencies,
        containers=containers,
    )
    plan = _replay_plan(
        sources=sources,
        hermeticity=hermeticity,
        containers=containers,
    )

    contract = {
        "format": ENVIRONMENT_CAPTURE_FORMAT_V06,
        "static_only": True,
        "network_accessed": False,
        "user_code_executed": False,
        "source_artifact_ids": sorted({source["artifact_id"] for source in sources}),
        "sources": sources,
        "python": {
            "interpreter_constraints": python_requires,
            "dependencies": [d for d in dependencies if d["ecosystem"] == "python"],
        },
        "r": {
            "interpreter_constraints": r_versions,
            "dependencies": [d for d in dependencies if d["ecosystem"] == "r"],
        },
        "conda": {
            "dependencies": [d for d in dependencies if d["ecosystem"] == "conda"],
        },
        "containers": containers,
        "hermeticity": hermeticity,
        "replay_plan": plan,
        "unresolved": unresolved,
        "summary": {
            "source_files": len(sources),
            "dependency_records": len(dependencies),
            "python_dependency_records": sum(1 for d in dependencies if d["ecosystem"] == "python"),
            "r_dependency_records": sum(1 for d in dependencies if d["ecosystem"] == "r"),
            "conda_dependency_records": sum(1 for d in dependencies if d["ecosystem"] == "conda"),
            "container_specs": len(containers),
            "unresolved_items": len(unresolved),
        },
    }
    contract["semantic_sha256"] = hashlib.sha256(
        json.dumps(contract, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    return contract


def environment_artifact_ids_v06(environment: dict[str, Any]) -> list[str]:
    return sorted(
        {
            source["artifact_id"]
            for source in environment.get("sources", [])
            if isinstance(source, dict) and isinstance(source.get("artifact_id"), str)
        }
    )


def environment_replay_plan_v06(environment: dict[str, Any]) -> dict[str, Any]:
    plan = environment.get("replay_plan")
    if not isinstance(plan, dict) or plan.get("format") != ENVIRONMENT_REPLAY_PLAN_FORMAT_V06:
        raise V06EnvironmentCaptureError("environment lacks a valid v0.6 replay plan")
    return plan



def write_environment_replay_plan_v06(
    environment: dict[str, Any],
    output: str | Path,
    *,
    overwrite: bool = False,
) -> Path:
    plan = environment_replay_plan_v06(environment)
    path = Path(output).resolve()
    if path.exists() and not overwrite:
        raise V06EnvironmentCaptureError(
            f"refusing to overwrite existing environment replay plan: {path}"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(plan, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return path



def render_environment_replay_script_v06(environment: dict[str, Any]) -> str:
    plan = environment_replay_plan_v06(environment)
    lines = [
        "#!/usr/bin/env sh",
        "set -eu",
        "",
        "# Generated by PCS from signed/static environment metadata.",
        "# REVIEW BEFORE EXECUTION: package managers and container builds may execute",
        "# arbitrary project/dependency installation code and may access the network.",
        "# PCS verification never runs this script automatically.",
        "",
    ]
    if not plan.get("steps"):
        lines.extend(
            [
                "echo 'PCS: no reconstructable environment strategy was detected.' >&2",
                "exit 2",
                "",
            ]
        )
        return "\n".join(lines)

    for index, step in enumerate(plan["steps"], start=1):
        command = step.get("command_template")
        lines.append(
            f"# Step {index}: {step.get('kind')} from {step.get('source_path')}"
        )
        lines.append(
            "# Network required: "
            + ("yes" if step.get("network_required") else "no")
        )
        lines.append(
            "# May execute project/build code: "
            + ("yes" if step.get("executes_project_build_instructions") else "no")
        )
        if isinstance(command, str) and command:
            lines.append(command)
        lines.append("")
    return "\n".join(lines)


def write_environment_replay_script_v06(
    environment: dict[str, Any],
    output: str | Path,
    *,
    overwrite: bool = False,
) -> Path:
    path = Path(output).resolve()
    if path.exists() and not overwrite:
        raise V06EnvironmentCaptureError(
            f"refusing to overwrite existing environment replay script: {path}"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        render_environment_replay_script_v06(environment),
        encoding="utf-8",
    )
    try:
        path.chmod(0o700)
    except OSError:
        pass
    return path
