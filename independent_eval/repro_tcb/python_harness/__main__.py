"""CLI: python -m independent_eval.repro_tcb.python_harness <command>."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Independent eval Workstream C harness")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_fix = sub.add_parser("materialize-fixtures", help="Write synthetic evidence fixtures + hash manifest")
    p_fix.add_argument("--target", type=Path, default=None)

    p_recon = sub.add_parser("reconstruct", help="Run reconstruction campaign")
    p_recon.add_argument("--output-dir", type=Path, default=None)

    p_atlas = sub.add_parser("tcb-atlas", help="Build TCB dependency atlas (read-only)")
    p_atlas.add_argument("--output", type=Path, default=None)

    p_audit = sub.add_parser("traceability", help="Audit claims report for evidence links")
    p_audit.add_argument("--report", type=Path, default=None)
    p_audit.add_argument("--output", type=Path, default=None)

    p_all = sub.add_parser("run-all", help="Materialize fixtures, reconstruct, atlas, audit")
    p_all.add_argument("--output-dir", type=Path, default=None)

    args = parser.parse_args(argv)

    if args.cmd == "materialize-fixtures":
        from .reconstruction import materialize_fixtures
        from .paths import FIXTURES, HASH_MANIFEST
        from .hashing import sha256_file

        digests = materialize_fixtures(args.target)
        # Include claims report hash once present.
        claims = FIXTURES / "claims" / "sample_claims_report.md"
        files = {f"evidence_bundle/{k}" if k != "evidence_canonical.zip" else k: v for k, v in digests.items()}
        if claims.is_file():
            files["claims/sample_claims_report.md"] = sha256_file(claims)
        manifest = {
            "format": "pcs-independent-eval-fixture-hashes-v1",
            "files": files,
        }
        HASH_MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps(manifest, indent=2, sort_keys=True))
        return 0

    if args.cmd == "reconstruct":
        from .reconstruction import run_full_campaign

        print(json.dumps(run_full_campaign(args.output_dir), indent=2, sort_keys=True))
        return 0

    if args.cmd == "tcb-atlas":
        from .tcb_atlas import write_atlas

        print(json.dumps(write_atlas(args.output), indent=2, sort_keys=True))
        return 0

    if args.cmd == "traceability":
        from .traceability import audit_report

        print(json.dumps(audit_report(args.report, output=args.output), indent=2, sort_keys=True))
        return 0

    if args.cmd == "run-all":
        from .reconstruction import materialize_fixtures, run_full_campaign
        from .tcb_atlas import write_atlas
        from .traceability import audit_report
        from .paths import FIXTURES, HASH_MANIFEST, RESULTS
        from .hashing import sha256_file

        out = args.output_dir or RESULTS
        digests = materialize_fixtures()
        claims = FIXTURES / "claims" / "sample_claims_report.md"
        files = {
            (f"evidence_bundle/{k}" if k != "evidence_canonical.zip" else k): v
            for k, v in digests.items()
        }
        if claims.is_file():
            files["claims/sample_claims_report.md"] = sha256_file(claims)
        manifest = {"format": "pcs-independent-eval-fixture-hashes-v1", "files": files}
        HASH_MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        summary = {
            "reconstruction": run_full_campaign(out),
            "tcb_atlas": write_atlas(out / "tcb_atlas.json"),
            "traceability": audit_report(output=out / "traceability_audit.json"),
            "fixture_hashes": manifest,
        }
        (out / "workstream_c_summary.json").write_text(
            json.dumps(
                {
                    "reconstruction_pass": summary["reconstruction"]["pass"],
                    "atlas_nodes": len(summary["tcb_atlas"]["graph"]["nodes"]),
                    "traceability_counts": summary["traceability"]["counts"],
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        print(json.dumps(summary["reconstruction"], indent=2, sort_keys=True))
        return 0 if summary["reconstruction"]["pass"] else 1

    return 2


if __name__ == "__main__":
    sys.exit(main())
