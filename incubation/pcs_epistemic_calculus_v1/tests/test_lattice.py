from pcs_epistemic.lattice import EvidenceClass, discharges, le, meet


def test_non_promotion_computational_to_formal():
    assert le(EvidenceClass.COMPUTATIONAL, EvidenceClass.FORMAL) is False
    assert discharges(EvidenceClass.COMPUTATIONAL, EvidenceClass.FORMAL, accepted=True) is False


def test_formal_covers_computational():
    assert le(EvidenceClass.FORMAL, EvidenceClass.COMPUTATIONAL) is True


def test_provenance_never_scientific():
    assert le(EvidenceClass.PROVENANCE, EvidenceClass.FORMAL) is False
    assert le(EvidenceClass.PROVENANCE, EvidenceClass.EMPIRICAL) is False


def test_meet_heterogeneous_collapses_to_provenance():
    assert meet(EvidenceClass.FORMAL, EvidenceClass.EMPIRICAL) == EvidenceClass.PROVENANCE
