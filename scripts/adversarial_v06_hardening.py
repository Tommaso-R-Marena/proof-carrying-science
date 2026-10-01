from __future__ import annotations

import json
import shutil
import tempfile
import warnings
import zipfile
from pathlib import Path

from pcs.canonical_json import canonicalize_jcs, parse_jcs_json
from pcs.environment_replay_v06 import verify_environment_replay_v06
from pcs.verifier_zip_v06 import (
    V06BundleVerificationError,
    load_package_zip_v06,
    verify_package_zip_end_to_end_v06,
)
try:
    from scripts.run_golden_examples_v06 import build_golden_examples
except ModuleNotFoundError:
    # Direct execution ("python scripts/adversarial_v06_hardening.py")
    # puts scripts/ rather than the repository root on sys.path.
    from run_golden_examples_v06 import build_golden_examples


def _rewrite_zip(source: Path, dest: Path, transform) -> None:
    with zipfile.ZipFile(source, "r") as zin, zipfile.ZipFile(dest, "w", compression=zipfile.ZIP_STORED) as zout:
        for info in zin.infolist():
            raw = zin.read(info.filename)
            name, raw2 = transform(info.filename, raw)
            out = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            out.create_system = 3
            out.external_attr = 0o100644 << 16
            out.compress_type = zipfile.ZIP_STORED
            zout.writestr(out, raw2)


def campaign(workdir: str | Path) -> dict:
    root = Path(workdir).resolve()
    golden = build_golden_examples(root / "golden")
    cases = {c["name"]: root / "golden" / c["bundle"] for c in golden["cases"]}
    public = root / "golden" / "demo-public.pem"
    env_public = root / "golden" / "demo-public.pem"

    results = []

    def run(name, fn):
        try:
            rejected, detail = fn()
        except Exception as exc:
            rejected, detail = False, f"campaign error {type(exc).__name__}: {exc}"
        results.append({"attack": name, "rejected": bool(rejected), "detail": detail})

    def package_tamper(member: str, replacement: bytes):
        out = root / f"tamper-{member.replace('/', '-')}.zip"
        _rewrite_zip(cases["pkpd-supported"], out, lambda n, r: (n, replacement if n == member else r))
        checked = verify_package_zip_end_to_end_v06(out, public)
        return (not checked["valid"], checked.get("failed_stage") or checked.get("errors"))

    run("signed_certificate_byte_tamper", lambda: package_tamper("certificate.json", b"{}"))

    def add_member(name: str, raw: bytes = b"x"):
        out = root / ("namespace-" + name.replace("/", "-").replace("..", "dotdot") + ".zip")
        shutil.copyfile(cases["pkpd-supported"], out)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            with zipfile.ZipFile(out, "a", compression=zipfile.ZIP_STORED) as zf:
                zf.writestr(name, raw)
        try:
            load_package_zip_v06(out)
        except V06BundleVerificationError as exc:
            return True, str(exc)
        return False, "unsafe namespace accepted"

    run("zip_path_traversal", lambda: add_member("../escape.txt"))
    run("zip_duplicate_control_member", lambda: add_member("certificate.json", b"{}"))
    run("zip_casefold_collision", lambda: add_member("Certificate.json", b"{}"))
    run("zip_windows_reserved_name", lambda: add_member("artifacts/CON.txt"))
    run("zip_backslash_alias", lambda: add_member("artifacts\\alias.txt"))
    run("zip_non_nfc_name", lambda: add_member("artifacts/e\u0301.txt"))
    run("zip_trailing_dot_segment", lambda: add_member("artifacts/result."))
    run("normalized_index_byte_tamper", lambda: package_tamper("normalized/index.json", b"{}"))
    def unsigned_extra_member():
        out = root / "unsigned-extra-member.zip"
        shutil.copyfile(cases["pkpd-supported"], out)
        with zipfile.ZipFile(out, "a", compression=zipfile.ZIP_STORED) as zf:
            zf.writestr("notes.txt", b"not signed")
        checked = verify_package_zip_end_to_end_v06(out, public)
        return (not checked["valid"], checked.get("failed_stage") or checked.get("errors"))

    run("unsigned_extra_member", unsigned_extra_member)

    def environment_source_tamper():
        src = cases["environment-bound"]
        out = root / "environment-source-tamper.zip"
        with zipfile.ZipFile(src, "r") as zf:
            certificate = json.loads(zf.read("certificate.json").decode("utf-8"))
            env_artifacts = [
                row for row in certificate.get("artifacts", [])
                if row.get("source_path") == "requirements.txt"
            ]
        if not env_artifacts:
            return False, "environment bundle did not bind requirements.txt"
        target = env_artifacts[0]["path"]
        _rewrite_zip(src, out, lambda n, r: (n, b"cryptography==0.0.1\n" if n == target else r))
        checked = verify_package_zip_end_to_end_v06(out, env_public)
        return (not checked["valid"], checked.get("failed_stage") or checked.get("errors"))

    run("environment_source_drift_after_signing", environment_source_tamper)

    def forged_environment_proposition():
        src = cases["environment-bound"]
        with zipfile.ZipFile(src, "r") as zf:
            package_files = {n: zf.read(n) for n in zf.namelist() if not n.endswith("/")}
        certificate = json.loads(package_files["certificate.json"].decode("utf-8"))
        binding = certificate.get("environment")
        if not binding:
            return False, "environment-bound golden case had no environment binding"
        proposition = parse_jcs_json(binding["contract"]["proposition"])
        deps = proposition.get("python", {}).get("dependencies", [])
        if not deps:
            return False, "environment proposition had no Python dependencies"
        deps[0]["version"] = "999.999.999"
        deps[0]["raw"] = deps[0].get("name", "dependency") + "==999.999.999"
        binding["contract"]["proposition"] = canonicalize_jcs(proposition)
        checked = verify_environment_replay_v06(certificate, package_files)
        return (not checked["valid"], checked["errors"])

    run("fully_rehashed_style_false_environment_claim_at_replay_boundary", forged_environment_proposition)

    total = len(results)
    rejected = sum(1 for r in results if r["rejected"])
    return {
        "format": "pcs-v06-adversarial-hardening-v1",
        "attacks": total,
        "rejected": rejected,
        "false_accepts": total - rejected,
        "results": results,
    }


if __name__ == "__main__":
    with tempfile.TemporaryDirectory(prefix="pcs-v06-adversarial-") as td:
        result = campaign(td)
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result["false_accepts"] == 0 else 1)
