"""The thirteen Allen relations (PRIMER, part C, step S1)."""

import itertools

import pytest

from alligator import allen

#: One representative pair of intervals per sign. Interval 1 first.
CASES = {
    "<": ((0, 1), (2, 3)),
    ">": ((2, 3), (0, 1)),
    "m": ((0, 1), (1, 2)),
    "mi": ((1, 2), (0, 1)),
    "o": ((0, 2), (1, 3)),
    "oi": ((1, 3), (0, 2)),
    "s": ((0, 1), (0, 2)),
    "si": ((0, 2), (0, 1)),
    "f": ((1, 2), (0, 2)),
    "fi": ((0, 2), (1, 2)),
    "d": ((1, 2), (0, 3)),
    "di": ((0, 3), (1, 2)),
    "=": ((0, 1), (0, 1)),
}

GRID = list(itertools.product(range(4), repeat=2))


@pytest.mark.parametrize("sign,intervals", CASES.items(), ids=list(CASES))
def test_each_sign_has_its_case(sign, intervals):
    (a1, b1), (a2, b2) = intervals
    assert allen.relation_signs(a1, b1, a2, b2) == (sign,)


@pytest.mark.parametrize("sign,intervals", CASES.items(), ids=list(CASES))
def test_the_converse_case_gives_the_converse_sign(sign, intervals):
    (a1, b1), (a2, b2) = intervals
    assert allen.first_sign(a2, b2, a1, b1) == allen.CONVERSE[sign]


def test_at_most_one_sign_holds_at_a_time():
    """The pipeline keeps only the first sign, which is safe only if it is alone."""
    for (a1, b1), (a2, b2) in itertools.product(GRID, repeat=2):
        signs = allen.relation_signs(a1, b1, a2, b2)
        assert len(signs) <= 1, ((a1, b1), (a2, b2), signs)


def test_the_converse_holds_across_the_whole_grid():
    for (a1, b1), (a2, b2) in itertools.product(GRID, repeat=2):
        there = allen.first_sign(a1, b1, a2, b2)
        back = allen.first_sign(a2, b2, a1, b1)
        assert back == (None if there is None else allen.CONVERSE[there])


def test_a_point_can_only_ever_equal():
    """Four Roman events are dated 69 to 69; they relate to nothing but each other."""
    for a2, b2 in GRID:
        sign = allen.first_sign(1, 1, a2, b2)
        assert sign in (None, "=")
        assert sign != "=" or (a2, b2) == (1, 1)


def test_an_interval_equals_itself():
    for a, b in GRID:
        assert allen.first_sign(a, b, a, b) == "="


def test_unrelated_intervals_have_no_sign():
    """A point inside a proper interval: no Allen relation holds."""
    assert allen.relation_signs(1, 1, 0, 3) == ()


def test_every_sign_has_a_property_and_a_description():
    assert set(allen.PROPERTIES) == set(allen.SIGNS)
    assert set(allen.DESCRIPTIONS) == set(allen.SIGNS)
    assert len(set(allen.PROPERTIES.values())) == len(allen.SIGNS)


def test_the_properties_are_owl_time():
    assert allen.property_of("di").endswith("#intervalContains")
    assert allen.property_of("mi").endswith("#intervalMetBy")
    with pytest.raises(KeyError):
        allen.property_of("DURINGi")
