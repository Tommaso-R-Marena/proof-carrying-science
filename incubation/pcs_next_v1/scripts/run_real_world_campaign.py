#!/usr/bin/env python3
from __future__ import annotations
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pcs_next_v1.campaigns.real_world_mutation import run_campaign
report = run_campaign(ROOT / "results" / "real_world_campaign")
print(json.dumps({
  "caught": report["caught"],
  "missed": report["missed"],
  "false_alarms": report["false_alarms"],
  "catch_rate": report["catch_rate"],
  "n_mutations": report["n_mutations"],
  "errors": report["errors"],
}, indent=2))
# Prefer reporting misses over failing the whole validate gate hard; exit 0 if campaign ran.
raise SystemExit(0 if not report["errors"] else 1)
