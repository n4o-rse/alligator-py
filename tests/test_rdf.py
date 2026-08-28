"""The two Turtle outputs of step S3, checked against the Java reference.

What step S3 is finished by (PRIMER, part C): both files carry the same triples
as the reference, the AMT file carries the Allen axioms AMT.engine expects, and
two runs are byte-identical.

"The same triples" cannot mean literal equality -- the reference files come
from their own API calls and carry their own random identifiers (D-01), the
vocabulary has moved on since they were written, and this port types its
literals (D-06). So the reference is *translated* here, through explicit tables,
and the translation is then compared exactly. Every registered deviation appears
below as a named table entry; an unregistered one fails the comparison.

Comparison is by event name throughout.
"""

from __future__ import annotations

import os
import subprocess
import sys

import pytest
from alligator.outputs import amt as amt_module
from alligator.outputs import rdf as rdf_module
from alligator.outputs import turtle
from rdflib import BNode, Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, RDFS, XSD

# --------------------------------------------------------------------------
# the reference vocabulary, and what each term became
# --------------------------------------------------------------------------
#: Namespaces the reference files use for the events. `romanempire` came from a
#: build that still wrote the placeholder, `potterlimes` from the deployed tool.
GOLDEN_EVENT_NAMESPACES = (
    "http://example.net/event#",
    "http://data.archaeology.link/data/ae/",
)

#: Namespaces the reference files use for the Alligator vocabulary. Three URIs
#: for one thing; the Triceratops Edition is the one that counts (PRIMER A6).
GOLDEN_VOCAB_NAMESPACES = (
    "http://rgzm.github.io/alligator/ontology#",
    "https://rgzm.github.io/alligator/vocab#",
    "http://archaeology.link/ontology#",
)

#: D-15: the class the reference writes, and the class the vocabulary declares.
D_15_GOLDEN_CLASS = "event"
D_15_CLASS = rdf_module.EVENT_CLASS

#: D-06: reference literals are untyped strings; these predicates get a type.
D_06_TYPES: dict[str, URIRef] = {
    "estimatedstart": XSD.double,
    "estimatedend": XSD.double,
    "cax": XSD.double,
    "cay": XSD.double,
    "caz": XSD.double,
    "startfixed": XSD.boolean,
    "endfixed": XSD.boolean,
}

#: D-16: written by this port and absent from the reference file, because the
#: web tool calls the one Java method that leaves them out.
D_16_EXTRA_PREDICATES = (rdf_module.ALLIGATOR.nfsnE, rdf_module.ALLIGATOR.nfenE)

#: The AMT vocabulary block the reference repeats in every file and this port
#: does not write, because AMT.engine loads it itself (PRIMER A4, D-11).
D_11_AMT_NAMESPACE = str(amt_module.AMT)


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def parse(text: str) -> Graph:
    graph = Graph()
    graph.parse(data=text, format="turtle")
    return graph


def labels_to_iris(graph: Graph, namespaces: tuple[str, ...]) -> dict[str, URIRef]:
    """Event label -> the IRI the reference gave it."""
    found: dict[str, URIRef] = {}
    for subject, _, obj in graph.triples((None, RDFS.label, None)):
        if isinstance(subject, URIRef) and str(subject).startswith(namespaces):
            found[str(obj)] = subject
    return found


def translate_alligator(golden: Graph, result) -> set[tuple]:
    """The reference graph, restated in the vocabulary this port writes."""
    by_label = labels_to_iris(golden, GOLDEN_EVENT_NAMESPACES)
    ours = {
        golden_iri: rdf_module.iri(result.by_name(name).id)
        for name, golden_iri in by_label.items()
    }
    identifiers = {
        golden_iri: result.by_name(name).id for name, golden_iri in by_label.items()
    }

    def node(term):
        if term in ours:
            return ours[term]
        if isinstance(term, URIRef) and str(term).startswith(GOLDEN_VOCAB_NAMESPACES):
            local = str(term).rsplit("#", 1)[-1]
            if local == D_15_GOLDEN_CLASS:
                return D_15_CLASS
            return rdf_module.ALLIGATOR[local]
        return term

    translated: set[tuple] = set()
    for subject, predicate, obj in golden:
        local = str(predicate).rsplit("#", 1)[-1].rsplit("/", 1)[-1]
        if local == "identifier":
            value = Literal(identifiers[subject])
        elif local in D_06_TYPES:
            value = Literal(str(obj), datatype=D_06_TYPES[local])
        else:
            value = node(obj)
        translated.add((node(subject), node(predicate), value))
    return translated


def statements(graph: Graph, names: dict[URIRef, str]) -> set[tuple]:
    """Every reified AMT relation as (subject name, role, object name, weight)."""
    found = set()
    for node in set(graph.subjects(RDF.subject, None)):
        subject = graph.value(node, RDF.subject)
        obj = graph.value(node, RDF.object)
        role = str(graph.value(node, RDF.predicate)).rsplit("#", 1)[-1]
        weight = str(graph.value(node, amt_module.AMT.weight))
        found.add((names[subject], role, names[obj], weight))
    return found


def amt_names(graph: Graph) -> dict[URIRef, str]:
    return {
        subject: str(label)
        for subject, _, label in graph.triples((None, RDFS.label, None))
        if (subject, amt_module.AMT.instanceOf, None) in graph
    }


# --------------------------------------------------------------------------
# fixtures
# --------------------------------------------------------------------------
@pytest.fixture(scope="module")
def written_ttl(romanempire):
    return rdf_module.rdf(romanempire)


@pytest.fixture(scope="module")
def written_amt(romanempire):
    return amt_module.amt(romanempire)


# --------------------------------------------------------------------------
# the Alligator file
# --------------------------------------------------------------------------
def test_the_turtle_matches_the_reference_triple_for_triple(
    romanempire, golden, written_ttl
):
    ours = set(parse(written_ttl))
    theirs = translate_alligator(parse(golden["ttl"]), romanempire)
    extra = {triple for triple in ours if triple[1] in D_16_EXTRA_PREDICATES}
    assert ours - extra == theirs


def test_the_potterlimes_turtle_matches_its_reference(potterlimes, golden_potterlimes):
    ours = set(parse(rdf_module.rdf(potterlimes)))
    theirs = translate_alligator(parse(golden_potterlimes["ttl"]), potterlimes)
    extra = {triple for triple in ours if triple[1] in D_16_EXTRA_PREDICATES}
    assert ours - extra == theirs


def test_the_reference_holds_the_relation_count_the_primer_states(golden):
    relations = [
        triple
        for triple in parse(golden["ttl"])
        if str(triple[1]).startswith("http://www.w3.org/2006/time#interval")
    ]
    assert len(relations) == 68


def test_every_event_is_typed_by_the_vocabulary_not_by_the_java_string(written_ttl):
    graph = parse(written_ttl)
    assert set(graph.objects(None, RDF.type)) == {
        rdf_module.EVENT_CLASS,
        rdf_module.INTERVAL_CLASS,
    }


def test_a_dated_event_points_at_its_neighbour_by_iri(romanempire, written_ttl):
    graph = parse(written_ttl)
    event = romanempire.by_name("DomitianConsulate2")
    neighbour = romanempire.by_name("Domitian")
    subject = rdf_module.iri(event.id)
    assert graph.value(subject, rdf_module.ALLIGATOR.nfsn) == Literal("Domitian")
    assert graph.value(subject, rdf_module.ALLIGATOR.nfsnE) == rdf_module.iri(
        neighbour.id
    )
    assert graph.value(subject, rdf_module.ALLIGATOR.nfenE) == rdf_module.iri(
        neighbour.id
    )


def test_a_fixed_event_names_no_neighbour(romanempire, written_ttl):
    graph = parse(written_ttl)
    subject = rdf_module.iri(romanempire.by_name("Galba").id)
    for predicate in ("nfsn", "nfen", "nfsnE", "nfenE"):
        assert graph.value(subject, rdf_module.ALLIGATOR[predicate]) is None


def test_the_numbers_are_doubles_and_the_flags_are_booleans(romanempire, written_ttl):
    graph = parse(written_ttl)
    subject = rdf_module.iri(romanempire.by_name("fruehkaiserzeitlich").id)
    assert graph.value(subject, rdf_module.ALLIGATOR.cax) == Literal(
        "-0.266", datatype=XSD.double
    )
    assert graph.value(subject, rdf_module.ALLIGATOR.startfixed) == Literal(True)


def test_no_event_is_related_to_itself(romanempire, written_ttl):
    graph = parse(written_ttl)
    for subject, predicate, obj in graph:
        if str(predicate).startswith("http://www.w3.org/2006/time#interval"):
            assert subject != obj


# --------------------------------------------------------------------------
# the AMT file
# --------------------------------------------------------------------------
def test_the_amt_relations_match_the_reference(golden, written_amt):
    ours = parse(written_amt)
    theirs = parse(golden["amt"])
    assert statements(ours, amt_names(ours)) == statements(theirs, amt_names(theirs))


def test_the_potterlimes_amt_relations_match_the_reference(
    potterlimes, golden_potterlimes
):
    ours = parse(amt_module.amt(potterlimes))
    theirs = parse(golden_potterlimes["amt"])
    assert statements(ours, amt_names(ours)) == statements(theirs, amt_names(theirs))


def test_the_weights_are_decimals_and_follow_the_subject(romanempire, written_amt):
    graph = parse(written_amt)
    weights: dict[str, int] = {}
    for node in graph.subjects(RDF.subject, None):
        weight = graph.value(node, amt_module.AMT.weight)
        assert weight.datatype == XSD.decimal
        weights[str(weight)] = weights.get(str(weight), 0) + 1
    assert weights == {"0.99": 61, "0.95": 7}


def test_every_relation_with_the_dated_event_as_subject_is_the_lighter_one(
    romanempire, written_amt
):
    graph = parse(written_amt)
    subject = rdf_module.iri(romanempire.by_name("DomitianConsulate2").id)
    light = [
        node
        for node in graph.subjects(RDF.subject, subject)
        if str(graph.value(node, amt_module.AMT.weight)) == "0.95"
    ]
    assert len(light) == 7


def test_the_events_are_the_same_iris_as_in_the_alligator_file(
    written_ttl, written_amt
):
    alligator = {
        subject
        for subject in parse(written_ttl).subjects(RDF.type, rdf_module.EVENT_CLASS)
    }
    engine = set(parse(written_amt).subjects(amt_module.AMT.instanceOf, None))
    assert alligator == engine
    assert all(str(subject).startswith(str(rdf_module.EVENT)) for subject in engine)


def test_the_axioms_are_the_ones_the_reference_carries(golden, written_amt):
    ours = parse(written_amt)
    theirs = parse(golden["amt"])
    vocabulary = Namespace(D_11_AMT_NAMESPACE)

    def axioms(graph: Graph) -> set[tuple]:
        """Vocabulary only: in the reference the events sit here too (D-17)."""
        instances = set(graph.subjects(amt_module.AMT.instanceOf, None))
        return {
            (subject, predicate, obj)
            for subject, predicate, obj in graph
            if str(subject).startswith(str(amt_module.RGZM))
            and subject not in instances
        }

    assert axioms(ours) == axioms(theirs)
    assert not [triple for triple in ours if str(triple[0]).startswith(str(vocabulary))]


def test_the_axiom_file_holds_what_the_engine_expects():
    graph = Graph()
    graph.parse(amt_module.AXIOMS, format="turtle")
    counted = {
        str(obj).rsplit("#", 1)[-1]: 0 for obj in set(graph.objects(None, RDF.type))
    }
    for _, _, obj in graph.triples((None, RDF.type, None)):
        counted[str(obj).rsplit("#", 1)[-1]] += 1
    assert counted == {
        "Concept": 1,
        "Role": 31,
        "InverseAxiom": 28,
        "SelfDisjointAxiom": 31,
        "DisjointAxiom": 6,
        "RoleChainAxiom": 126,
    }
    assert len(graph) == 921


# --------------------------------------------------------------------------
# the writer itself
# --------------------------------------------------------------------------
def test_a_blank_node_label_survives_a_sign_that_is_not_a_letter():
    assert turtle.label("eABC", "<", "eDEF") == "eABC___eDEF"


def test_the_document_refuses_to_write_a_graph_it_would_lose():
    document = turtle.Document({"ex": "http://example.org/"})
    document.add(URIRef("http://example.org/a"), RDF.type, BNode("x"))
    assert "_:x" in document.text()


def test_two_runs_in_two_processes_are_byte_identical(root):
    """Blank node labels are the risk here, so this has to leave the process.

    `rdflib.Graph.serialize` draws them from a per-process counter; a check
    that stays in one interpreter would not see that at all.

    The environment is inherited and only `PYTHONHASHSEED` is set on top of it.
    Handing the child a stripped-down environment instead costs Windows its
    `SystemRoot`, and without that `os.urandom` cannot reach the crypto
    provider -- which has nothing to do with what is being measured here.
    """
    script = (
        "import sys; sys.path.insert(0, %r)\n"
        "from alligator.core import calculate_file\n"
        "from alligator.outputs import amt, rdf\n"
        "r = calculate_file(%r)\n"
        "sys.stdout.write(rdf.rdf(r)); sys.stdout.write(amt.amt(r))\n"
    ) % (
        str(root / "py"),
        str(root / "data" / "romanempire" / "romanempire.agt"),
    )
    runs = [
        subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            check=True,
            env={**os.environ, "PYTHONHASHSEED": seed},
        ).stdout
        for seed in ("0", "1", "random")
    ]
    assert runs[0] == runs[1] == runs[2]
    assert runs[0]


def test_both_files_end_in_a_newline_and_hold_no_carriage_return(romanempire, tmp_path):
    from alligator.core import write

    paths = write(romanempire, tmp_path, "romanempire", ["ttl", "amt"])
    assert {path.name for path in paths} == {"romanempire.ttl", "romanempire_amt.ttl"}
    for path in paths:
        raw = path.read_bytes()
        assert raw.endswith(b"\n")
        assert b"\r" not in raw


def test_the_written_files_parse(romanempire, tmp_path):
    from alligator.core import write

    for path in write(romanempire, tmp_path, "romanempire", ["ttl", "amt"]):
        graph = Graph()
        graph.parse(path, format="turtle")
        assert len(graph) > 0
