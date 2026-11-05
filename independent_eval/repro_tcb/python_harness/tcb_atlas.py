"""Task 13 — Trusted computing base dependency atlas.

Builds a machine-readable dependency graph for the assurance chain:

  source bytes → OS I/O → ZIP → crypto → Python → transcripts → Lean authority
  → policy → output

Each node is classified as one of:
  kernel-proved | executable-tested | cryptographically-assumed |
  externally-trusted | unresolved

This module performs a **read-only** audit of ``formal/`` and ``pcs/``. It never
modifies Lean sources or production packages.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Literal

from .environment import capture_host_environment, git_commit
from .hashing import sha256_file, sha256_json
from .paths import REPO_ROOT, RESULTS

TrustClass = Literal[
    "kernel-proved",
    "executable-tested",
    "cryptographically-assumed",
    "externally-trusted",
    "unresolved",
]


def _node(
    node_id: str,
    *,
    layer: str,
    trust_class: TrustClass,
    description: str,
    evidence: list[str] | None = None,
    sources: list[str] | None = None,
    lean_tcb_item: str | None = None,
) -> dict[str, Any]:
    return {
        "id": node_id,
        "layer": layer,
        "trust_class": trust_class,
        "description": description,
        "evidence": evidence or [],
        "sources": sources or [],
        "lean_tcb_item": lean_tcb_item,
    }


def _edge(src: str, dst: str, relation: str) -> dict[str, str]:
    return {"from": src, "to": dst, "relation": relation}


def _read_text(path: Path, limit: int = 200_000) -> str | None:
    if not path.is_file():
        return None
    try:
        return path.read_text(encoding="utf-8", errors="replace")[:limit]
    except OSError:
        return None


def _probe_paths(repo: Path) -> dict[str, Any]:
    """Read-only existence/hash probes of key formal and pcs artifacts."""
    candidates = [
        "formal/PCS/V2/TCB.lean",
        "formal/PCS/V2/Authority.lean",
        "formal/PCS/V2/SHA256.lean",
        "formal/PCS/V2/Ed25519.lean",
        "formal/PCS/V2/Zip.lean",
        "formal/PCS/V2/CanonicalArchive.lean",
        "pcs/canonical_zip_v06.py",
        "pcs/hashing.py",
        "pcs/signing_v06.py",
        "pcs/lean_authority_v06.py",
        "pcs/policy_v06.py",
        "pcs/verifier_zip_v06.py",
        "pcs/canonical_json.py",
        "lean-toolchain",
        "docs/SECURITY_AND_TRUST.md",
    ]
    probed: dict[str, Any] = {}
    for rel in candidates:
        path = repo / rel
        if path.is_file():
            probed[rel] = {
                "exists": True,
                "sha256": sha256_file(path),
                "bytes": path.stat().st_size,
            }
        else:
            probed[rel] = {"exists": False}
    return probed


def _parse_lean_tcb_status(repo: Path) -> dict[str, str]:
    """Extract ``tcbStatus`` mappings from ``formal/PCS/V2/TCB.lean`` (read-only)."""
    text = _read_text(repo / "formal/PCS/V2/TCB.lean")
    if not text:
        return {}
    mapping: dict[str, str] = {}
    for match in re.finditer(r"\|\s*\.(\w+)\s*=>\s*\.(\w+)", text):
        mapping[match.group(1)] = match.group(2)
    return mapping


def _map_lean_status(status: str | None) -> TrustClass:
    if status == "provedInLean":
        return "kernel-proved"
    if status == "leanSpecification":
        return "executable-tested"
    if status == "namedHypothesis":
        return "cryptographically-assumed"
    if status == "foundation":
        return "externally-trusted"
    return "unresolved"


def build_atlas(repo: Path | None = None) -> dict[str, Any]:
    root = repo or REPO_ROOT
    lean_status = _parse_lean_tcb_status(root)
    probes = _probe_paths(root)
    host = capture_host_environment(root)

    nodes = [
        _node(
            "source_bytes",
            layer="source",
            trust_class="externally-trusted",
            description="Exact delivered project/artifact bytes presented to the verifier.",
            evidence=["package member SHA-256 digests", "intake freeze hashes"],
            sources=["pcs/intake.py", "pcs/package_v06.py"],
        ),
        _node(
            "os_io",
            layer="os",
            trust_class="externally-trusted",
            description="Operating-system filesystem and process I/O delivering bytes into user space.",
            evidence=["docs/SECURITY_AND_TRUST.md current TCB list"],
            sources=["docs/SECURITY_AND_TRUST.md"],
            lean_tcb_item="filesystemOS",
        ),
        _node(
            "zip_archive",
            layer="archive",
            trust_class="cryptographically-assumed",
            description="ZIP decode / canonical ZIP_STORED archive subset used for handoff (ZipDecoderFaithful hypothesis).",
            evidence=[
                "formal/PCS/V2/Zip.lean (when present)",
                "pcs/canonical_zip_v06.py executable tests",
            ],
            sources=["formal/PCS/V2/Zip.lean", "pcs/canonical_zip_v06.py", "pcs/verifier_zip_v06.py"],
            lean_tcb_item="archiveExtractor",
        ),
        _node(
            "crypto_sha256",
            layer="crypto",
            trust_class="executable-tested",
            description="SHA-256 digests binding artifacts; Lean FIPS transcription + KATs; production hashlib correspondence hypothesized.",
            evidence=["formal/PCS/V2/SHA256.lean", "hashlib KATs / differential tests"],
            sources=["formal/PCS/V2/SHA256.lean", "pcs/hashing.py"],
            lean_tcb_item="sha256Impl",
        ),
        _node(
            "crypto_sha256_collision",
            layer="crypto",
            trust_class="cryptographically-assumed",
            description="Collision / second-preimage resistance appears only as an explicit named hypothesis.",
            evidence=["Sha256Collision disjuncts in formal/PCS/V2/TCB.lean"],
            sources=["formal/PCS/V2/TCB.lean"],
            lean_tcb_item="sha256Collision",
        ),
        _node(
            "crypto_ed25519",
            layer="crypto",
            trust_class="executable-tested",
            description="Ed25519 verify transcription (RFC 8032) with KATs; unforgeability remains a named hypothesis.",
            evidence=["formal/PCS/V2/Ed25519.lean", "pcs/signing_v06.py"],
            sources=["formal/PCS/V2/Ed25519.lean", "pcs/signing_v06.py"],
            lean_tcb_item="ed25519Impl",
        ),
        _node(
            "crypto_ed25519_unforgeability",
            layer="crypto",
            trust_class="cryptographically-assumed",
            description="NoForgery hypothesis for the trust-anchor public key.",
            evidence=["NoForgery in formal/PCS/V2/TCB.lean"],
            sources=["formal/PCS/V2/TCB.lean"],
            lean_tcb_item="ed25519Unforgeability",
        ),
        _node(
            "python_runtime",
            layer="python",
            trust_class="externally-trusted",
            description="CPython (or alternate) runtime executing the production verifier and replay helpers.",
            evidence=["docs/SECURITY_AND_TRUST.md", "pyproject.toml requires-python"],
            sources=["pcs", "pyproject.toml"],
            lean_tcb_item="pythonRuntime",
        ),
        _node(
            "python_canonical_json",
            layer="python",
            trust_class="kernel-proved",
            description="JCS parser/codec proved in Lean; production path differentially tested.",
            evidence=["parserCodec => provedInLean", "pcs/canonical_json.py tests"],
            sources=["pcs/canonical_json.py", "formal/PCS/V2/Canonical.lean"],
            lean_tcb_item="parserCodec",
        ),
        _node(
            "transcripts",
            layer="transcript",
            trust_class="executable-tested",
            description="Lean authority observation/result transcripts binding checker outcomes to archive bytes.",
            evidence=["pcs/lean_authority_v06.py transcript formats"],
            sources=["pcs/lean_authority_v06.py"],
        ),
        _node(
            "lean_authority",
            layer="lean",
            trust_class="kernel-proved",
            description="Lean acceptance kernel / authority path; theorems under formal/PCS/V2 gate production acceptance.",
            evidence=["formal/PCS/V2/Authority.lean", "formal/PCS/V2/TCB.lean tcbStatus"],
            sources=["formal/PCS/V2/Authority.lean", "formal/PCS/V2/TCB.lean", "pcs/lean_authority_v06.py"],
            lean_tcb_item="leanKernel",
        ),
        _node(
            "lean_kernel_foundation",
            layer="lean",
            trust_class="externally-trusted",
            description="Lean logical foundation (propext, Classical.choice, Quot.sound) is not proved inside PCS.",
            evidence=["#print axioms audits in formal reports"],
            sources=["formal/PCS/V2/TCB.lean"],
            lean_tcb_item="leanKernel",
        ),
        _node(
            "reviewer_policy",
            layer="policy",
            trust_class="externally-trusted",
            description="External reviewer acceptance policy supplied out of band; producer-valid bundles may still be rejected.",
            evidence=["pcs/policy_v06.py", "schemas/acceptance_policy.schema.json"],
            sources=["pcs/policy_v06.py", "docs/SECURITY_AND_TRUST.md"],
        ),
        _node(
            "verification_output",
            layer="output",
            trust_class="executable-tested",
            description="Verification receipts / ACCEPT-REJECT outcomes recorded for audit.",
            evidence=["verification receipt schema", "pcs verify-bundle receipts"],
            sources=["pcs/bundle_verify.py", "schemas/verification_receipt.schema.json"],
        ),
        _node(
            "production_refines_lean",
            layer="correspondence",
            trust_class="cryptographically-assumed",
            description="Hypothesis that production acceptance implies Lean acceptArchive; differentially tested on finite suites, not proved for arbitrary Python.",
            evidence=["ProductionRefinesLean"],
            sources=["formal/PCS/V2/TCB.lean"],
            lean_tcb_item="productionCorrespondence",
        ),
        _node(
            "scientific_predicate",
            layer="science",
            trust_class="externally-trusted",
            description="User-supplied Holds/Describes scientific meaning is outside the kernel.",
            evidence=["named hypothesis scientificPredicate"],
            sources=["formal/PCS/V2/TCB.lean"],
            lean_tcb_item="scientificPredicate",
        ),
        _node(
            "environment_reconstruction",
            layer="environment",
            trust_class="unresolved",
            description="v0.6 Lean model does not claim environment reconstruction fidelity; hermetic rebuild across hosts remains an engineering obligation.",
            evidence=["reconstructionFidelity => notApplicable in TCB.lean"],
            sources=["formal/PCS/V2/TCB.lean", "docs/REPRODUCIBILITY_ENVIRONMENT_V06.md"],
            lean_tcb_item="reconstructionFidelity",
        ),
    ]

    for node in nodes:
        missing: list[str] = []
        for src in node["sources"]:
            path = root / src
            if not path.exists():
                missing.append(src)
        node["missing_sources"] = missing
        # Align trust_class with extracted Lean status when available.
        item = node.get("lean_tcb_item")
        if item and item in lean_status:
            node["lean_tcb_status"] = lean_status[item]
            mapped = _map_lean_status(lean_status[item])
            node["lean_mapped_trust_class"] = mapped

    edges = [
        _edge("source_bytes", "os_io", "delivered_via"),
        _edge("os_io", "zip_archive", "reads_as"),
        _edge("zip_archive", "crypto_sha256", "binds_members_with"),
        _edge("zip_archive", "crypto_ed25519", "may_authenticate_with"),
        _edge("crypto_sha256", "crypto_sha256_collision", "relies_on"),
        _edge("crypto_ed25519", "crypto_ed25519_unforgeability", "relies_on"),
        _edge("zip_archive", "python_runtime", "checked_by_production"),
        _edge("python_runtime", "python_canonical_json", "executes"),
        _edge("python_runtime", "transcripts", "invokes_authority_producing"),
        _edge("transcripts", "lean_authority", "records"),
        _edge("lean_authority", "lean_kernel_foundation", "depends_on"),
        _edge("lean_authority", "production_refines_lean", "corresponds_via"),
        _edge("lean_authority", "reviewer_policy", "feeds"),
        _edge("reviewer_policy", "verification_output", "decides"),
        _edge("lean_authority", "scientific_predicate", "interprets_under"),
        _edge("environment_reconstruction", "python_runtime", "unresolved_gap_affects"),
    ]

    by_class: dict[str, list[str]] = {}
    for node in nodes:
        by_class.setdefault(node["trust_class"], []).append(node["id"])

    atlas: dict[str, Any] = {
        "format": "pcs-independent-eval-tcb-atlas-v1",
        "task": 13,
        "audit_mode": "read-only",
        "git_commit": git_commit(root),
        "lean_tcb_status_extracted": lean_status,
        "probes": probes,
        "environment": {
            "platform": host.get("platform"),
            "toolchains": host.get("toolchains"),
        },
        "graph": {"nodes": nodes, "edges": edges},
        "classification_index": by_class,
        "chain": [
            "source_bytes",
            "os_io",
            "zip_archive",
            "crypto_sha256",
            "crypto_ed25519",
            "python_runtime",
            "transcripts",
            "lean_authority",
            "reviewer_policy",
            "verification_output",
        ],
        "open_gaps": [
            "environment_reconstruction",
            "crypto_sha256_collision",
            "crypto_ed25519_unforgeability",
            "production_refines_lean",
            "os_io",
            "lean_kernel_foundation",
            "scientific_predicate",
        ],
    }
    atlas["atlas_sha256"] = sha256_json({k: v for k, v in atlas.items() if k != "atlas_sha256"})
    return atlas


def write_atlas(output: Path | None = None, repo: Path | None = None) -> dict[str, Any]:
    atlas = build_atlas(repo)
    out = output or (RESULTS / "tcb_atlas.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(atlas, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    atlas["written_to"] = str(out)
    return atlas


if __name__ == "__main__":
    print(json.dumps(write_atlas(), indent=2, sort_keys=True))
