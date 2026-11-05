from pcs_next_v1.core.statuses import AssuranceStatus, weaker

def test_weaker():
    assert weaker(AssuranceStatus.REFUTED, AssuranceStatus.FORMALLY_VERIFIED) == AssuranceStatus.REFUTED
