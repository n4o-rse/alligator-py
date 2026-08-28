"""The two matrix outputs.

Port of de.rgzm.alligator.functions.MatrixAllen and MatrixDist -- see PRIMER.md,
part C, step S2.

Both are square tables with a header row and a header column of event names, in
file order. The Allen matrix holds the kept sign per ordered pair, the distance
matrix the weighted CA distance to four decimal places. Each is written as JSON
for the GitHub Pages site of step S4 and as CSV for anything that wants to read
the numbers.

Two differences from the reference: the decimal separator is a point, because
the Java `DecimalFormat` picks up the server locale and would write the same
calculation differently on a different machine (PRIMER A8, D-10), and the main
diagonal of the Allen matrix is empty rather than `=`, because an interval
equalling itself says nothing about chronology (D-13). The shape is unchanged:
`romanempire` stays a 12 by 12 matrix with its headers.

Implemented in step S2 of the work plan.
"""

from __future__ import annotations

from pathlib import Path

from alligator.model import Result
from alligator.outputs import files

#: Decimal places of the distance matrix, as in the Java `DecimalFormat`.
DECIMALS = 4

#: Content of a cell that has no relation, and of the corner above the header
#: column.
EMPTY = ""


def _header(result: Result) -> list[str]:
    return [EMPTY, *result.names]


def allen(result: Result) -> list[list[str]]:
    """The Allen matrix: the kept sign per ordered pair, empty where there is none."""
    rows = [_header(result)]
    for one in result.events:
        rows.append(
            [one.name, *(result.relation(one.id, other.id) or EMPTY for other in result.events)]
        )
    return rows


def dist(result: Result) -> list[list[str]]:
    """The distance matrix, formatted to four decimal places with a point."""
    rows = [_header(result)]
    for one in result.events:
        rows.append(
            [
                one.name,
                *(
                    f"{result.distance(one.id, other.id):.{DECIMALS}f}"
                    for other in result.events
                ),
            ]
        )
    return rows


def write(result: Result, out_dir: Path, dataset: str) -> list[Path]:
    written = []
    for name, rows in (("allen", allen(result)), ("dist", dist(result))):
        stem = out_dir / f"{dataset}_matrix_{name}"
        written.append(files.write_json(stem.with_suffix(".json"), rows))
        written.append(files.write_csv(stem.with_suffix(".csv"), rows))
    return written
