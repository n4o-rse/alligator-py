"""Deterministic event identifiers.

The Java implementation derives a Hashid from a fresh random UUID per event, so
no two runs produce the same file. This module replaces that with an identifier
derived from the event's own AGT row (PRIMER A8, D-01).

    id = "e" + base32(blake2s(name|x|y|z|von|bis, digest_size=8))[:8]

Hashed are the *parsed numbers*, each written back as Python's shortest string
that reads back as the same float, not the text as it stands in the file. An
identifier is a name for a point in CA space with a date range, and `0.0810`,
`0.081` and ` 0.081 ` are the same point: they have to get the same name, or
else re-exporting the correspondence analysis with a different column width
renames every event in the repository.

The leading letter is not decoration: Cypher variable names may not start with a
digit, which is also why the Java code draws Hashids until it gets one.

Implemented in step S1 of the work plan.
"""

from __future__ import annotations

import base64
import hashlib
import secrets

from alligator.agt import AgtRow

#: Length of the base32 part. Nine characters in total, as in the Java output.
LENGTH = 8

#: Separator between the fields of the hashed row. Any character that cannot
#: occur inside a tab-separated field would do; the pipe reads well in a log.
SEPARATOR = "|"

_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"


def normalise(text: str) -> str:
    """One numeric field in its canonical form.

    `repr` of a float is the shortest string that reads back as that same float
    and has been stable since Python 3.1, so this is a property of the number
    and not of the interpreter that happens to run.
    """
    return repr(float(text))


def fingerprint(name: str, x: str, y: str, z: str, start: str, end: str) -> str:
    """The string that is hashed. Column 7 is deliberately not part of it.

    Whether an event floats is decided by the metadata block, not by column 7
    (PRIMER A7), so a file that disagrees with itself in that column must not
    produce different identifiers than one that does not.
    """
    numbers = (normalise(value) for value in (x, y, z, start, end))
    return SEPARATOR.join((name, *numbers))


def event_id(row: AgtRow) -> str:
    """The deterministic identifier of one AGT row."""
    digest = hashlib.blake2s(
        fingerprint(row.name, row.x, row.y, row.z, row.start, row.end).encode("utf-8"),
        digest_size=8,
    ).digest()
    return "e" + base64.b32encode(digest).decode("ascii")[:LENGTH]


def random_id(length: int = 6) -> str:
    """A random identifier, for `--random-ids`.

    This restores the *property* the Java implementation has -- an identifier
    that differs between runs, so that two outputs can be told apart -- not its
    Hashid algorithm. Reproducing that algorithm would need the same library and
    the same UUID, and the point of the switch is A/B comparison, not byte
    equality with a run that cannot be repeated anyway.
    """
    first = secrets.choice(_ALPHABET[:52])
    rest = "".join(secrets.choice(_ALPHABET) for _ in range(length - 1))
    return first + rest
