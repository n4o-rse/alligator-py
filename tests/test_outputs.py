"""The four data outputs of step S2, checked against the Java reference.

What step S2 is finished by (PRIMER, part C): timeline, graph, both matrices and
Cypher agree with the golden files, and two runs are byte-identical.

The reference and this port disagree in exactly two places, and both are written
out here as named exception tables rather than as a loosened comparison, so that
a third disagreement fails the test instead of slipping through:

* `D_02_JAVA_NAMES` -- the Cypher relation types the Java `replace()` chain
  actually produces (PRIMER A8, D-02).
* the self-relations on the main diagonal, which Java writes into the matrix,
  the graph and the Cypher file and this port writes nowhere (D-13).

Comparison is by event name throughout: every reference file comes from its own
API call and carries its own random identifiers (D-01).
"""

from __future__ import annotations

import json
import re

import pytest
from alligator import allen as allen_module
from alligator.core import AlligatorError, parse_formats, write
from alligator.outputs import cypher as cypher_module
from alligator.outputs import graph as graph_module
from alligator.outputs import matrix as matrix_module
from alligator.outputs import timeline as timeline_module

# --------------------------------------------------------------------------
# the two registered deviations, as tables
# --------------------------------------------------------------------------
#: Our relation type -> the one in the reference file. Java replaces `d` before
#: `di`, `m` before `mi` and so on, so the inverse of every relation whose sign
#: ends in `i` comes out as the base name with an `i` stuck to it (D-02).
D_02_JAVA_NAMES = {
    "MET_BY": "MEETSi",
    "OVERLAPPED_BY": "OVERLAPSi",
    "STARTED_BY": "STARTSi",
    "FINISHED_BY": "FINISHESi",
    "CONTAINS": "DURINGi",
}

#: What Java writes on the main diagonal and this port does not (D-13).
D_13_DIAGONAL_SIGN = "="
D_13_DIAGONAL_NAME = "EQUALS"


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
CREATE = re.compile(r"^CREATE \((\w+):Event\{label: '(.*)'\}\)$")
MERGE = re.compile(r"^MERGE \((\w+)\)-\[:(\w+)\]->\((\w+)\)$")


def read_cypher(text: str):
    """A Cypher file as (names by variable, relations by name pair, RETURN list)."""
    names: dict[str, str] = {}
    relations: dict[tuple[str, str], str] = {}
    returned: list[str] = []
    for line in text.replace("\r\n", "\n").strip().split("\n"):
        created = CREATE.match(line)
        merged = MERGE.match(line)
        if created:
            names[created.group(1)] = created.group(2)
        elif merged:
            one, relation, other = merged.groups()
            relations[(names[one], names[other])] = relation
        elif line.startswith("RETURN "):
            returned = [name.strip() for name in line[len("RETURN ") :].split(",")]
        else:
            raise AssertionError(f"unparsed Cypher line: {line!r}")
    return names, relations, returned


def cells(matrix):
    """A reference matrix as {(row name, column name): value}."""
    names = matrix[0][1:]
    return {
        (row[0], column): value
        for row in matrix[1:]
        for column, value in zip(names, row[1:])
    }


@pytest.fixture(scope="module")
def written(romanempire, tmp_path_factory):
    """Every S2 file for `romanempire`, written once and read back."""
    directory = tmp_path_factory.mktemp("s2")
    paths = write(romanempire, directory, "romanempire", parse_formats("timeline,graph,matrix,cypher"))
    return {path.name: path for path in paths}


def load(written, name):
    path = written[name]
    return json.loads(path.read_text(encoding="utf-8")) if path.suffix == ".json" else path.read_text(encoding="utf-8")


# --------------------------------------------------------------------------
# timeline
# --------------------------------------------------------------------------
def test_the_timeline_matches_the_reference(romanempire, golden):
    """No exception applies here: the timeline never carried self-relations."""
    ours = {
        item["content"].partition("-->")[0]: item
        for item in timeline_module.items(romanempire)
    }
    assert len(ours) == len(golden["timeline"])
    for expected in golden["timeline"]:
        item = ours[expected["content"].partition("-->")[0]]
        for key in ("content", "start", "end", "className", "nn_start", "nn_end"):
            assert item[key] == expected[key], (expected["content"], key)
        assert item.get("type") == expected.get("type")


def test_the_dated_event_is_orange_and_names_both_neighbours(romanempire):
    item = next(
        item
        for item in timeline_module.items(romanempire)
        if item["content"].startswith("DomitianConsulate2")
    )
    assert item["className"] == timeline_module.ORANGE
    assert item["content"] == "DomitianConsulate2-->Domitian,Domitian"


def test_a_half_floating_event_marks_the_fixed_end_with_a_star(potterlimes):
    """`NoordzeeKust` has a fixed start and a floating end (PRIMER A1)."""
    item = next(
        item
        for item in timeline_module.items(potterlimes)
        if item["content"].startswith("NoordzeeKust")
    )
    assert item["className"] == timeline_module.ORANGE
    assert item["content"].partition("-->")[2].startswith(timeline_module.FIXED_MARKER + ",")
    assert item["nn_start"] is None and item["nn_end"] is not None


def test_the_timeline_json_is_a_list_of_items(written):
    items = load(written, "romanempire_timeline.json")
    assert items[0]["content"] == "fruehkaiserzeitlich"


# --------------------------------------------------------------------------
# graph
# --------------------------------------------------------------------------
def test_the_graph_nodes_match_the_reference(romanempire, golden):
    ours = [node["label"] for node in graph_module.nodes(romanempire)]
    assert ours == [node["label"] for node in golden["graph"]["nodes"]]


def test_the_graph_edges_match_the_reference_off_the_diagonal(romanempire, golden):
    labels = {node["id"]: node["label"] for node in golden["graph"]["nodes"]}
    expected = {
        (labels[edge["from"]], labels[edge["to"]]): edge["label"]
        for edge in golden["graph"]["edges"]
        if edge["from"] != edge["to"]  # D-13, and only here
    }
    ours = {
        (romanempire.by_id(edge["from"]).name, romanempire.by_id(edge["to"]).name): edge["label"]
        for edge in graph_module.edges(romanempire)
    }
    assert ours == expected


def test_the_graph_drops_exactly_the_self_edges_java_writes(romanempire, golden):
    """The D-13 exception, stated rather than assumed: 12 edges, all `=`."""
    dropped = [
        edge for edge in golden["graph"]["edges"] if edge["from"] == edge["to"]
    ]
    assert len(dropped) == len(romanempire)
    assert {edge["label"] for edge in dropped} == {D_13_DIAGONAL_SIGN}
    assert len(graph_module.edges(romanempire)) == len(golden["graph"]["edges"]) - len(romanempire)


# --------------------------------------------------------------------------
# matrices
# --------------------------------------------------------------------------
def test_the_allen_matrix_keeps_the_shape_of_the_reference(romanempire, golden):
    ours = matrix_module.allen(romanempire)
    assert ours[0] == golden["matrix_allen"][0]
    assert [row[0] for row in ours] == [row[0] for row in golden["matrix_allen"]]


def test_the_allen_matrix_matches_the_reference_off_the_diagonal(romanempire, golden):
    expected = cells(golden["matrix_allen"])
    for (one, other), value in cells(matrix_module.allen(romanempire)).items():
        if one == other:
            continue  # D-13, checked separately below
        assert value == expected[(one, other)], (one, other)


def test_the_allen_diagonal_is_empty_where_java_writes_equals(romanempire, golden):
    """The D-13 exception, stated: the reference has `=` there, we have nothing."""
    expected = cells(golden["matrix_allen"])
    for (one, other), value in cells(matrix_module.allen(romanempire)).items():
        if one == other:
            assert expected[(one, other)] == D_13_DIAGONAL_SIGN
            assert value == matrix_module.EMPTY


def test_the_distance_matrix_matches_the_reference(romanempire, golden):
    """Same numbers, a decimal point instead of the server's comma (D-10)."""
    expected = cells(golden["matrix_dist"])
    for key, value in cells(matrix_module.dist(romanempire)).items():
        assert value == expected[key].replace(",", "."), key


def test_the_distance_matrix_is_symmetric_and_zero_on_the_diagonal(romanempire):
    values = cells(matrix_module.dist(romanempire))
    for (one, other), value in values.items():
        assert value == values[(other, one)]
        if one == other:
            assert float(value) == 0.0


def test_the_csv_matrices_hold_the_same_cells_as_the_json(written):
    import csv

    for name in ("allen", "dist"):
        as_json = load(written, f"romanempire_matrix_{name}.json")
        as_csv = list(csv.reader(written[f"romanempire_matrix_{name}.csv"].read_text(
            encoding="utf-8"
        ).splitlines()))
        assert as_csv == as_json


# --------------------------------------------------------------------------
# cypher
# --------------------------------------------------------------------------
def test_the_cypher_creates_one_node_per_event_in_file_order(romanempire):
    names, _, returned = read_cypher(cypher_module.cypher(romanempire))
    assert list(names.values()) == list(romanempire.names)
    assert returned == list(romanempire.ids)


def test_the_cypher_matches_the_reference(romanempire, golden):
    """Every reference relation, translated through D-02 and minus D-13."""
    _, expected, _ = read_cypher(golden["cypher"])
    _, ours, _ = read_cypher(cypher_module.cypher(romanempire))

    for (one, other), java_name in expected.items():
        if one == other:
            assert java_name == D_13_DIAGONAL_NAME  # D-13
            assert (one, other) not in ours
            continue
        assert D_02_JAVA_NAMES.get(ours[(one, other)], ours[(one, other)]) == java_name, (
            one,
            other,
        )
    assert set(ours) == {pair for pair in expected if pair[0] != pair[1]}


def test_the_cypher_names_are_the_neo4j_ones(romanempire):
    """The point of D-02: `di` is CONTAINS, not DURING with an `i` after it."""
    assert cypher_module.RELATION_NAMES["di"] == "CONTAINS"
    assert cypher_module.RELATION_NAMES["mi"] == "MET_BY"
    assert set(cypher_module.RELATION_NAMES) == set(allen_module.SIGNS)


def test_a_name_with_an_apostrophe_is_escaped(romanempire):
    """D-14: Java concatenates the name in unescaped and writes broken Cypher."""
    assert cypher_module.quote("Ain't") == "'Ain\\'t'"


# --------------------------------------------------------------------------
# the writing itself
# --------------------------------------------------------------------------
def test_every_file_ends_in_a_newline_and_holds_no_carriage_return(written):
    for path in written.values():
        raw = path.read_bytes()
        assert raw.endswith(b"\n"), path.name
        assert b"\r" not in raw, path.name


def test_two_runs_are_byte_identical(romanempire, tmp_path):
    formats = parse_formats("timeline,graph,matrix,cypher")
    first = write(romanempire, tmp_path / "one", "romanempire", formats)
    second = write(romanempire, tmp_path / "two", "romanempire", formats)
    assert [path.name for path in first] == [path.name for path in second]
    for one, other in zip(first, second):
        assert one.read_bytes() == other.read_bytes(), one.name


def test_potterlimes_writes_every_format(potterlimes, tmp_path):
    paths = write(potterlimes, tmp_path, "potterlimes", parse_formats("timeline,graph,matrix,cypher"))
    assert sorted(path.name for path in paths) == [
        "potterlimes.cypher",
        "potterlimes_graph.json",
        "potterlimes_matrix_allen.csv",
        "potterlimes_matrix_allen.json",
        "potterlimes_matrix_dist.csv",
        "potterlimes_matrix_dist.json",
        "potterlimes_timeline.json",
    ]


def test_an_unknown_format_is_refused():
    with pytest.raises(AlligatorError, match="unknown output format"):
        parse_formats("timeline,teapot")


def test_the_format_list_keeps_the_declared_order():
    assert parse_formats("cypher,timeline") == ["timeline", "cypher"]


# --------------------------------------------------------------------------
# the second dataset, against the grapHNR23 reference
# --------------------------------------------------------------------------
def test_the_potterlimes_reference_is_the_same_input(root, golden_potterlimes):
    """Same AGT as `data/potterlimes/`, bar the header names the parser ignores."""
    ours = (root / "data" / "potterlimes" / "potterlimes.agt").read_text(encoding="utf-8")
    theirs = golden_potterlimes["agt"]
    strip = lambda text: [
        line for line in text.replace("\r\n", "\n").strip().split("\n")
    ]
    mine, other = strip(ours), strip(theirs)
    assert len(mine) == len(other)
    differing = [index for index, (a, b) in enumerate(zip(mine, other)) if a != b]
    assert differing == [4], differing  # the header line and nothing else
    assert mine[4].split("\t")[4:6] == ["von", "bis"]
    assert other[4].split("\t")[4:6] == ["from", "to"]


def test_the_potterlimes_cypher_matches_the_reference(potterlimes, golden_potterlimes):
    """The same two exceptions, on a dataset with real CA weights."""
    _, expected, _ = read_cypher(golden_potterlimes["cypher"])
    _, ours, _ = read_cypher(cypher_module.cypher(potterlimes))

    for (one, other), java_name in expected.items():
        if one == other:
            assert java_name == D_13_DIAGONAL_NAME  # D-13
            assert (one, other) not in ours
            continue
        assert D_02_JAVA_NAMES.get(ours[(one, other)], ours[(one, other)]) == java_name, (
            one,
            other,
        )
    assert set(ours) == {pair for pair in expected if pair[0] != pair[1]}


def test_the_potterlimes_dating_matches_the_reference(potterlimes, golden_potterlimes):
    """The virtual years and the neighbour names, read out of the Turtle file.

    This is an S1 check on a second provenance: `HadriansWall` floats at both
    ends and `NoordzeeKust` only at the end, and the weighted axes decide which
    neighbour each takes its date from.
    """
    values = {}
    for subject, predicate, literal in re.findall(r"ae:(\w+) (\S+) \"([^\"]*)\"", golden_potterlimes["ttl"]):
        values.setdefault(subject, {})[predicate.split(":")[-1]] = literal

    assert len(values) == len(potterlimes)
    for fields in values.values():
        event = potterlimes.by_name(fields["label"])
        assert event.a == float(fields["estimatedstart"])
        assert event.b == float(fields["estimatedend"])
        assert event.start_fixed is (fields["startfixed"] == "true")
        assert event.end_fixed is (fields["endfixed"] == "true")
        assert event.nn_start_name == fields.get("nfsn")
        assert event.nn_end_name == fields.get("nfen")


def test_the_potterlimes_relation_count_matches_the_reference(
    potterlimes, golden_potterlimes
):
    assert sum(len(row) for row in potterlimes.relations.values()) == len(
        re.findall(r"time:interval", golden_potterlimes["ttl"])
    )


def test_the_amt_reference_confirms_the_weights_of_step_s3(potterlimes, golden_potterlimes):
    """Not an S2 check, but the numbers S3 is written against, now measured.

    `0.95` where the subject has a floating end, `0.99` otherwise. Fourteen and
    forty-two here, which is the seven relations of each of the two floating
    events counted twice over.
    """
    weights = re.findall(r'amt:weight "([^"]*)"', golden_potterlimes["amt"])
    floating = [event for event in potterlimes.events if not event.fixed]
    expected_low = sum(len(potterlimes.relations[event.id]) for event in floating)
    assert weights.count("0.95") == expected_low == 14
    assert weights.count("0.99") == len(weights) - expected_low == 42
