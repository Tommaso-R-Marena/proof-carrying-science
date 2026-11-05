"""Reject identity substitutions before attempting the real operator process."""
import hashlib
import json

import pytest

from research.scientific_receiver_v1.full_profile import run


def test_untrusted_qualification_does_not_bootstrap_itself(tmp_path):
    (tmp_path / "qualification.json").write_text("{}")
    with pytest.raises(ValueError, match="operator-pinned"):
        run(tmp_path, "0" * 64, tmp_path / "out")
    assert not (tmp_path / "out").exists()


def test_environment_substitution_rejects_even_with_original_module_inventory(tmp_path):
    inventory = b'{"artifacts":[],"modules":0}'
    environment = b'{"LEAN_PATH":"/attacker/modules"}'
    q = {"module_artifacts_sha256": hashlib.sha256(inventory).hexdigest(),
         "environment_sha256": hashlib.sha256(b'{"LEAN_PATH":"/reviewed/modules"}').hexdigest()}
    raw = json.dumps(q).encode()
    (tmp_path / "qualification.json").write_bytes(raw)
    (tmp_path / "module-artifacts.json").write_bytes(inventory)
    (tmp_path / "environment.json").write_bytes(environment)
    with pytest.raises(ValueError, match="search environment"):
        run(tmp_path, hashlib.sha256(raw).hexdigest(), tmp_path / "out")
    assert not (tmp_path / "out").exists()
