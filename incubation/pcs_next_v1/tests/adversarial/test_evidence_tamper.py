import json

from pcs_next_v1.core.errors import PcsNextError
from pcs_next_v1.trust.evidence_store import EvidenceStore


def test_payload_tamper_detected(tmp_path):
    store = EvidenceStore(tmp_path / "ev")
    store.commit("a", {"v": 1})
    store.commit("b", {"v": 2})
    store.verify_chain()
    ev = sorted((tmp_path / "ev").glob("evt-*.json"))[-1]
    body = json.loads(ev.read_text())
    body["payload"]["v"] = 999
    ev.write_text(json.dumps(body))
    try:
        store.verify_chain()
        assert False, "expected hash mismatch"
    except PcsNextError as exc:
        assert "mismatch" in str(exc).lower() or "HASH" in str(exc) or "hash" in str(exc).lower()
