"""The AGT reader and writer (PRIMER A7)."""

import pytest

from alligator import agt as agt_module
from alligator.agt import AgtError, dumps, parse, read

HEAD = "#9999\n#true\n#0.365|0.149|0.145\n#data\n"
HEADER = "name\tx\ty\tz\tvon\tbis\tfixed\n"
ROW = "A\t0.1\t0.2\t0.3\t10\t20\tfixed"


def build(head: str = HEAD, header: str = HEADER, *rows: str) -> str:
    return head + header + "\n".join(rows or (ROW,))


def test_metadata_of_the_roman_file(root):
    agt = read(root / "data" / "romanempire" / "romanempire.agt")
    assert agt.floating_value == 9999.0
    assert agt.use_weights is True
    assert agt.weights == (1.0, 1.0, 1.0)
    assert len(agt) == 12
    assert agt.rows[0].name == "fruehkaiserzeitlich"
    assert agt.rows[-1].name == "DomitianConsulate2"


def test_metadata_of_the_limes_file(root):
    agt = read(root / "data" / "potterlimes" / "potterlimes.agt")
    assert agt.weights == (0.365, 0.149, 0.145)
    assert len(agt) == 8


def test_padded_numbers_are_stripped(root):
    """`ca_3Dcoordinates_4_2.agt` right-aligns its columns with spaces."""
    agt = read(root / "data" / "potterlimes" / "potterlimes.agt")
    assert agt.rows[0].y == "0.109"


def test_false_discards_line_three():
    agt = parse(build("#9999\n#false\n#0.365|0.149|0.145\n#data\n"))
    assert agt.weights == (1.0, 1.0, 1.0)


def test_crlf_is_accepted():
    agt = parse(build().replace("\n", "\r\n"))
    assert len(agt) == 1
    assert agt.rows[0].flag == "fixed"


def test_column_names_are_never_read():
    """`agt.md` says from/to/floating, the test data say von/bis/fixed."""
    english = "name\tx\ty\tz\tfrom\tto\tfloating\n"
    assert parse(build(HEAD, english)).rows[0].start == "10"


def test_header_must_have_seven_columns():
    with pytest.raises(AgtError, match="6 columns"):
        parse(build(HEAD, "name\tx\ty\tz\tvon\tbis\n"))


def test_data_line_must_have_seven_columns():
    with pytest.raises(AgtError, match="data line 1"):
        parse(build(HEAD, HEADER, "A\t0.1\t0.2\t0.3\t10\t20"))


def test_a_file_without_the_separator_is_rejected():
    with pytest.raises(AgtError, match="#data"):
        parse(HEADER + ROW)


def test_the_weights_flag_must_be_true_or_false():
    with pytest.raises(AgtError, match="true"):
        parse(build("#9999\n#yes\n#1|1|1\n#data\n"))


def test_three_weights_are_required():
    with pytest.raises(AgtError, match="three weights"):
        parse(build("#9999\n#true\n#1.0|1.0\n#data\n"))


def test_a_header_without_events_is_rejected():
    with pytest.raises(AgtError, match="no events"):
        parse(HEAD + HEADER)


@pytest.mark.parametrize("dataset", ["romanempire", "potterlimes"])
def test_round_trip(root, dataset):
    original = read(root / "data" / dataset / f"{dataset}.agt")
    assert parse(dumps(original)) == original


def test_the_writer_uses_lf_only(tmp_path, root):
    original = read(root / "data" / "romanempire" / "romanempire.agt")
    target = agt_module.write(original, tmp_path / "out.agt")
    assert b"\r" not in target.read_bytes()
    assert target.read_bytes().endswith(b"\n")
