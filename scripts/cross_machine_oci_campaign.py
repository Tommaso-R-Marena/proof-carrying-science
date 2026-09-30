from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from pcs.attest_v06 import attest_v06
from pcs.discover_v06 import (
    confirm_manifest_draft_v06,
    discover_project_v06,
    write_discovery_outputs_v06,
)
from pcs.environment_execute_v06 import (
    V06SandboxReplayError,
    execute_prepared_replay_workspace_v06,
)
from pcs.environment_workspace_v06 import prepare_verified_environment_workspace_v06
from pcs.scaffold import init_project
from pcs.signing import generate_keypair


FORMAT = "pcs-cross-machine-oci-campaign-v1"
ANALYSIS = r'''from __future__ import annotations
import json
from decimal import Decimal, getcontext
from pathlib import Path

getcontext().prec = 50
model = json.loads(Path("model.json").read_text(encoding="utf-8"))
dose = Decimal(str(model["dose"]["value"]))
vol = Decimal(str(model["volume"]["value"]))
cl = Decimal(str(model["clearance"]["value"]))
e0 = Decimal(str(model["pd"]["e0"]["value"]))
emax = Decimal(str(model["pd"]["emax"]["value"]))
ec50 = Decimal(str(model["pd"]["ec50"]["value"]))
rows = ["time,concentration,effect"]
for raw_t in ("0", "1", "2", "4", "8"):
    t = Decimal(raw_t)
    c = (dose / vol) * (-(cl / vol) * t).exp()
    effect = e0 + emax * c / (ec50 + c)
    rows.append(
        ",".join(
            [
                f"{t:.1f}",
                f"{c.quantize(Decimal('0.000000000001'))}",
                f"{effect.quantize(Decimal('0.000000000001'))}",
            ]
        )
    )
Path("predictions.csv").write_text("\n".join(rows) + "\n", encoding="utf-8", newline="\n")
'''


def run(argv: list[str], *, cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(argv, cwd=cwd, text=True, capture_output=True, check=False)
    if check and proc.returncode != 0:
        raise RuntimeError(
            f"command failed ({proc.returncode}): {argv!r}\n"
            f"stdout={proc.stdout[-8000:]}\nstderr={proc.stderr[-8000:]}"
        )
    return proc


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def json_write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def docker_arch() -> str:
    return run(["docker", "info", "--format", "{{.Architecture}}"]).stdout.strip()


def image_index_digest(tag: str) -> str:
    # buildx exposes the multi-architecture index digest. Using the index digest
    # allows the same signed Dockerfile to resolve natively on amd64 and arm64.
    proc = run(["docker", "buildx", "imagetools", "inspect", tag])
    match = re.search(r"(?m)^Digest:\s+(sha256:[0-9a-f]{64})\s*$", proc.stdout)
    if not match:
        raise RuntimeError(f"could not determine OCI index digest for {tag!r}")
    return match.group(1)


def image_runtime_identity(tag: str) -> tuple[str, str]:
    run(["docker", "pull", tag])
    pyver = run(
        ["docker", "run", "--rm", "--network=none", tag, "python", "-c", "import platform; print(platform.python_version())"]
    ).stdout.strip()
    pip_text = run(
        ["docker", "run", "--rm", "--network=none", tag, "python", "-m", "pip", "--version"]
    ).stdout.strip()
    match = re.match(r"pip\s+([^\s]+)", pip_text)
    if not match:
        raise RuntimeError(f"cannot parse pip version from {pip_text!r}")
    return pyver, match.group(1)


def variant_specs() -> list[dict[str, Any]]:
    return [
        {
            "id": "baseline_locked_bookworm",
            "tag": "python:3.12-slim-bookworm",
            "lock": "exact",
            "expected_contract_valid": True,
            "purpose": "baseline signed digest-pinned Debian bookworm image with exact pip pin",
        },
        {
            "id": "lock_range_bookworm",
            "tag": "python:3.12-slim-bookworm",
            "lock": "range",
            "expected_contract_valid": True,
            "purpose": "same image/output with range-constrained rather than exact package state",
        },
        {
            "id": "lock_bad_bookworm",
            "tag": "python:3.12-slim-bookworm",
            "lock": "bad",
            "expected_contract_valid": False,
            "purpose": "signed impossible exact pip pin; realized comparison must reject",
        },
        {
            "id": "os_bullseye_locked",
            "tag": "python:3.12-slim-bullseye",
            "lock": "exact",
            "expected_contract_valid": True,
            "purpose": "container OS/base variation: Debian bullseye instead of bookworm",
        },
        {
            "id": "provenance_full_bookworm",
            "tag": "python:3.12-bookworm",
            "lock": "exact",
            "expected_contract_valid": True,
            "purpose": "same OS/Python family with distinct full-image provenance",
        },
        {
            "id": "arch_amd64_pinned",
            "tag": "python:3.12-slim-bookworm",
            "lock": "exact",
            "platform": "linux/amd64",
            "expected_contract_valid": None,
            "purpose": "explicit signed linux/amd64 container-platform constraint",
        },
        {
            "id": "arch_arm64_pinned",
            "tag": "python:3.12-slim-bookworm",
            "lock": "exact",
            "platform": "linux/arm64",
            "expected_contract_valid": None,
            "purpose": "explicit signed linux/arm64 container-platform constraint",
        },
    ]


def requirements(lock: str, pip_version: str) -> str:
    if lock == "exact":
        return f"pip=={pip_version}\n"
    if lock == "bad":
        return "pip==0.0.0\n"
    major = int(pip_version.split(".", 1)[0])
    return f"pip>={major},<{major + 1}\n"


def build_project(root: Path, spec: dict[str, Any], image_ref: str, pyver: str, pipver: str) -> None:
    init_project(root, template="pkpd", subject=f"cross-machine-{spec['id']}")
    (root / "analysis.py").write_text(ANALYSIS, encoding="utf-8")
    (root / "requirements.txt").write_text(requirements(spec["lock"], pipver), encoding="utf-8")
    (root / ".python-version").write_text(pyver + "\n", encoding="utf-8")
    platform_clause = f" --platform={spec['platform']}" if spec.get("platform") else ""
    (root / "Dockerfile").write_text(f"FROM{platform_clause} {image_ref}\n", encoding="utf-8")

    # Produce the signed expected scientific output in the native producer image.
    # The Decimal-based model is chosen specifically to make cross-architecture
    # byte equality a meaningful falsifiable target rather than an assumed one.
    run(
        [
            "docker", "run", "--rm", "--network=none",
            "-v", f"{root}:/workspace", "-w", "/workspace",
            spec["tag"], "python", "analysis.py",
        ]
    )


def produce(output: Path) -> dict[str, Any]:
    if shutil.which("docker") is None:
        raise RuntimeError("Docker is required")
    output.mkdir(parents=True, exist_ok=False)
    image_cache: dict[str, dict[str, str]] = {}
    variants = []

    for spec in variant_specs():
        tag = spec["tag"]
        if tag not in image_cache:
            digest = image_index_digest(tag)
            pyver, pipver = image_runtime_identity(tag)
            repo = tag.split(":", 1)[0]
            image_ref = f"{repo}@{digest}"
            # Ensure the exact digest reference is materialized in the local store.
            run(["docker", "pull", image_ref])
            image_cache[tag] = {
                "index_digest": digest,
                "image_ref": image_ref,
                "python_version": pyver,
                "pip_version": pipver,
            }
        ident = image_cache[tag]
        variant_dir = output / spec["id"]
        project = Path(tempfile.mkdtemp(prefix=f"pcs-producer-{spec['id']}-"))
        try:
            build_project(project, spec, ident["image_ref"], ident["python_version"], ident["pip_version"])
            report = discover_project_v06(project)
            draft = project / "pcs-manifest.draft.json"
            write_discovery_outputs_v06(
                report,
                manifest_output=draft,
                report_output=project / "pcs-discovery.json",
                overwrite=True,
            )
            manifest = project / "confirmed-manifest.json"
            confirm_manifest_draft_v06(
                draft,
                manifest,
                project_root=project,
                overwrite=True,
            )
            variant_dir.mkdir(parents=True)
            private = project.parent / f"{spec['id']}-private.pem"
            public = variant_dir / "producer-public.pem"
            fingerprint = generate_keypair(private, public)["fingerprint"]
            bundle = variant_dir / "study.pcs.zip"
            attested = attest_v06(
                manifest,
                bundle,
                private,
                public,
                expected_fingerprint=fingerprint,
            )
            if not attested.get("valid"):
                raise RuntimeError(f"attestation failed for {spec['id']}: {attested}")
            meta = {
                **spec,
                **ident,
                "producer_architecture": docker_arch(),
                "producer_host": platform.platform(),
                "producer_public_key_fingerprint": fingerprint,
                "bundle_sha256": sha256_file(bundle),
                "expected_predictions_sha256": sha256_file(project / "predictions.csv"),
            }
            json_write(variant_dir / "variant.json", meta)
            variants.append(meta)
        finally:
            shutil.rmtree(project, ignore_errors=True)
            try:
                private.unlink()
            except (OSError, UnboundLocalError):
                pass

    campaign = {
        "format": FORMAT,
        "phase": "producer",
        "producer_host": platform.platform(),
        "producer_machine": platform.machine(),
        "producer_docker_arch": docker_arch(),
        "variants": variants,
    }
    json_write(output / "campaign.json", campaign)
    return campaign


def host_identity(machine_id: str) -> dict[str, Any]:
    os_release = {}
    try:
        for line in Path("/etc/os-release").read_text(encoding="utf-8").splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                os_release[k] = v.strip().strip('"')
    except OSError:
        pass
    return {
        "machine_id": machine_id,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "os_release": os_release,
        "docker_architecture": docker_arch(),
        "docker_version": run(["docker", "--version"]).stdout.strip(),
        "docker_server": run(["docker", "version", "--format", "{{json .Server}}"]).stdout.strip(),
        "python": platform.python_version(),
    }


def pre_pull(meta: dict[str, Any]) -> None:
    argv = ["docker", "pull"]
    if meta.get("platform"):
        argv += ["--platform", meta["platform"]]
    argv.append(meta["image_ref"])
    run(argv)


def replay_one(source: Path, result_root: Path, meta: dict[str, Any]) -> dict[str, Any]:
    variant_id = meta["id"]
    target = result_root / variant_id
    target.mkdir(parents=True)
    pre_pull(meta)
    workspace = target / "workspace"
    public = source / variant_id / "producer-public.pem"
    bundle = source / variant_id / "study.pcs.zip"
    fingerprint = meta["producer_public_key_fingerprint"]
    prepared = prepare_verified_environment_workspace_v06(
        bundle,
        workspace,
        public,
        expected_fingerprint=fingerprint,
    )
    execution_dir = target / "replay"
    record: dict[str, Any] = {
        "variant": variant_id,
        "prepared_valid": prepared.get("valid"),
        "expected_contract_valid": meta.get("expected_contract_valid"),
        "expected_predictions_sha256": meta["expected_predictions_sha256"],
    }
    try:
        result = execute_prepared_replay_workspace_v06(
            workspace,
            execution_dir,
            public,
            expected_fingerprint=fingerprint,
            determinism_runs=3,
        )
        record["execution_result"] = result
        record["valid"] = bool(result.get("valid"))
        receipt_path = execution_dir / "pcs-replay-execution.json"
        realized_path = execution_dir / "pcs-realized-environment.json"
        if receipt_path.is_file():
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            record["receipt_semantic_sha256"] = receipt.get("semantic_sha256")
            record["determinism"] = receipt.get("determinism")
            record["environment_comparison"] = receipt.get("environment_comparison")
            record["workflow_outputs"] = receipt.get("workflow_outputs")
        if realized_path.is_file():
            realized = json.loads(realized_path.read_text(encoding="utf-8"))
            record["realized_environment_semantic_sha256"] = realized.get("semantic_sha256")
            record["dependency_tree_sha256"] = realized.get("dependency_tree_sha256")
            record["container_image_digest"] = realized.get("container_image_digest")
            record["container_image"] = realized.get("container_image")
            record["platform"] = realized.get("platform")
        predictions = execution_dir / "outputs" / "predictions.csv"
        if predictions.is_file():
            record["realized_predictions_sha256"] = sha256_file(predictions)
            record["output_matches_producer"] = (
                record["realized_predictions_sha256"] == meta["expected_predictions_sha256"]
            )
    except Exception as exc:
        record["valid"] = False
        record["exception"] = f"{type(exc).__name__}: {exc}"
    json_write(target / "summary.json", record)
    return record


def replay(source: Path, output: Path, machine_id: str) -> dict[str, Any]:
    if shutil.which("docker") is None:
        raise RuntimeError("Docker is required")
    campaign = json.loads((source / "campaign.json").read_text(encoding="utf-8"))
    output.mkdir(parents=True, exist_ok=False)
    host = host_identity(machine_id)
    json_write(output / "host.json", host)
    records = []

    for meta in campaign["variants"]:
        records.append(replay_one(source, output, meta))

    # Provenance substitution attack: a signed container contract must never accept
    # a reviewer-supplied replacement image, even if that image is otherwise valid.
    baseline = next(x for x in campaign["variants"] if x["id"] == "baseline_locked_bookworm")
    base_dir = source / baseline["id"]
    attack_dir = output / "attack_provenance_substitution"
    attack_dir.mkdir()
    attack = {"expected": "reject", "rejected": False}
    try:
        pre_pull(baseline)
        workspace = attack_dir / "workspace"
        prepare_verified_environment_workspace_v06(
            base_dir / "study.pcs.zip",
            workspace,
            base_dir / "producer-public.pem",
            expected_fingerprint=baseline["producer_public_key_fingerprint"],
        )
        execute_prepared_replay_workspace_v06(
            workspace,
            attack_dir / "replay",
            base_dir / "producer-public.pem",
            expected_fingerprint=baseline["producer_public_key_fingerprint"],
            image="python:3.12-bookworm",
            determinism_runs=2,
        )
    except Exception as exc:
        attack["rejected"] = True
        attack["exception"] = f"{type(exc).__name__}: {exc}"
    json_write(attack_dir / "summary.json", attack)

    # Missing-base/no-pull attack: remove the signed base from the local image store.
    missing_dir = output / "attack_missing_signed_base"
    missing_dir.mkdir()
    missing = {"expected": "reject_without_registry_pull", "rejected": False}
    try:
        run(["docker", "image", "rm", "--force", baseline["tag"]], check=False)
        run(["docker", "image", "rm", "--force", baseline["image_ref"]], check=False)
        workspace = missing_dir / "workspace"
        prepare_verified_environment_workspace_v06(
            base_dir / "study.pcs.zip",
            workspace,
            base_dir / "producer-public.pem",
            expected_fingerprint=baseline["producer_public_key_fingerprint"],
        )
        execute_prepared_replay_workspace_v06(
            workspace,
            missing_dir / "replay",
            base_dir / "producer-public.pem",
            expected_fingerprint=baseline["producer_public_key_fingerprint"],
            determinism_runs=2,
        )
    except Exception as exc:
        missing["rejected"] = True
        missing["exception"] = f"{type(exc).__name__}: {exc}"
    json_write(missing_dir / "summary.json", missing)

    summary = {
        "format": FORMAT,
        "phase": "consumer",
        "host": host,
        "variants": records,
        "provenance_substitution_attack": attack,
        "missing_signed_base_attack": missing,
    }
    json_write(output / "summary.json", summary)
    return summary


def aggregate(input_root: Path, output: Path) -> dict[str, Any]:
    machine_summaries = []
    for path in sorted(input_root.rglob("summary.json")):
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(value, dict) and value.get("format") == FORMAT and value.get("phase") == "consumer":
            machine_summaries.append(value)
    machines = [x["host"]["machine_id"] for x in machine_summaries]
    by_variant: dict[str, list[dict[str, Any]]] = {}
    for machine in machine_summaries:
        for row in machine.get("variants", []):
            by_variant.setdefault(row["variant"], []).append(
                {
                    "machine_id": machine["host"]["machine_id"],
                    "host_os": machine["host"].get("os_release", {}).get("PRETTY_NAME"),
                    "host_machine": machine["host"].get("machine"),
                    "docker_architecture": machine["host"].get("docker_architecture"),
                    "valid": row.get("valid"),
                    "output_sha256": row.get("realized_predictions_sha256"),
                    "output_matches_producer": row.get("output_matches_producer"),
                    "dependency_tree_sha256": row.get("dependency_tree_sha256"),
                    "container_image_digest": row.get("container_image_digest"),
                    "platform": row.get("platform"),
                    "exception": row.get("exception"),
                }
            )
    comparisons = {}
    for variant, rows in sorted(by_variant.items()):
        hashes = sorted({r["output_sha256"] for r in rows if isinstance(r.get("output_sha256"), str)})
        comparisons[variant] = {
            "machines": len(rows),
            "valid_runs": sum(1 for r in rows if r.get("valid") is True),
            "unique_output_hashes": len(hashes),
            "output_hashes": hashes,
            "rows": rows,
        }

    aggregate = {
        "format": FORMAT,
        "phase": "aggregate",
        "machine_count": len(machine_summaries),
        "machines": machines,
        "comparisons": comparisons,
        "baseline_cross_machine_byte_identical": (
            comparisons.get("baseline_locked_bookworm", {}).get("unique_output_hashes") == 1
            and comparisons.get("baseline_locked_bookworm", {}).get("machines", 0) >= 2
        ),
    }
    json_write(output, aggregate)
    return aggregate


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("produce")
    p.add_argument("--output", required=True)
    r = sub.add_parser("replay")
    r.add_argument("--input", required=True)
    r.add_argument("--output", required=True)
    r.add_argument("--machine-id", required=True)
    a = sub.add_parser("aggregate")
    a.add_argument("--input", required=True)
    a.add_argument("--output", required=True)
    args = parser.parse_args()

    if args.command == "produce":
        value = produce(Path(args.output).resolve())
    elif args.command == "replay":
        value = replay(Path(args.input).resolve(), Path(args.output).resolve(), args.machine_id)
    else:
        value = aggregate(Path(args.input).resolve(), Path(args.output).resolve())
    print(json.dumps(value, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
