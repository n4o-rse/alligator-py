"""The graph output.

Port of de.rgzm.alligator.functions.Graph -- see PRIMER.md, part C, step S2.

A vis.js network: one node per event, one directed edge per kept Allen sign.
The key names are the Java ones, because the GitHub Pages site of step S4 reads
this file directly.

Twelve edges fewer than the reference for `romanempire`: an event is no longer
related to itself (PRIMER A8, D-13). The nodes are unchanged.

Implemented in step S2 of the work plan.
"""

from __future__ import annotations

from pathlib import Path

from alligator.model import Result
from alligator.outputs import files


def nodes(result: Result) -> list[dict]:
    """One node per event, in file order."""
    return [{"id": event.id, "label": event.name} for event in result.events]


def edges(result: Result) -> list[dict]:
    """One edge per kept relation, in file order of source then target.

    Both loops run over the events rather than over the relation dictionary, so
    the order of the file survives into the output and does not depend on how a
    dictionary happens to be laid out.
    """
    out: list[dict] = []
    for one in result.events:
        for other in result.events:
            sign = result.relation(one.id, other.id)
            if sign is not None:
                out.append({"from": one.id, "to": other.id, "label": sign})
    return out


def graph(result: Result) -> dict:
    return {"nodes": nodes(result), "edges": edges(result)}


def write(result: Result, out_dir: Path, dataset: str) -> list[Path]:
    return [files.write_json(out_dir / f"{dataset}_graph.json", graph(result))]
