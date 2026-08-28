"""The timeline output.

Port of de.rgzm.alligator.functions.Timeline -- see PRIMER.md, part C, step S2.

The items are vis.js timeline items and the GitHub Pages site of step S4 reads
this file directly, so the key names are the Java ones and not ours to choose.

One difference in mechanism, none in result: the Java writer swaps `a` and `b`
inside the event object when dating put the end before the start, so the five
writers that run after it see a different interval than the ones that ran
before. Here the swap is read off the event as a property and nothing is
written back (PRIMER A8, D-05).

Implemented in step S2 of the work plan.
"""

from __future__ import annotations

from pathlib import Path

from alligator.model import Event, Result
from alligator.outputs import files

#: Stands for an end that the file itself dated, in the content string of an
#: event whose other end had to be taken from a neighbour.
FIXED_MARKER = "*"

#: vis.js class names. Red beats orange beats blue, which is how the Java
#: conditions come out: every colour test but the last one requires that the
#: interval did not end up reversed.
BLUE, ORANGE, RED = "blue", "orange", "red"


def content(event: Event) -> str:
    """The label: the name, and where a date came from if not from the file.

    `Vespasian` for an event the file dated at both ends,
    `DomitianConsulate2-->Domitian,Domitian` for one dated at both ends from a
    neighbour, and `NoordzeeKust-->*,Vechten` where only the end floated.
    """
    if event.nn_start_name is None and event.nn_end_name is None:
        return event.name
    start = event.nn_start_name or FIXED_MARKER
    end = event.nn_end_name or FIXED_MARKER
    return f"{event.name}-->{start},{end}"


def class_name(event: Event) -> str:
    """`blue` both ends fixed, `orange` at least one end dated, `red` reversed."""
    if event.reversed:
        return RED
    if event.fixed:
        return BLUE
    return ORANGE


def item(event: Event) -> dict:
    """One vis.js item. `type` is present only for a point event."""
    result: dict = {
        "id": event.id,
        "content": content(event),
        "start": event.start,
        "end": event.end,
        "className": class_name(event),
    }
    if event.is_point:
        result["type"] = "point"
    result["nn_start"] = event.nn_start_name
    result["nn_end"] = event.nn_end_name
    return result


def items(result: Result) -> list[dict]:
    """Every event as a vis.js item, in file order."""
    return [item(event) for event in result.events]


def write(result: Result, out_dir: Path, dataset: str) -> list[Path]:
    return [files.write_json(out_dir / f"{dataset}_timeline.json", items(result))]
