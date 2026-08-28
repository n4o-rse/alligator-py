"""The Cypher output.

Port of de.rgzm.alligator.functions.Cypher -- see PRIMER.md, part C, step S2.

One `CREATE` per event, one `MERGE` per kept relation, one `RETURN` naming every
variable. The event identifier is the Cypher variable name, which is why an
identifier may not start with a digit (see ids.py).

Two differences from the reference, both registered in PRIMER A8:

* The relation names come from a dictionary, not from a chain of `replace()`
  calls. Java replaces `d` before `di`, so `di` comes out as `DURING` + `i`;
  the reference file therefore reads `DURINGi`, `MEETSi`, `OVERLAPSi`,
  `STARTSi` and `FINISHESi` where a Neo4j relation type should read `CONTAINS`,
  `MET_BY`, `OVERLAPPED_BY`, `STARTED_BY` and `FINISHED_BY` (D-02).
* No `MERGE (x)-[:EQUALS]->(x)`: an event is not related to itself (D-13). For
  `romanempire` that is twelve lines fewer.

Implemented in step S2 of the work plan.
"""

from __future__ import annotations

from pathlib import Path

from alligator.model import Result
from alligator.outputs import files

#: Allen sign -> Neo4j relation type. This is the table Java's `replace()` chain
#: was meant to produce (PRIMER A8, D-02).
RELATION_NAMES: dict[str, str] = {
    "<": "BEFORE",
    ">": "AFTER",
    "m": "MEETS",
    "mi": "MET_BY",
    "o": "OVERLAPS",
    "oi": "OVERLAPPED_BY",
    "s": "STARTS",
    "si": "STARTED_BY",
    "f": "FINISHES",
    "fi": "FINISHED_BY",
    "d": "DURING",
    "di": "CONTAINS",
    "=": "EQUALS",
}

#: Node label of every event.
NODE_LABEL = "Event"


def quote(text: str) -> str:
    """A single-quoted Cypher string literal.

    Java concatenates the name into the statement unescaped, so a name holding
    an apostrophe produces a file Neo4j cannot read. Escaping it is a fix and
    not a difference in behaviour for any name that worked before, but it is a
    departure from the original all the same (PRIMER A8, D-14).
    """
    return "'" + text.replace("\\", "\\\\").replace("'", "\\'") + "'"


def statements(result: Result) -> list[str]:
    """The file as a list of lines, without their line endings."""
    lines = [
        f"CREATE ({event.id}:{NODE_LABEL}{{label: {quote(event.name)}}})"
        for event in result.events
    ]
    for one in result.events:
        for other in result.events:
            sign = result.relation(one.id, other.id)
            if sign is not None:
                lines.append(f"MERGE ({one.id})-[:{RELATION_NAMES[sign]}]->({other.id})")
    lines.append("RETURN " + ",".join(result.ids))
    return lines


def cypher(result: Result) -> str:
    return "\n".join(statements(result))


def write(result: Result, out_dir: Path, dataset: str) -> list[Path]:
    return [files.write_text(out_dir / f"{dataset}.cypher", cypher(result))]
