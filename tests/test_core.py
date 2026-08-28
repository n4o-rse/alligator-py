"""The core calculation, checked against the Java reference outputs.

This is what step S1 is finished by (PRIMER, part C): the same virtual years and
the same Allen matrix as the golden files, compared by name because every one of
the six reference files carries different random identifiers (PRIMER A8, D-01).
"""

import pytest

from alligator import agt as agt_module
from alligator.core import (
    AlligatorError,
    NoNeighbourError,
    calculate,
    calculate_file,
    distance,
    scale,
)

HEAD = "#9999\n#true\n#1.0|1.0|1.0\n#data\nname\tx\ty\tz\tvon\tbis\tfixed\n"


def build(*rows: str):
    return agt_module.parse(HEAD + "\n".join(rows))


# --------------------------------------------------------------------------
# against the golden files
# --------------------------------------------------------------------------
def test_the_event_order_is_the_file_order(romanempire, golden):
    assert list(romanempire.names) == golden["matrix_allen"][0][1:]


def test_the_allen_matrix_matches_the_reference(romanempire, golden):
    """Everything but the diagonal: self-relations are dropped (PRIMER A8, D-13)."""
    matrix = golden["matrix_allen"]
    names = matrix[0][1:]
    for row in matrix[1:]:
        one = row[0]
        for other, expected in zip(names, row[1:]):
            if one == other:
                continue
            assert (romanempire.relation_by_name(one, other) or "") == expected, (
                one,
                other,
            )


def test_the_diagonal_is_empty(romanempire):
    for event in romanempire.events:
        assert romanempire.relation(event.id, event.id) is None


def test_the_relation_count_matches_the_rdf_output(romanempire):
    """68 relations, as counted in `alligator_re_results_rdf.ttl` (PRIMER, S3)."""
    assert sum(len(row) for row in romanempire.relations.values()) == 68


def test_the_distance_matrix_matches_the_reference(romanempire, golden):
    """Java writes a decimal comma here; the value is the same (PRIMER A8, D-10)."""
    matrix = golden["matrix_dist"]
    names = matrix[0][1:]
    for row in matrix[1:]:
        one = romanempire.by_name(row[0]).id
        for other, expected in zip(names, row[1:]):
            got = romanempire.distance(one, romanempire.by_name(other).id)
            assert f"{got:.4f}" == expected.replace(",", ".")


def test_the_virtual_years_match_the_reference(romanempire, golden):
    for item in golden["timeline"]:
        event = romanempire.by_name(item["content"].split("-->")[0])
        assert (event.start, event.end) == (item["start"], item["end"])
        assert event.nn_start_name == item["nn_start"]
        assert event.nn_end_name == item["nn_end"]
        assert event.is_point == (item.get("type") == "point")


def test_the_floating_event_is_dated_from_its_neighbour(romanempire):
    """DomitianConsulate2 takes both ends from Domitian: 81 to 96."""
    event = romanempire.by_name("DomitianConsulate2")
    assert (event.a, event.b) == (81.0, 96.0)
    assert event.nn_start_name == event.nn_end_name == "Domitian"
    assert not event.start_fixed and not event.end_fixed
    assert romanempire.relation_by_name("DomitianConsulate2", "Domitian") == "="


def test_the_fixed_events_keep_their_dates(romanempire):
    for event in romanempire.events:
        if event.fixed:
            assert (event.a, event.b) == (event.a_given, event.b_given)
            assert event.nn_start_name is None and event.nn_end_name is None


# --------------------------------------------------------------------------
# distances
# --------------------------------------------------------------------------
def test_the_first_axis_keeps_weight_one():
    assert scale((1.0, 1.0, 1.0)) == (1.0, 1.0, 1.0)
    first, second, third = scale((0.365, 0.149, 0.145))
    assert first == 1.0
    assert second == pytest.approx(0.4082, abs=1e-4)
    assert third == pytest.approx(0.3973, abs=1e-4)


def test_a_zero_first_weight_is_an_error():
    with pytest.raises(AlligatorError, match="cannot be scaled"):
        scale((0.0, 0.1, 0.1))


def test_unweighted_distance_is_euclidean():
    assert distance((0, 0, 0), (3, 4, 0), (1.0, 1.0, 1.0)) == 5.0


def test_weights_damp_the_second_and_third_axis():
    weights = scale((0.365, 0.149, 0.145))
    assert distance((0, 0, 0), (0, 1, 0), weights) == pytest.approx(0.4082, abs=1e-4)


def test_distances_are_symmetric_and_zero_on_the_diagonal(potterlimes):
    for one in potterlimes.events:
        assert potterlimes.distance(one.id, one.id) == 0.0
        for other in potterlimes.events:
            assert potterlimes.distance(one.id, other.id) == pytest.approx(
                potterlimes.distance(other.id, one.id)
            )


# --------------------------------------------------------------------------
# the mixed case: one end fixed, one floating
# --------------------------------------------------------------------------
def test_both_ends_are_judged_independently(potterlimes):
    """`120 ... 9999` is a valid line and keeps its start (PRIMER A7)."""
    event = potterlimes.by_name("NoordzeeKust")
    assert event.start_fixed and not event.end_fixed
    assert event.a == 120.0
    assert event.nn_start_name is None
    assert event.nn_end_name == "Wetteraulimes"
    assert event.b == potterlimes.by_name("Wetteraulimes").b


def test_a_fully_floating_event_takes_both_ends(potterlimes):
    event = potterlimes.by_name("HadriansWall")
    assert (event.nn_start_name, event.nn_end_name) == (
        "Wetteraulimes",
        "Wetteraulimes",
    )
    assert (event.a, event.b) == (110.0, 260.0)


def test_the_marker_can_be_overridden(root):
    """`--floating-value` decides, whatever the metadata block says."""
    result = calculate_file(
        root / "data" / "romanempire" / "romanempire.agt", floating_value=69.0
    )
    assert not result.by_name("Galba").start_fixed
    assert result.by_name("DomitianConsulate2").start_fixed


# --------------------------------------------------------------------------
# ties, limits and reversed intervals
# --------------------------------------------------------------------------
def test_a_tie_keeps_the_earlier_line():
    """Java's strict `<` against a running minimum; documented, not repaired."""
    agt = build(
        "First\t1\t0\t0\t10\t20\tfixed",
        "Second\t-1\t0\t0\t30\t40\tfixed",
        "Floating\t0\t0\t0\t9999\t9999\tfloating",
    )
    result = calculate(agt)
    assert result.by_name("Floating").nn_start_name == "First"


def test_a_lonely_floating_event_is_an_error():
    agt = build("Only\t0\t0\t0\t9999\t9999\tfloating")
    with pytest.raises(NoNeighbourError, match="no fixed start"):
        calculate(agt)


def test_the_neighbour_distance_limit_is_enforced():
    agt = build(
        "Far\t100\t0\t0\t10\t20\tfixed",
        "Floating\t0\t0\t0\t9999\t9999\tfloating",
    )
    calculate(agt)  # the default limit of 200 still reaches it
    with pytest.raises(NoNeighbourError, match="within 50"):
        calculate(agt, max_neighbour_distance=50.0)


def test_a_reversed_interval_is_flagged_not_repaired():
    """Java swaps a and b inside the timeline writer; here it is a property."""
    agt = build(
        "Late\t1\t0\t0\t200\t300\tfixed",
        "Early\t-9\t0\t0\t10\t20\tfixed",
        "Reversed\t0\t0\t0\t9999\t50\tfixed",
    )
    result = calculate(agt)
    event = result.by_name("Reversed")
    assert (event.a, event.b) == (200.0, 50.0)
    assert event.reversed
    assert (event.start, event.end) == (50.0, 200.0)
    assert any("before the start" in warning for warning in result.warnings)


# --------------------------------------------------------------------------
# warnings and strictness
# --------------------------------------------------------------------------
def test_a_clean_file_warns_about_nothing(romanempire, potterlimes):
    assert romanempire.warnings == ()
    assert potterlimes.warnings == ()


def test_column_seven_is_reported_but_does_not_decide():
    agt = build("A\t0\t0\t0\t10\t20\tfloating", "B\t1\t0\t0\t30\t40\tfixed")
    result = calculate(agt)
    assert result.by_name("A").fixed
    assert any("column 7" in warning for warning in result.warnings)


def test_strict_turns_that_warning_into_an_error():
    agt = build("A\t0\t0\t0\t10\t20\tfloating", "B\t1\t0\t0\t30\t40\tfixed")
    with pytest.raises(AlligatorError, match="column 7"):
        calculate(agt, strict=True)


def test_a_fractional_year_is_reported():
    agt = build("A\t0\t0\t0\t10.5\t20\tfixed")
    result = calculate(agt)
    assert any("whole year" in warning for warning in result.warnings)


def test_two_identical_rows_are_reported():
    agt = build("A\t0\t0\t0\t10\t20\tfixed", "A\t0\t0\t0\t10\t20\tfixed")
    result = calculate(agt)
    assert any("identical CA row" in warning for warning in result.warnings)


# --------------------------------------------------------------------------
# reproducibility
# --------------------------------------------------------------------------
@pytest.mark.parametrize("dataset", ["romanempire", "potterlimes"])
def test_two_runs_give_the_same_ids_and_relations(root, dataset):
    path = root / "data" / dataset / f"{dataset}.agt"
    first, second = calculate_file(path), calculate_file(path)
    assert first.ids == second.ids
    assert first.relations == second.relations
    assert first.distances == second.distances


def test_random_ids_do_not(root):
    path = root / "data" / "romanempire" / "romanempire.agt"
    first = calculate_file(path, random_ids=True)
    second = calculate_file(path, random_ids=True)
    assert first.ids != second.ids
    assert first.names == second.names
