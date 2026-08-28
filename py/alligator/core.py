"""The transformation itself: parse, measure, date, relate.

Port of de.rgzm.alligator.functions.Alligator.

`calculate` takes a parsed AGT file and returns a `Result`; it touches no files
and writes no output (PRIMER A3). The four steps are the ones the Java
`calculate` runs in the same order: build the events, measure every pair, date
the floating ends from their nearest fixed neighbour, then read the Allen sign
off every pair of dated intervals.

Implemented in steps S1 to S3 of the work plan -- see PRIMER.md, part C.
"""

from __future__ import annotations

import logging
from pathlib import Path

from alligator import agt as agt_module
from alligator import allen, ids
from alligator.agt import AgtFile, AgtRow
from alligator.model import Event, Result

LOG = logging.getLogger("alligator.core")

#: Largest distance still accepted as a nearest fixed neighbour. The Java code
#: starts its minimum search at 200.0 and dereferences null if nothing beats it
#: (PRIMER A8, D-03).
DEFAULT_MAX_NEIGHBOUR_DISTANCE = 200.0


class AlligatorError(Exception):
    """The input cannot be transformed."""


class NoNeighbourError(AlligatorError):
    """A floating end has no fixed neighbour within the accepted distance."""


class _Warnings:
    """Collects warnings, or raises on the first one under `--strict`."""

    def __init__(self, strict: bool) -> None:
        self.strict = strict
        self.messages: list[str] = []

    def add(self, message: str) -> None:
        if self.strict:
            raise AlligatorError(message)
        LOG.warning("%s", message)
        self.messages.append(message)


def scale(weights: tuple[float, float, float]) -> tuple[float, float, float]:
    """Turn the CA eigenvalues into axis weights: (1, d2/d1, d3/d1).

    The first axis keeps weight 1 and the other two are damped in proportion to
    it, so `1.0|1.0|1.0` is the plain Euclidean case.
    """
    first, second, third = weights
    if first == 0.0:
        raise AlligatorError(
            "the first dimension weight is 0; the other two cannot be scaled against it"
        )
    return (1.0, second / first, third / first)


def distance(
    one: Event | tuple[float, float, float],
    other: Event | tuple[float, float, float],
    weights: tuple[float, float, float],
) -> float:
    """Weighted Euclidean distance in the three CA dimensions."""
    x1, y1, z1 = (one.x, one.y, one.z) if isinstance(one, Event) else one
    x2, y2, z2 = (other.x, other.y, other.z) if isinstance(other, Event) else other
    w1, w2, w3 = weights
    dx = (x2 - x1) * w1
    dy = (y2 - y1) * w2
    dz = (z2 - z1) * w3
    return (dx * dx + dy * dy + dz * dz) ** 0.5


def _build_event(row: AgtRow, floating_value: float, random_ids: bool) -> Event:
    """One AGT row as an Event, with both ends judged against the marker.

    Column 7 does not decide. The Java API always passes the floating value from
    the metadata block down, and then only `von == marker` and `bis == marker`
    matter -- independently, which is what makes `120 ... 9999` a valid line
    (PRIMER A7).
    """
    identifier = ids.random_id() if random_ids else ids.event_id(row)
    a = float(row.start)
    b = float(row.end)
    return Event(
        id=identifier,
        name=row.name,
        x=float(row.x),
        y=float(row.y),
        z=float(row.z),
        a=a,
        b=b,
        a_given=a,
        b_given=b,
        flag=row.flag,
        start_fixed=a != floating_value,
        end_fixed=b != floating_value,
        row=row,
    )


def _check_row(event: Event, floating_value: float, warnings: _Warnings) -> None:
    """Report a column 7 that disagrees with the metadata block."""
    says_floating = event.flag.strip().lower() == agt_module.FLOATING_FLAG
    is_floating = not (event.start_fixed and event.end_fixed)
    if says_floating != is_floating:
        warnings.add(
            f"{event.name}: column 7 says {event.flag!r} but the dates say "
            f"{'floating' if is_floating else 'fixed'} against the marker "
            f"{floating_value:g}; the dates decide (PRIMER A7)"
        )
    for value, label in ((event.a_given, "start"), (event.b_given, "end")):
        if value != floating_value and value != int(value):
            warnings.add(
                f"{event.name}: the {label} date {value} is not a whole year; "
                "dates are compared exactly, so rounding may decide a relation"
            )


def _nearest_fixed(
    event: Event,
    candidates: list[Event],
    distances: dict[str, dict[str, float]],
    limit: float,
    which: str,
) -> tuple[Event, float]:
    """The nearest candidate, first one in file order on a tie.

    Java runs a strict `<` against a minimum that starts at 200.0, so a tie
    keeps the earlier line and a distance that never beats the start value
    leaves the identifier null. The tie rule is reproduced; the null is not
    (PRIMER A8, D-03).
    """
    best: Event | None = None
    best_distance = limit
    for candidate in candidates:
        this = distances[event.id][candidate.id]
        if this < best_distance:
            best_distance = this
            best = candidate
    if best is None:
        raise NoNeighbourError(
            f"{event.name}: no fixed {which} within {limit:g} to take a date from. "
            f"Raise --max-neighbour-distance, or fix at least one {which} in the file."
        )
    return best, best_distance


def calculate(
    agt: AgtFile,
    *,
    floating_value: float | None = None,
    weights: tuple[float, float, float] | None = None,
    max_neighbour_distance: float = DEFAULT_MAX_NEIGHBOUR_DISTANCE,
    random_ids: bool = False,
    strict: bool = False,
) -> Result:
    """Read an AGT file into fully dated intervals and their Allen relations."""
    marker = agt.floating_value if floating_value is None else floating_value
    given = agt.weights if weights is None else weights
    axis_weights = scale(given)
    warnings = _Warnings(strict)

    # 1. the events
    events = [_build_event(row, marker, random_ids) for row in agt.rows]
    seen: dict[str, str] = {}
    for event in events:
        if event.id in seen and not random_ids:
            warnings.add(
                f"{event.name}: identical CA row and dates as {seen[event.id]}, "
                f"so both carry the id {event.id}"
            )
        seen.setdefault(event.id, event.name)
        _check_row(event, marker, warnings)

    # 2. every distance, including an event with itself
    distances = {
        one.id: {other.id: distance(one, other, axis_weights) for other in events}
        for one in events
    }

    # 3. the virtual years
    fixed_starts = [event for event in events if event.start_fixed]
    fixed_ends = [event for event in events if event.end_fixed]
    for event in events:
        if not event.start_fixed:
            neighbour, at = _nearest_fixed(
                event, fixed_starts, distances, max_neighbour_distance, "start"
            )
            event.a = neighbour.a
            event.nn_start_name = neighbour.name
            event.nn_start_id = neighbour.id
            event.nn_start_distance = at
    for event in events:
        if not event.end_fixed:
            neighbour, at = _nearest_fixed(
                event, fixed_ends, distances, max_neighbour_distance, "end"
            )
            event.b = neighbour.b
            event.nn_end_name = neighbour.name
            event.nn_end_id = neighbour.id
            event.nn_end_distance = at
    for event in events:
        if event.reversed:
            warnings.add(
                f"{event.name}: dating put the end ({event.b:g}) before the start "
                f"({event.a:g}); the interval is used the other way round and the "
                "timeline marks it red (PRIMER A8, D-05)"
            )

    # 4. the Allen signs
    relations: dict[str, dict[str, str]] = {}
    for one in events:
        row: dict[str, str] = {}
        for other in events:
            if one.id == other.id:
                continue  # PRIMER A8, D-13
            sign = allen.first_sign(one.a, one.b, other.a, other.b)
            if sign is not None:
                row[other.id] = sign
        relations[one.id] = row

    return Result(
        events=tuple(events),
        distances=distances,
        relations=relations,
        weights=axis_weights,
        weights_given=given,
        floating_value=marker,
        warnings=tuple(warnings.messages),
    )


def calculate_file(path: str | Path, **kwargs) -> Result:
    """Convenience wrapper: read an AGT file from disk and calculate."""
    return calculate(agt_module.read(path), **kwargs)


def run(agt: Path, out_dir: Path, args) -> list[Path]:
    """Read an AGT file and write the requested output formats."""
    result = calculate_file(
        agt,
        floating_value=getattr(args, "floating_value", None),
        weights=_weights_from(getattr(args, "dimensions", None)),
        max_neighbour_distance=getattr(
            args, "max_neighbour_distance", DEFAULT_MAX_NEIGHBOUR_DISTANCE
        ),
        random_ids=getattr(args, "random_ids", False),
        strict=getattr(args, "strict", False),
    )
    LOG.info(
        "      %d events, %d relations, weights %s",
        len(result),
        sum(len(row) for row in result.relations.values()),
        "|".join(f"{w:g}" for w in result.weights),
    )
    for event in result.events:
        LOG.debug(
            "      %-22s %8g %8g  %s",
            event.name,
            event.a,
            event.b,
            "fixed" if event.fixed else f"{event.nn_start_name},{event.nn_end_name}",
        )
    raise NotImplementedError(
        "The calculation is done (step S1), but the output writers are steps S2 "
        "and S3 of the work plan, so nothing was written. See PRIMER.md, part C."
    )


def _weights_from(text: str | None) -> tuple[float, float, float] | None:
    """Parse the `--dimensions x|y|z` override."""
    if not text:
        return None
    chunks = [chunk.strip() for chunk in text.split("|")]
    if len(chunks) != 3:
        raise AlligatorError(f"--dimensions needs three values separated by '|': {text!r}")
    return (float(chunks[0]), float(chunks[1]), float(chunks[2]))
