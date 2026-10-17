from pcs_next_v1.trust.evidence_store import EvidenceStore
from pcs_next_v1.core.errors import PcsNextError
import pytest

def test_cas_and_chain(tmp_path):
    store = EvidenceStore(tmp_path / "ev")
    store.commit("a", {"x": 1})
    with pytest.raises(PcsNextError):
        store.commit("b", {"x": 2}, expected_generation=0)
    store.commit("b", {"x": 2}, expected_generation=1)
    assert store.verify_chain()["ok"] is True
