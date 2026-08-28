"""The Alligator Turtle output.

Port of de.rgzm.alligator.functions.RDFEvents.writeRDFasText, rebuilt on rdflib
and on the vocabulary as it stands today rather than on the string the Java
method assembles. See PRIMER.md, part C, step S3.

The file describes the events -- identifier, label, the three CA coordinates,
the dated interval, which end was fixed, and where a floating end got its date
from -- and then the Allen relations as OWL-Time properties. Both parts are in
AGT file order, as every other output is.

Four things differ from the reference file, all four registered in PRIMER A8:

* the class is `alligator:Alligator_Event`, the one the Triceratops Edition of
  the vocabulary actually defines. Java writes `alligator:event`, which no
  version of the ontology has ever declared (D-15). `a time:Interval` stays
  alongside it, as in the reference, for readers that do not reason;
* literals are typed, `xsd:double` and `xsd:boolean`, exactly as the ranges in
  the vocabulary say (D-06);
* the two neighbour IRIs `alligator:nfsnE` and `alligator:nfenE` are written.
  They are declared object properties, the `writeRDF` variant of the Java class
  writes them, and only `writeRDFasText` -- the method the web tool calls, and
  therefore the one the reference file comes from -- leaves them out. A name is
  not a reference: two events may share one (D-16);
* the events sit in the namespace the deployed tool uses today, not in
  `http://example.net/event#` (PRIMER A6).

Implemented in step S3 of the work plan.
"""

from __future__ import annotations

from pathlib import Path

from alligator import allen as allen_module
from alligator.model import Event, Result
from alligator.outputs import files, turtle
from rdflib import Literal, Namespace, URIRef
from rdflib.namespace import RDF, RDFS, XSD

#: The Alligator vocabulary, Triceratops Edition (PRIMER A4, A6).
ALLIGATOR = Namespace("http://archaeology.link/ontology#")

#: The events. This is what <https://tools.leiza.de/alligator/> writes today;
#: `http://example.net/event#` in the Java source was a placeholder that
#: outlived its purpose (PRIMER A6).
EVENT = Namespace("http://data.archaeology.link/data/ae/")

TIME = Namespace("http://www.w3.org/2006/time#")
DC = Namespace("http://purl.org/dc/elements/1.1/")

#: Prefix block of the written file, in this order.
PREFIXES: dict[str, str] = {
    "alligator": str(ALLIGATOR),
    "ae": str(EVENT),
    "time": str(TIME),
    "rdfs": str(RDFS),
    "dc": str(DC),
    "xsd": str(XSD),
}

#: The class of an event. The vocabulary declares
#: `:Alligator_Event rdfs:subClassOf time:Interval`; Java writes an undeclared
#: `alligator:event` (D-15).
EVENT_CLASS = ALLIGATOR.Alligator_Event

#: Written explicitly although it follows from the class, because the reference
#: file has it and a consumer without a reasoner would otherwise lose it.
INTERVAL_CLASS = TIME.Interval


def iri(identifier: str) -> URIRef:
    """The IRI of an event, from its identifier."""
    return EVENT[identifier]


def double(value: float) -> Literal:
    """A number as `xsd:double`, in the shortest form that reads back exactly.

    `repr` of a float is the shortest round-tripping representation and has
    been since Python 3.1, which is the rule `ids.normalise` follows as well --
    so two rows that get the same identifier also get the same literal.
    """
    return Literal(repr(float(value)), datatype=XSD.double)


def _describe(document: turtle.Document, event: Event) -> None:
    """One event, as the vocabulary describes it."""
    subject = iri(event.id)
    document.add(subject, RDF.type, EVENT_CLASS)
    document.add(subject, RDF.type, INTERVAL_CLASS)
    document.add(subject, DC.identifier, Literal(event.id))
    document.add(subject, RDFS.label, Literal(event.name))
    document.add(subject, ALLIGATOR.estimatedstart, double(event.a))
    document.add(subject, ALLIGATOR.estimatedend, double(event.b))
    document.add(subject, ALLIGATOR.cax, double(event.x))
    document.add(subject, ALLIGATOR.cay, double(event.y))
    document.add(subject, ALLIGATOR.caz, double(event.z))
    document.add(subject, ALLIGATOR.startfixed, Literal(event.start_fixed))
    document.add(subject, ALLIGATOR.endfixed, Literal(event.end_fixed))
    if event.nn_start_id is not None:
        document.add(subject, ALLIGATOR.nfsn, Literal(event.nn_start_name))
        document.add(subject, ALLIGATOR.nfsnE, iri(event.nn_start_id))
    if event.nn_end_id is not None:
        document.add(subject, ALLIGATOR.nfen, Literal(event.nn_end_name))
        document.add(subject, ALLIGATOR.nfenE, iri(event.nn_end_id))
    document.end_block()


def document(result: Result) -> turtle.Document:
    """The whole file as a Turtle document."""
    doc = turtle.Document(PREFIXES, type_as_keyword=True)
    for event in result.events:
        _describe(doc, event)
    for one in result.events:
        for other in result.events:
            sign = result.relation(one.id, other.id)
            if sign is not None:
                doc.add(
                    iri(one.id), URIRef(allen_module.property_of(sign)), iri(other.id)
                )
    return doc


def rdf(result: Result) -> str:
    return document(result).text()


def write(result: Result, out_dir: Path, dataset: str) -> list[Path]:
    return [files.write_text(out_dir / f"{dataset}.ttl", rdf(result))]
