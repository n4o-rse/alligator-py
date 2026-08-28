"""The Academic Meta Tool Turtle output.

Port of de.rgzm.alligator.functions.AMTEvents, rebuilt on rdflib. See
PRIMER.md, part C, step S3.

This file is the interface to AMT.engine, so it follows what the engine reads
rather than what the Java method concatenates. Three parts, in this order:

1. the events, one `amt:instanceOf rgzm:Event` and one label each;
2. every kept Allen relation as a reified statement -- subject, predicate,
   object -- carrying an `amt:weight`;
3. the Allen roles and axioms, appended verbatim from
   `vocab/amt_allen_axioms.ttl` (PRIMER A8, D-11).

The weight says how far the relation can be trusted. A relation whose subject
was dated in the file weighs `0.99`; one whose subject has at least one end
dated from a neighbour weighs `0.95`, because the interval it rests on was
inferred. That is the Java rule, kept as it stands.

Two things differ from the reference file, both registered in PRIMER A8:

* the events are `ae:` IRIs, the same ones the Alligator Turtle uses, instead
  of sitting in `rgzm:` next to the roles and axioms. `rgzm:` then holds
  vocabulary only, and the two Turtle files of one run describe the same
  events instead of two disjoint sets that merely happen to share labels
  (D-17). The engine is unaffected: it reaches an event through
  `amt:instanceOf rgzm:Event`, never through the shape of its IRI;
* blank node labels are derived from the statement they reify rather than
  drawn at random (D-12), and `amt:weight` is an `xsd:decimal` rather than a
  string (D-06, PRIMER A4).

The general AMT vocabulary is deliberately not written: the engine loads its
own `ontology/amt.ttl` (PRIMER A4).

Implemented in step S3 of the work plan.
"""

from __future__ import annotations

from pathlib import Path

from alligator.model import Result
from alligator.outputs import files, turtle
from alligator.outputs.rdf import EVENT, iri
from rdflib import BNode, Literal, Namespace
from rdflib.namespace import RDF, RDFS, XSD

#: The AMT vocabulary. External, and not written into the output.
AMT = Namespace("http://academic-meta-tool.xyz/vocab#")

#: The Allen roles, the axioms over them and the `Event` concept. Vocabulary
#: only -- the events live in `ae:` (D-17).
RGZM = Namespace("http://rgzm.de/datingmechanism#")

#: Prefix block of the written file, in this order.
PREFIXES: dict[str, str] = {
    "rdf": str(RDF),
    "rdfs": str(RDFS),
    "amt": str(AMT),
    "rgzm": str(RGZM),
    "ae": str(EVENT),
    "xsd": str(XSD),
}

#: The concept every event is an instance of.
EVENT_CONCEPT = RGZM.Event

#: Allen sign -> AMT role name. The three signs that are not letters get one:
#: `<` before, `>` after, `=` equals. The other ten are already role names.
ROLES: dict[str, str] = {
    "<": "b",
    ">": "a",
    "=": "e",
    "m": "m",
    "mi": "mi",
    "o": "o",
    "oi": "oi",
    "s": "s",
    "si": "si",
    "f": "f",
    "fi": "fi",
    "d": "d",
    "di": "di",
}

#: Weight of a relation whose subject was dated in the file.
WEIGHT_FIXED = Literal("0.99", datatype=XSD.decimal)

#: Weight of a relation whose subject has an end dated from a neighbour.
WEIGHT_DATED = Literal("0.95", datatype=XSD.decimal)

#: The static roles and axioms, next to this package.
AXIOMS = Path(__file__).resolve().parent.parent / "vocab" / "amt_allen_axioms.ttl"


def role(sign: str):
    """The AMT role of an Allen sign."""
    try:
        return RGZM[ROLES[sign]]
    except KeyError:  # pragma: no cover - message is the point
        raise KeyError(f"not an Allen relation sign: {sign!r}") from None


def axioms() -> str:
    """The static Allen axioms as they stand on disk."""
    return AXIOMS.read_text(encoding="utf-8")


def document(result: Result) -> turtle.Document:
    """The whole file as a Turtle document."""
    doc = turtle.Document(PREFIXES, type_as_keyword=False)

    for event in result.events:
        subject = iri(event.id)
        doc.add(subject, AMT.instanceOf, EVENT_CONCEPT)
        doc.add(subject, RDFS.label, Literal(event.name))
        doc.end_block()

    for one in result.events:
        for other in result.events:
            sign = result.relation(one.id, other.id)
            if sign is None:
                continue
            statement = BNode(turtle.label(one.id, ROLES[sign], other.id))
            doc.add(statement, RDF.subject, iri(one.id))
            doc.add(statement, RDF.object, iri(other.id))
            doc.add(statement, RDF.predicate, role(sign))
            doc.add(
                statement,
                AMT.weight,
                WEIGHT_FIXED if one.fixed else WEIGHT_DATED,
            )

    doc.append(axioms())
    return doc


def amt(result: Result) -> str:
    return document(result).text()


def write(result: Result, out_dir: Path, dataset: str) -> list[Path]:
    return [files.write_text(out_dir / f"{dataset}_amt.ttl", amt(result))]
