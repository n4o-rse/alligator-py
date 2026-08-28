"""Canonical Turtle: the one place in the code that turns triples into a file.

The repository versions its own output, so a second run has to produce the same
bytes (PRIMER A3). `rdflib.Graph.serialize` does not: measured against rdflib
7.1.1, a graph of plain IRIs comes out the same every time, but one blank node
is enough to make three consecutive processes write three different files,
because blank node labels are drawn from a counter seeded per process. The AMT
output is 68 blank nodes, so the serialiser is unusable there, and relying on
the IRI case staying stable would mean depending on an implementation detail
rdflib does not promise.

Hence this module. The graph is still *built* with rdflib -- these are real
IRIs and typed literals, and rdflib does the escaping and the qname lookup
(PRIMER A4, and A8/D-07) -- but the byte layout is ours:

* triples in the order they were added, deduplicated, never sorted, so the file
  follows the AGT file the way every other output does;
* one triple per line, subject repeated, as in the published reference files,
  so that a diff points at a statement instead of at a semicolon;
* blank node labels derived from the statement they reify (PRIMER A8, D-12);
* a blank line between blocks, wherever the caller ends one.

Every document checks itself: `text()` parses its own output back and compares
it with the graph the triples describe. A layout bug that drops or mangles a
statement fails at write time rather than in whatever reads the file next.

Implemented in step S3 of the work plan.
"""

from __future__ import annotations

from rdflib import BNode, Graph, Literal, URIRef
from rdflib.compare import isomorphic
from rdflib.namespace import NamespaceManager

#: `rdf:type`, written as the Turtle keyword. The Alligator reference file uses
#: it, the AMT one spells `rdf:type` out; each output says which it wants.
TYPE = URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")

#: Characters that may stand in a blank node label. Anything else in an
#: identifier or a role name is replaced, so a label can never turn a valid
#: document into an invalid one.
_LABEL_SAFE = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_")


def label(*parts: str) -> str:
    """A blank node label built from the statement it stands for.

    Java draws a fresh Hashid per edge, so its AMT files never repeat between
    two runs (PRIMER A8, D-12). A label made of subject, role and object is
    stable, unique -- the reification of one ordered pair under one role exists
    once -- and readable, which matters when a SHACL report names a node.
    """
    clean = ("".join(c if c in _LABEL_SAFE else "_" for c in part) for part in parts)
    return "_".join(clean)


class Document:
    """Triples plus the prefix block they are written under.

    Terms are rdflib terms. The caller adds them in the order they should
    appear and ends a block wherever the file should breathe.
    """

    def __init__(self, prefixes: dict[str, str], *, type_as_keyword: bool = True):
        self.prefixes = dict(prefixes)
        self.type_as_keyword = type_as_keyword
        self._triples: list[tuple] = []
        self._seen: set[tuple] = set()
        #: Line offsets at which a blank line is inserted.
        self._breaks: set[int] = set()
        #: Verbatim Turtle appended after the triples, for static vocabulary.
        self._appended: list[str] = []
        self._namespaces = NamespaceManager(Graph(), bind_namespaces="none")
        for prefix, namespace in self.prefixes.items():
            self._namespaces.bind(prefix, URIRef(namespace), override=True)

    # -- building ----------------------------------------------------------

    def add(self, subject, predicate, obj) -> None:
        """One triple. A repeat of a triple already added is dropped."""
        triple = (subject, predicate, obj)
        if triple in self._seen:
            return
        self._seen.add(triple)
        self._triples.append(triple)

    def end_block(self) -> None:
        """Put a blank line after what has been added so far."""
        if self._triples:
            self._breaks.add(len(self._triples))

    def append(self, turtle: str) -> None:
        """Append a block of Turtle verbatim, prefix declarations removed.

        For the static AMT axioms, whose section comments and grouping are part
        of a published file and are worth more intact than reformatted. The
        text still goes through the parse-back check like everything else.
        """
        body = [
            line
            for line in turtle.splitlines()
            if not line.lstrip().startswith(("@prefix", "@base"))
        ]
        self._appended.append("\n".join(body).strip("\n"))

    # -- reading -----------------------------------------------------------

    def graph(self) -> Graph:
        """The triples as a graph, for validation and for comparison in tests."""
        graph = Graph()
        for prefix, namespace in self.prefixes.items():
            graph.bind(prefix, URIRef(namespace), override=True)
        for triple in self._triples:
            graph.add(triple)
        for block in self._appended:
            graph.parse(data=self._prefix_block() + block, format="turtle")
        return graph

    def __len__(self) -> int:
        return len(self._triples)

    # -- writing -----------------------------------------------------------

    def term(self, node) -> str:
        """One term, as rdflib would write it under our prefixes."""
        if isinstance(node, BNode):
            return f"_:{node}"
        if isinstance(node, (URIRef, Literal)):
            return node.n3(self._namespaces)
        raise TypeError(f"not an RDF term: {node!r}")

    def _prefix_block(self) -> str:
        return (
            "\n".join(
                f"@prefix {prefix}: <{namespace}> ."
                for prefix, namespace in self.prefixes.items()
            )
            + "\n\n"
        )

    def _body(self) -> str:
        lines: list[str] = []
        for index, (subject, predicate, obj) in enumerate(self._triples):
            if index in self._breaks:
                lines.append("")
            verb = (
                "a"
                if predicate == TYPE and self.type_as_keyword
                else self.term(predicate)
            )
            lines.append(f"{self.term(subject)} {verb} {self.term(obj)} .")
        for block in self._appended:
            lines.append("")
            lines.append(block)
        return "\n".join(lines) + "\n"

    def text(self) -> str:
        """The document, checked against the graph it is supposed to carry."""
        written = self._prefix_block() + self._body()
        parsed = Graph()
        parsed.parse(data=written, format="turtle")
        expected = self.graph()
        if not isomorphic(parsed, expected):
            raise ValueError(
                "the serialised Turtle does not carry the graph it was built "
                f"from: wrote {len(parsed)} triples, expected {len(expected)}"
            )
        return written
