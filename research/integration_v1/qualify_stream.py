"""Run one imported suite with isolated imports and fresh output destinations.

The original test logic and all its assertions execute. Historical result files
are not overwritten. Separate processes preserve independent harness namespaces.
"""
from __future__ import annotations
import argparse
import importlib
import json
import os
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[2]
STREAMS = {
    "121": ("independent_eval/protocol_adversarial", "."),
    "122": ("independent_eval/reviewer_adoption", "."),
    "123": ("independent_eval/repro_tcb", "."),
    "124": ("independent_eval/scientific_falsification", "."),
    "126": ("independent_eval/program_assurance", "."),
    "128": ("independent_eval/assurance_card", "."),
    "137": ("incubation/pcs_next_v1", "."),
    "139": ("incubation/pcs_certified_numerics_v1", "python"),
    "140": ("incubation/pcs_epistemic_calculus_v1", "."),
    "143": ("incubation/pcs_causal_laboratory_v1", "src"),
    "144": ("incubation/pcs_heterogeneous_compose_v1", "."),
    "147": ("incubation/pcs_conservation_algebra_v1", "python"),
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stream", required=True, choices=STREAMS)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    relative, import_root = STREAMS[args.stream]
    package = ROOT / relative
    sys.path[:0] = [str(package / import_root), str(ROOT)]
    os.chdir(package)
    # Subprocesses used by the original tests also receive the selected profile.
    os.environ["PYTHONPATH"] = os.pathsep.join((str(package / import_root), str(ROOT)))
    mappings = [(package / "results", out / "results")]
    if args.stream == "123":
        shutil.copytree(package / "fixtures", out / "fixtures")
        mappings.append((package / "fixtures", out / "fixtures"))
    remapped = []
    if (package / "python_harness").is_dir():
        for file in sorted((package / "python_harness").glob("*.py")):
            if file.stem not in ("__main__", "__init__"):
                importlib.import_module("python_harness." + file.stem)
        for old, new in mappings:
            new.mkdir(parents=True, exist_ok=True)
        for name, module in list(sys.modules.items()):
            if name == "python_harness" or name.startswith("python_harness."):
                for key, value in list(vars(module).items()):
                    if isinstance(value, Path):
                        for old, new in mappings:
                            if value == old or value.is_relative_to(old):
                                setattr(module, key, new / value.relative_to(old))
                                remapped.append({"module": name, "attribute": key})
                                break
    (out / "OUTPUT_RELOCATION.json").write_text(json.dumps(remapped, indent=2) + "\n")
    import pytest
    return pytest.main(["-q", "tests", f"--junitxml={out / 'tests.xml'}",
                        "-o", f"cache_dir={out / 'pytest-cache'}"])


if __name__ == "__main__":
    raise SystemExit(main())
