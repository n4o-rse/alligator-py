"""Reader and writer for the Alligator file format (*.agt).

The format is specified in PRIMER.md, part A7. Parsing is strictly positional:
the header must have exactly seven tab-separated columns and the column names
are never read.

Port of the parsing that is split between de.rgzm.alligator.rest.AlligatorAPI
(the metadata block) and Alligator.writeToAlligatorEventList (the data block).
This module keeps both halves in one place and, unlike the Java original, keeps
the raw text of every numeric field: identifiers are derived from it (ids.py)
and the writer reproduces the file it read.

Implemented in step S1 of the work plan.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

#: Column count of the data block. The names are never read, only the order.
COLUMNS = 7

#: Default header, used when a file is written from scratch (step S5).
DEFAULT_HEADER = ("name", "x", "y", "z", "von", "bis", "fixed")

#: Column 7 values that mark an event as floating in the Java code path that
#: ignores the metadata block. Kept for the consistency check in core.py.
FLOATING_FLAG = "floating"


class AgtError(ValueError):
    """The file is not a readable AGT file."""


@dataclass(frozen=True)
class AgtRow:
    """One data line, with every field exactly as it stands in the file.

    Surrounding whitespace is stripped -- `ca_3Dcoordinates_4_2.agt` pads its
    numbers to a fixed width (`" 0.109"`) and Java's `Double.parseDouble`
    tolerates that. Everything else is kept verbatim, because the event
    identifier is derived from these strings (PRIMER, part C, step S1).
    """

    name: str
    x: str
    y: str
    z: str
    start: str
    end: str
    flag: str
    line_number: int = 0

    @property
    def fields(self) -> tuple[str, str, str, str, str, str, str]:
        return (self.name, self.x, self.y, self.z, self.start, self.end, self.flag)

    def as_line(self) -> str:
        return "\t".join(self.fields)


@dataclass(frozen=True)
class AgtFile:
    """A parsed AGT file: three metadata values plus the data block."""

    floating_value: float
    use_weights: bool
    weights: tuple[float, float, float]
    rows: tuple[AgtRow, ...]
    header: tuple[str, ...] = DEFAULT_HEADER
    #: The metadata lines as they stood in the file, so that a file that is
    #: read and written again is unchanged.
    floating_raw: str = ""
    weights_raw: str = ""

    def __post_init__(self) -> None:
        if not self.floating_raw:
            object.__setattr__(self, "floating_raw", _format_number(self.floating_value))
        if not self.weights_raw:
            object.__setattr__(
                self, "weights_raw", "|".join(_format_number(w) for w in self.weights)
            )

    def __len__(self) -> int:
        return len(self.rows)


def _format_number(value: float) -> str:
    """Write a float the way the metadata block does: no trailing `.0` noise."""
    text = repr(float(value))
    return text[:-2] if text.endswith(".0") else text


def _parse_float(text: str, *, field: str, line: int) -> float:
    try:
        return float(text)
    except ValueError as error:  # pragma: no cover - message is the point
        raise AgtError(f"line {line}: {field} is not a number: {text!r}") from error


def parse(text: str) -> AgtFile:
    """Parse the text of an AGT file.

    The Java implementation splits the payload at the literal ``#data``, strips
    the line breaks out of the front part and splits that on ``#``; positions 1,
    2 and 3 are the floating marker, the weights flag and the weights. That is
    reproduced here, including the rule that ``#false`` discards line three.
    """
    if "#data" not in text:
        raise AgtError("no '#data' separator found; this is not an AGT file")

    head, _, body = text.partition("#data")

    metadata = re.sub(r"[\r\n]+", "", head)
    parts = metadata.split("#")
    if len(parts) < 3:
        raise AgtError(
            "the metadata block needs at least a floating value and a weights flag"
        )

    floating_raw = parts[1].strip()
    floating_value = _parse_float(floating_raw, field="the floating value", line=1)

    flag = parts[2].strip().lower()
    if flag not in {"true", "false"}:
        raise AgtError(f"line 2 must be 'true' or 'false', not {parts[2].strip()!r}")
    use_weights = flag == "true"

    weights_raw = parts[3].strip() if len(parts) > 3 else ""
    if use_weights:
        if not weights_raw:
            raise AgtError("line 2 is 'true' but line 3 carries no weights")
        chunks = [chunk.strip() for chunk in weights_raw.split("|")]
        if len(chunks) != 3:
            raise AgtError(
                f"line 3 needs three weights separated by '|', got {weights_raw!r}"
            )
        weights = tuple(
            _parse_float(chunk, field="a dimension weight", line=3) for chunk in chunks
        )
    else:
        # Java: `ca_params = "1.0#1.0#1.0"`. Line three is not even looked at.
        weights = (1.0, 1.0, 1.0)
        weights_raw = "1.0|1.0|1.0"

    lines = [line for line in body.splitlines() if line.strip()]
    if not lines:
        raise AgtError("the data block is empty")

    header = tuple(field.strip() for field in lines[0].split("\t"))
    if len(header) != COLUMNS:
        raise AgtError(
            f"the header has {len(header)} columns, expected exactly {COLUMNS}"
        )

    rows: list[AgtRow] = []
    for offset, line in enumerate(lines[1:], start=1):
        fields = [field.strip() for field in line.split("\t")]
        if len(fields) != COLUMNS:
            raise AgtError(
                f"data line {offset} has {len(fields)} columns, expected {COLUMNS}"
            )
        rows.append(AgtRow(*fields, line_number=offset))

    if not rows:
        raise AgtError("the data block has a header but no events")

    return AgtFile(
        floating_value=floating_value,
        use_weights=use_weights,
        weights=weights,  # type: ignore[arg-type]
        rows=tuple(rows),
        header=header,
        floating_raw=floating_raw,
        weights_raw=weights_raw,
    )


def read(path: str | Path) -> AgtFile:
    """Read an AGT file from disk. CRLF and LF are both accepted (A4)."""
    return parse(Path(path).read_text(encoding="utf-8"))


def dumps(agt: AgtFile) -> str:
    """Serialise an AGT file. Always LF, always UTF-8 without BOM (A4)."""
    lines = [
        f"#{agt.floating_raw}",
        f"#{'true' if agt.use_weights else 'false'}",
        f"#{agt.weights_raw}",
        "#data",
        "\t".join(agt.header),
    ]
    lines.extend(row.as_line() for row in agt.rows)
    return "\n".join(lines) + "\n"


def write(agt: AgtFile, path: str | Path) -> Path:
    """Write an AGT file to disk and return the path."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(dumps(agt), encoding="utf-8", newline="\n")
    return target
