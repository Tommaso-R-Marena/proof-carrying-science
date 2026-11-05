from heck.levels import Level, meet, meet_list


def test_meet_is_weakest_link():
    assert meet(Level.FORMAL, Level.EMPIRICAL) is Level.EMPIRICAL
    assert meet(Level.COMPUTATIONAL, Level.EMPIRICAL) is Level.EMPIRICAL
    assert meet(Level.PROVENANCE, Level.FORMAL) is Level.PROVENANCE


def test_meet_comm_assoc_idempotent():
    levels = list(Level)
    for a in levels:
        assert meet(a, a) is a
        for b in levels:
            assert meet(a, b) is meet(b, a)
            for c in levels:
                assert meet(meet(a, b), c) is meet(a, meet(b, c))


def test_meet_list_and_empty():
    assert meet_list([]) is Level.FORMAL
    assert meet_list([Level.FORMAL]) is Level.FORMAL
    assert meet_list([Level.FORMAL, Level.EMPIRICAL, Level.COMPUTATIONAL]) is Level.EMPIRICAL


def test_no_empirical_equals_formal():
    assert Level.EMPIRICAL is not Level.FORMAL
    assert Level.EMPIRICAL.at_most_empirical()
    assert not Level.FORMAL.at_most_empirical()
    assert not Level.COMPUTATIONAL.at_most_empirical()
