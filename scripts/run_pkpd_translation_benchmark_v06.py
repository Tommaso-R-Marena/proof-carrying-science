from __future__ import annotations

import argparse
import json

from pcs.pkpd_translation_benchmark_v06 import (
    V06PkpdTranslationBenchmarkError,
    run_pkpd_translation_benchmark_v06,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run the realistic synthetic PCS PK/PD grounded-translation benchmark."
        )
    )
    parser.add_argument(
        "-o",
        "--output",
        required=True,
        help="fresh benchmark workspace/output directory",
    )
    parser.add_argument(
        "--fixture",
        help="optional fixture directory override",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="replace an existing output directory",
    )
    args = parser.parse_args()

    try:
        report = run_pkpd_translation_benchmark_v06(
            args.output,
            fixture_root=args.fixture,
            overwrite=args.force,
        )
    except (OSError, V06PkpdTranslationBenchmarkError) as exc:
        print(
            json.dumps(
                {
                    "passed": False,
                    "error": f"{type(exc).__name__}: {exc}",
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 2

    print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
