from __future__ import annotations

import argparse
import json
from pathlib import Path

from .formal_check import check_formal
from .hf_secondary import run_hf_secondary
from .run import run_campaign
from .replay import replay_campaign


def main() -> int:
    p = argparse.ArgumentParser(
        description="Assurance Mirage v1: formal metric independence + real-model red team"
    )
    sub = p.add_subparsers(dest="command", required=True)

    f = sub.add_parser("formal")
    f.add_argument("out", type=Path)

    r = sub.add_parser("run")
    r.add_argument("weights", type=Path)
    r.add_argument("out", type=Path)
    r.add_argument("--max-cases", type=int, default=None)
    r.add_argument(
        "--model",
        default="Qwen/Qwen3-0.6B-GGUF",
        choices=["Qwen/Qwen3-0.6B-GGUF", "Qwen/Qwen3-1.7B-GGUF"],
    )

    h = sub.add_parser("hf-secondary")
    h.add_argument("out", type=Path)
    h.add_argument("--max-cases", type=int, default=5)

    q = sub.add_parser("replay")
    q.add_argument("capture", type=Path)
    q.add_argument("out", type=Path)

    a = p.parse_args()
    try:
        if a.command == "formal":
            result = check_formal(a.out)
        elif a.command == "run":
            result = run_campaign(
                a.weights, a.out, max_cases=a.max_cases, model_id=a.model
            )
        elif a.command == "hf-secondary":
            result = run_hf_secondary(a.out, max_cases=a.max_cases)
        else:
            result = replay_campaign(a.capture, a.out)
        print(json.dumps({"ok": True, "result_keys": sorted(result.keys())}, indent=2))
        return 0
    except (ValueError, OSError, KeyError, TypeError, AssertionError) as e:
        print(json.dumps({"ok": False, "error": str(e), "production_authority": False}))
        return 20


if __name__ == "__main__":
    raise SystemExit(main())
