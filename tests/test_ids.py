"""Deterministic event identifiers (PRIMER A8, D-01)."""

from alligator import ids
from alligator.agt import AgtRow

ROW = AgtRow("Domitian", "-0.1430", "-0.2960", "0.1180", "81", "96", "fixed")


def test_the_id_is_stable():
    assert ids.event_id(ROW) == ids.event_id(ROW)


def test_the_id_starts_with_a_letter():
    """Cypher variable names may not start with a digit."""
    identifier = ids.event_id(ROW)
    assert identifier[0].isalpha()
    assert len(identifier) == ids.LENGTH + 1
    assert identifier.isalnum()


def test_trailing_zeros_are_part_of_the_input():
    """`0.0810` and `0.081` are the same number but not the same file."""
    padded = AgtRow("A", "0.0810", "0", "0", "1", "2", "fixed")
    short = AgtRow("A", "0.081", "0", "0", "1", "2", "fixed")
    assert ids.event_id(padded) != ids.event_id(short)


def test_surrounding_whitespace_is_not(root):
    """The reader strips it, so a right-aligned column cannot change an id."""
    from alligator.agt import read

    agt = read(root / "data" / "potterlimes" / "potterlimes.agt")
    plain = AgtRow("AlbLimes", "-0.226", "0.109", "-0.514", "97", "260", "fixed")
    assert ids.event_id(agt.rows[0]) == ids.event_id(plain)


def test_column_seven_does_not_change_the_id():
    """Which end floats is decided by the metadata block, not by column 7."""
    fixed = AgtRow("A", "0", "0", "0", "1", "2", "fixed")
    floating = AgtRow("A", "0", "0", "0", "1", "2", "floating")
    assert ids.event_id(fixed) == ids.event_id(floating)


def test_the_line_number_does_not_change_the_id():
    """Sorting the file must not renumber the events."""
    first = AgtRow("A", "0", "0", "0", "1", "2", "fixed", line_number=1)
    later = AgtRow("A", "0", "0", "0", "1", "2", "fixed", line_number=9)
    assert ids.event_id(first) == ids.event_id(later)


def test_different_rows_get_different_ids():
    rows = [
        AgtRow("A", "0", "0", "0", "1", "2", "fixed"),
        AgtRow("B", "0", "0", "0", "1", "2", "fixed"),
        AgtRow("A", "1", "0", "0", "1", "2", "fixed"),
        AgtRow("A", "0", "0", "0", "1", "3", "fixed"),
    ]
    assert len({ids.event_id(row) for row in rows}) == len(rows)


def test_random_ids_are_random_and_usable():
    generated = {ids.random_id() for _ in range(200)}
    assert len(generated) > 190
    assert all(one[0].isalpha() and one.isalnum() for one in generated)
