import json
import tempfile
from pathlib import Path

import pytest

from pcs.kernel import verify_certificate, build_certificate, AssuranceError
from pcs.policy import load_policy, PolicyError
from pcs.adapters.pkpd import check_contract_file


def test_duplicate_certificate_key_is_rejected_before_replay():
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "certificate.json"
        path.write_text(
            '{"spec_version":"pcs-0.5","subject":"first","subject":"second"}',
            encoding="utf-8",
        )
        result = verify_certificate(path)
        assert result["valid"] is False
        assert any("duplicate JSON object key" in err for err in result["errors"])


def test_duplicate_manifest_key_is_rejected_before_certification():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        path = root / "manifest.json"
        path.write_text(
            '{"subject":"first","subject":"second","claims":[],"artifacts":[],"checks":[],"workflow":{"nodes":[]}}',
            encoding="utf-8",
        )
        with pytest.raises(AssuranceError, match="duplicate JSON object key"):
            build_certificate(path, root / "out")


def test_duplicate_policy_key_is_rejected():
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "policy.json"
        path.write_text(
            '{"policy_version":"pcs-acceptance-policy-v1","required_claims":{"C":["OPEN"]},"required_claims":{"C":["COMPUTATIONALLY_SUPPORTED"]}}',
            encoding="utf-8",
        )
        with pytest.raises(PolicyError, match="duplicate JSON object key"):
            load_policy(path)


def test_duplicate_pk_parameter_key_is_rejected():
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "model.json"
        path.write_text(
            '{"model_type":"one_compartment_iv_bolus","dose":{"value":100,"value":1,"unit":"mg"},"volume":{"value":20,"unit":"L"},"clearance":{"value":2,"unit":"L/h"},"time_unit":"h","concentration_unit":"mg/L"}',
            encoding="utf-8",
        )
        ok, details = check_contract_file(path)
        assert ok is False
        assert "duplicate JSON object key" in details.get("message", "")
