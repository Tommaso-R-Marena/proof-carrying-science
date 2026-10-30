"""Bounded resource measurements for pathological verification inputs."""

from __future__ import annotations

import json
import resource
import time
import zipfile
from pathlib import Path
from typing import Any

from .paths import RESULTS


def _rss_kb() -> int:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss


def run_resource_bounds(work: Path) -> dict[str, Any]:
    work.mkdir(parents=True, exist_ok=True)
    measurements: list[dict[str, Any]] = []

    # Large but bounded JSON object graph for JCS
    from pcs.canonical_json import canonicalize_jcs, CanonicalJSONError

    for n in (100, 1000, 5000):
        obj = {f"k{i:05d}": i for i in range(n)}
        start_rss = _rss_kb()
        t0 = time.perf_counter()
        try:
            text = canonicalize_jcs(obj)
            ok = True
            err = None
            size = len(text)
        except CanonicalJSONError as exc:
            ok = False
            err = str(exc)
            size = 0
        elapsed = time.perf_counter() - t0
        measurements.append(
            {
                "id": f"jcs_object_{n}",
                "ok": ok,
                "error": err,
                "seconds": elapsed,
                "rss_kb_delta": max(0, _rss_kb() - start_rss),
                "output_bytes": size,
            }
        )

    # Nested arrays (bounded depth)
    for depth in (10, 50, 100):
        value: Any = []
        cur = value
        for _ in range(depth):
            nxt: list[Any] = []
            cur.append(nxt)
            cur = nxt
        t0 = time.perf_counter()
        start_rss = _rss_kb()
        try:
            text = canonicalize_jcs(value)
            ok = True
            err = None
            size = len(text)
        except Exception as exc:  # noqa: BLE001
            ok = False
            err = f"{type(exc).__name__}: {exc}"
            size = 0
        measurements.append(
            {
                "id": f"jcs_nested_array_depth_{depth}",
                "ok": ok,
                "error": err,
                "seconds": time.perf_counter() - t0,
                "rss_kb_delta": max(0, _rss_kb() - start_rss),
                "output_bytes": size,
            }
        )

    # Oversized ZIP member names / many members (bounded)
    for count in (50, 200):
        path = work / f"many_members_{count}.zip"
        t0 = time.perf_counter()
        start_rss = _rss_kb()
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED) as zf:
            for i in range(count):
                zf.writestr(f"m/{i:04d}.txt", b"x" * 16)
        try:
            from pcs.verifier_zip_v06 import load_package_zip_v06

            load_package_zip_v06(path)
            ok = True
            err = None
        except Exception as exc:  # noqa: BLE001
            ok = False
            err = f"{type(exc).__name__}: {exc}"
        measurements.append(
            {
                "id": f"zip_many_members_{count}",
                "ok": ok,
                "error": err,
                "seconds": time.perf_counter() - t0,
                "rss_kb_delta": max(0, _rss_kb() - start_rss),
                "output_bytes": path.stat().st_size,
            }
        )

    report = {
        "format": "pcs-independent-resource-bounds-v1",
        "measurement_count": len(measurements),
        "measurements": measurements,
        "limits": {
            "max_object_keys": 5000,
            "max_nesting_depth": 100,
            "max_zip_members": 200,
            "note": "Bounded synthetic inputs only; no external DoS.",
        },
        "risks": [
            "Large object key sorts are O(n log n) in key count.",
            "Deep nesting increases recursion/stack pressure in some parsers.",
            "Many ZIP members increase inventory work before authority checks.",
        ],
    }
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "resource_bounds.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return report
