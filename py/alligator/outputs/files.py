"""Writing conventions shared by every output format.

One place for the three rules that make `git status` stay clean after a second
run (PRIMER A3): UTF-8 without a BOM, LF line endings whatever the platform,
and a trailing newline so the files behave in a diff. Nothing here knows what
it is writing.

The Java implementation writes CRLF from `Cypher` and platform-default newlines
from the JSON writers, which is one of the reasons its output could never be
version controlled.

Implemented in step S2 of the work plan.
"""

from __future__ import annotations

import csv
import io
import json
from collections.abc import Iterable, Sequence
from pathlib import Path

#: Encoding of every generated text file. No BOM -- `RätischeLimes` and
#: `fruehkaiserzeitlich` both have to survive a round trip (PRIMER A4).
ENCODING = "utf-8"

#: Line ending of every generated text file, on every platform (PRIMER A4).
NEWLINE = "\n"

#: Indentation of the generated JSON. Java writes one long line; readable JSON
#: costs a few bytes and makes a diff mean something.
INDENT = 2


def write_text(path: Path, text: str) -> Path:
    """Write text with the repository's conventions, adding a final newline."""
    if not text.endswith("\n"):
        text += "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding=ENCODING, newline=NEWLINE) as handle:
        handle.write(text)
    return path


def write_json(path: Path, data) -> Path:
    """Write JSON without escaping non-ASCII, key order as given."""
    return write_text(path, json.dumps(data, ensure_ascii=False, indent=INDENT))


def write_csv(path: Path, rows: Iterable[Sequence[object]]) -> Path:
    """Write CSV through the csv module, so a name with a comma still works."""
    buffer = io.StringIO(newline="")
    csv.writer(buffer, lineterminator=NEWLINE).writerows(rows)
    return write_text(path, buffer.getvalue())
