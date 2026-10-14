import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("formal_environment_contract_v2", ROOT / "scripts/formal_environment_contract_v2.py")
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


def test_two_exact_versions_keep_the_historical_configuration_unchanged(tmp_path):
    assert gate.check_configuration(ROOT / "formal/lakefile.toml", gate.BASELINE_SHA256).startswith("exact_v2")
    snapshot = ROOT / "research/formal-integration-phase-v1/baseline-lakefile.toml.txt"
    assert gate.check_configuration(snapshot, gate.BASELINE_SHA256) == "exact_historical_configuration"


@pytest.mark.parametrize("mutation", ["old-library", "new-library", "new-flag", "extra-library"])
def test_changed_old_sources_or_unapproved_extension_are_rejected(tmp_path, mutation):
    raw = (ROOT / "formal/lakefile.toml").read_bytes()
    if mutation == "old-library":
        raw = raw.replace(b'name = "PCS"', b'name = "PCSChanged"', 1)
    elif mutation == "new-library":
        raw = raw.replace(b'name = "PCSConditionalRuntime"', b'name = "PCSAuthorityReplacement"')
    elif mutation == "new-flag":
        raw = raw.replace(b'"-M6000"', b'"-M40000"')
    else:
        raw += b'\n[[lean_lib]]\nname = "Unapproved"\n'
    altered = tmp_path / "lakefile.toml"
    altered.write_bytes(raw)
    with pytest.raises(ValueError, match="identity changed"):
        gate.check_configuration(altered, gate.BASELINE_SHA256)
