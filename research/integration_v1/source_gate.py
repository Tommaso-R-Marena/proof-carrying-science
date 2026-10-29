"""Read-only consolidated identity gate; never regenerates its expected profile."""
import ast
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
REPORTS = ROOT / "docs/integration/2026-10-18"
SUCCESSOR_PATH = "docs/research/post-integration-2026-10-18/receipt-source-profile-successor.json"
PREDECESSOR_COMMIT = "b916eec1b9d0d5c02c9cc19b070f7a47df5e5d87"
PREDECESSOR_PROFILE_SHA256 = "0610914446b24a6b2e7fb70cd385155531c42d65a95ec04b896d37c29f9d7297"
# These exact repair bytes require source review; the manifest cannot authorize
# arbitrary subsequent changes by replacing its own declared hashes.
RECEIPT_REPAIR_IDENTITIES = {
    "pcs/intake_verify_v06.py": (
        "af80a68f9f3a91f530a909a4db6cb3708a8f767299837d76c94780d8854eebec",
        "19763deafefee9179af0cc4b7d67fbd7355f33177c122657a9480a87ee2ddf20",
    ),
    "tests/test_intake_verify_v06.py": (
        "6b034c6324d127ccf35664108ed134dd3b1e1eade19c6963bf2f05d834bc797b",
        "923b6e345eff82ffdadceba06e0f7edb3215850bf12fe683d59b1839eeb5d31b",
    ),
    "pcs/receipt_contract_v06.py": (
        "35d7e8b53b7fe009b58812fc9f1abd2ec03645e7cabee9044a9e7a716522019e",
        "a5a9882dcd4b9cff872287c422ca2bd8fb00cb11c01f80afc6f0fe9b8c0dfeb1",
    ),
}

# Exact additional identities reviewed for the v11 integration candidate.
# Original predecessor and receipt successor bytes are retained separately.
RECEIPT_REPAIR_IDENTITIES.update({'.github/workflows/pcs-ci.yml': ('fd9f0a7de9c8a9af320b66d91c016cecf1862062c8bee7771448acbff0d71a0e', '825dda04ab678c1df4722b0d2ff2aa6441584bd97b6752b860613e2c10851a4a'), '.github/workflows/pcs-public-full-verification.yml': ('40e3cc3befb080f73439f80a2587e03324644c610f875d3c4bce1685319c9bf9', 'e983507a834c75f78e0f4034fc4b45191a46ff059142b6ad064913856d8f5e05'), 'pcs/transport_trace_kernel_v1.py': ('f1b994bb9152a3622e8475d58ae6d96f0f6b94a4bb1c64f01dd1743a1e5ed0ae', '7b1fd701ef7d05a3a5bfcad95ba1977591cc287928676bc8823ae313980d1280')})

# Only this non-authority differential driver may change imports. Its exact
# old/new bytes are pinned; every other protected main formal file stays fixed.
DIFFERENTIAL_DRIVER = 'formal/tools/LeanBuiltinCheck.lean'
RECEIPT_REPAIR_IDENTITIES[DIFFERENTIAL_DRIVER] = ('fb9e2e616cdf1abcb73d12b8902ba9d41b15bada6985d46341e5a6b2486b5d49', '78b201d6b9c1d19055b5b542ea13d8d465f57355d7688bdb92f78235986a9872')

# Exact dependency updates independently compared to current PR190/191/192 diffs.
RECEIPT_REPAIR_IDENTITIES.update({'.github/workflows/pcs-ci.yml': ('fd9f0a7de9c8a9af320b66d91c016cecf1862062c8bee7771448acbff0d71a0e', '6b3849a6ee927c5f4dd33e29e865e83320fcf386d346c90222d68dd36d4eb3ad'), '.github/workflows/pcs-public-full-verification.yml': ('40e3cc3befb080f73439f80a2587e03324644c610f875d3c4bce1685319c9bf9', '82cc23f2639e6621f79dc2d279c0561a241ef19ec7cf5eefb3f98c347b1fb496')})

# Exact reviewed documentation and fail-closed combined-source CI successor.
RECEIPT_REPAIR_IDENTITIES["README.md"] = ('0dcc965c85fb78f4e2521f6255b0010fc3212ddd63cac903ee8fdc236c4e0d5c', '75c933b85ceafd7b0a262b217d2b46856e4f57a47ecc0f4e356e8338c3b468c0')
RECEIPT_REPAIR_IDENTITIES[".github/workflows/pcs-public-full-verification.yml"] = ("40e3cc3befb080f73439f80a2587e03324644c610f875d3c4bce1685319c9bf9", 'cfbf20ad09638a79d2dc96595a91082ec5377a21b79dd2e64bfec9e86066b921')

RECEIPT_REPAIR_IDENTITIES["pcs/transport_trace_kernel_v1.py"] = ("f1b994bb9152a3622e8475d58ae6d96f0f6b94a4bb1c64f01dd1743a1e5ed0ae", '73878ddbdbc38ff71a5f522ab6b0fbbbe325e0a3b082146ecadf061f72382c0f')

GATE_PATH = "research/integration_v1/source_gate.py"
PREDECESSOR_GATE_SHA256 = "63b60bcec9538195f43506fed3102c37e960bb36654c57ee07e3d2452df6e625"


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate successor key: {key}")
        result[key] = value
    return result


def _successor_files(profile, tracked):
    """Apply one fixed, exact-byte successor; never accept caller profiles."""
    files = dict(profile["files"])
    path = ROOT / SUCCESSOR_PATH
    if not path.exists() and not path.is_symlink():
        return files, None
    if path.is_symlink() or not path.is_file() or SUCCESSOR_PATH not in tracked:
        raise ValueError("successor must be a tracked regular file")
    # The successor names reviewed source, not an editable working-tree grant.
    # Git HEAD and this gate remain trusted configuration, not an immutable root.
    raw_successor = path.read_bytes()
    committed = subprocess.check_output(
        ["git", "show", f"HEAD:{SUCCESSOR_PATH}"], cwd=ROOT
    )
    if raw_successor != committed:
        raise ValueError("successor differs from committed Git HEAD")
    predecessor = REPORTS / "SOURCE_PROFILE.json"
    if predecessor.is_symlink() or hashlib.sha256(predecessor.read_bytes()).hexdigest() != PREDECESSOR_PROFILE_SHA256:
        raise ValueError("successor predecessor profile bytes differ")
    successor = json.loads(raw_successor, object_pairs_hook=_unique_object)
    keys = {"format", "predecessor_commit", "predecessor_profile_sha256", "scope", "review_status", "files"}
    if not isinstance(successor, dict) or set(successor) != keys:
        raise ValueError("successor has unexpected fields")
    if (successor["format"] != "pcs-receipt-source-successor-v1"
            or successor["predecessor_commit"] != PREDECESSOR_COMMIT
            or successor["predecessor_profile_sha256"] != PREDECESSOR_PROFILE_SHA256
            or successor["scope"] != "SOURCE_IDENTITY_ONLY_NO_ACCEPTANCE_AUTHORITY"
            or successor["review_status"] not in {"pending_independent_review", "independently_reviewed"}):
        raise ValueError("successor identity or scope differs")
    entries = successor["files"]
    expected_paths = set(RECEIPT_REPAIR_IDENTITIES) | {GATE_PATH}
    if not isinstance(entries, dict) or set(entries) != expected_paths:
        raise ValueError("successor path allowlist differs")
    for name, entry in entries.items():
        if not isinstance(entry, dict) or set(entry) != {"old_sha256", "new_sha256", "mode", "reason"}:
            raise ValueError(f"successor entry shape differs: {name}")
        old, new = RECEIPT_REPAIR_IDENTITIES.get(name, (PREDECESSOR_GATE_SHA256, None))
        if entry["old_sha256"] != old or (new is not None and entry["new_sha256"] != new):
            raise ValueError(f"successor pinned identity differs: {name}")
        prior = files.get(name)
        if prior is not None and ((prior.get("baseline_formal_unchanged") and name != DIFFERENTIAL_DRIVER) or prior["sha256"] != old):
            raise ValueError(f"successor cannot override predecessor entry: {name}")
        file = ROOT / name
        if (name not in tracked or file.is_symlink() or not file.is_file()
                or file.stat().st_mode & 0o111 or entry["mode"] != "100644"
                or not isinstance(entry["reason"], str) or not entry["reason"]
                or hashlib.sha256(file.read_bytes()).hexdigest() != entry["new_sha256"]):
            raise ValueError(f"successor file identity or mode differs: {name}")
        files[name] = {**(prior or {}), "sha256": entry["new_sha256"]}
    return files, hashlib.sha256(raw_successor).hexdigest()


def check_profile():
    from scripts.audit_lean_source import audit
    profile = json.loads((REPORTS / "SOURCE_PROFILE.json").read_text())
    tracked = set(subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode().split("\0"))
    failures = []
    try:
        files, successor_sha256 = _successor_files(profile, tracked)
    except (ValueError, TypeError, OSError, subprocess.SubprocessError) as exc:
        failures.append(f"source successor invalid: {exc}")
        files, successor_sha256 = profile["files"], None
    for path, expected in files.items():
        file = ROOT / path
        if path not in tracked or not file.is_file() or file.is_symlink():
            failures.append(f"missing, untracked, or symlink source: {path}")
            continue
        if hashlib.sha256(file.read_bytes()).hexdigest() != expected["sha256"]:
            failures.append(f"source identity differs: {path}")
        if file.suffix == ".py":
            try:
                ast.parse(file.read_bytes(), filename=path)
            except (SyntaxError, UnicodeError) as exc:
                failures.append(f"Python source does not parse: {path}: {exc}")
        if file.suffix == ".sh" and not file.stat().st_mode & 0o111:
            failures.append(f"shell script lacks executable mode: {path}")
    modules = {p.relative_to(ROOT).as_posix() for p in (ROOT / "formal/PCS/V2").glob("ProofGated*.lean")}
    # Main also contains untrusted proof-task exercises and unsafe prover workers.
    # Their bytes are pinned above; they are outside production authority's
    # existing admission gate. Preserve that distinction instead of rewriting
    # historical tasks. All newly imported research Lean must pass this audit.
    failures.extend(audit([ROOT / path for path, item in profile["files"].items()
                           if path.endswith(".lean") and not item.get("baseline_formal_unchanged")]))
    if modules != set(profile["V7_modules"]):
        failures.append("V7 module discovery differs from the exact audited source profile")
    ledger = json.loads((REPORTS / "OPEN_PR_LEDGER.json").read_text())
    if len(ledger["pull_requests"]) != 32 or len({p["number"] for p in ledger["pull_requests"]}) != 32:
        failures.append("32-PR source ledger incomplete")
    return {"format": "pcs-consolidated-source-gate-v1", "passed": not failures,
            "files_checked": len(profile["files"]), "V7_modules": len(modules),
            "additional_files_checked": len(files) - len(profile["files"]),
            "successor_sha256": successor_sha256,
            "failures": failures, "production_authority": False,
            "admission_scope": "new research Lean; unchanged main authority separately requires scripts/verify_lean.sh"}


if __name__ == "__main__":
    result = check_profile()
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["passed"] else 1)
