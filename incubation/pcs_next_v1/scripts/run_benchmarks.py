#!/usr/bin/env python3
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pcs_next_v1.benchmarks.suite import write_report
report = write_report(ROOT / "results" / "benchmark_report.json")
print(report["metrics"])
