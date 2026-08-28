"""Allen interval algebra.

Port of de.rgzm.alligator.allen.AllenInttervalAlgebra. The thirteen relations
and their OWL-Time properties are tabulated in PRIMER.md, part C, step S1.

Freksa's semi-interval relations exist in the Java class but are never called
from the pipeline; they are not ported (PRIMER A8, D-09). The AMT axioms do
reference their roles, which is a different matter -- see part D.

Implemented in step S1 of the work plan.
"""

from __future__ import annotations

TIME = "http://www.w3.org/2006/time#"

#: The thirteen signs, in the order the Java implementation tests them. The
#: order matters: only the first match is kept (PRIMER, part C, step S1).
SIGNS: tuple[str, ...] = ("<", ">", "m", "mi", "o", "oi", "s", "si", "f", "fi", "d", "di", "=")

#: Sign -> OWL-Time property.
PROPERTIES: dict[str, str] = {
    "<": TIME + "intervalBefore",
    ">": TIME + "intervalAfter",
    "m": TIME + "intervalMeets",
    "mi": TIME + "intervalMetBy",
    "o": TIME + "intervalOverlaps",
    "oi": TIME + "intervalOverlappedBy",
    "s": TIME + "intervalStarts",
    "si": TIME + "intervalStartedBy",
    "f": TIME + "intervalFinishes",
    "fi": TIME + "intervalFinishedBy",
    "d": TIME + "intervalDuring",
    "di": TIME + "intervalContains",
    "=": TIME + "intervalEquals",
}

#: Sign -> the short description used in Freksa (1992).
DESCRIPTIONS: dict[str, str] = {
    "<": "before",
    ">": "after",
    "m": "meets",
    "mi": "met-by",
    "o": "overlaps",
    "oi": "overlapped-by",
    "s": "starts",
    "si": "started-by",
    "f": "finishes",
    "fi": "finished-by",
    "d": "during",
    "di": "contains",
    "=": "equals",
}

#: Sign -> converse sign. Not used by the pipeline; the relation of B to A is
#: calculated, not derived. Kept because the tests check the two against each
#: other, which is what catches a transcription slip in the table below.
CONVERSE: dict[str, str] = {
    "<": ">",
    ">": "<",
    "m": "mi",
    "mi": "m",
    "o": "oi",
    "oi": "o",
    "s": "si",
    "si": "s",
    "f": "fi",
    "fi": "f",
    "d": "di",
    "di": "d",
    "=": "=",
}


def relation_signs(a1: float, b1: float, a2: float, b2: float) -> tuple[str, ...]:
    """Every Allen sign that holds between interval 1 (a1, b1) and 2 (a2, b2).

    Transcribed condition for condition from the Java original. Every relation
    except `=` requires both intervals to be proper, which is why a point event
    -- and `romanempire.agt` has four of them, all dated to 69 -- can only ever
    be `=` to another interval. That is the behaviour of the original, not a gap
    in the port.

    In practice the list holds at most one sign; it stays a list because the
    original returns one and because a second entry would be the loudest
    possible signal that the table above has become inconsistent.
    """
    relations: list[str] = []
    if a1 < b1 and b1 < a2 and a2 < b2:
        relations.append("<")
    if a2 < b2 and b2 < a1 and a1 < b1:
        relations.append(">")
    if a1 < b1 and b1 == a2 and a2 < b2:
        relations.append("m")
    if a2 < b2 and b2 == a1 and a1 < b1:
        relations.append("mi")
    if a1 < a2 and a2 < b1 and b1 < b2:
        relations.append("o")
    if a2 < a1 and a1 < b2 and b2 < b1:
        relations.append("oi")
    if a1 == a2 and a2 < b1 and b1 < b2:
        relations.append("s")
    if a1 == a2 and a2 < b2 and b2 < b1:
        relations.append("si")
    if a2 < a1 and a1 < b2 and b2 == b1:
        relations.append("f")
    if a1 < a2 and a2 < b2 and b2 == b1:
        relations.append("fi")
    if a2 < a1 and a1 < b1 and b1 < b2:
        relations.append("d")
    if a1 < a2 and a2 < b2 and b2 < b1:
        relations.append("di")
    if b1 == b2 and a1 == a2:
        relations.append("=")
    return tuple(relations)


def first_sign(a1: float, b1: float, a2: float, b2: float) -> str | None:
    """The sign that is kept, or None if the two intervals are unrelated."""
    signs = relation_signs(a1, b1, a2, b2)
    return signs[0] if signs else None


def property_of(sign: str) -> str:
    """The OWL-Time IRI of a sign.

    Java returns `null` for an unknown sign and then filters it out by comparing
    the string against `"null"` (PRIMER A8, D-04). Here an unknown sign is a
    programming error and says so.
    """
    try:
        return PROPERTIES[sign]
    except KeyError:  # pragma: no cover - message is the point
        raise KeyError(f"not an Allen relation sign: {sign!r}") from None
