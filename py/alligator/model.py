"""The event record and the result of one calculation.

Port of de.rgzm.alligator.classes.AlligatorEvent, with two changes of substance.

The Java class carries a normalised distance map and an `AllenObject` that
nothing ever reads (PRIMER A8, D-09); they are gone. And it is mutable all the
way through the pipeline: `Timeline.writeTimeline` swaps `a` and `b` when an
event came out reversed, so the object the sixth writer sees is not the object
the first one saw. Here the swap is a property (`start`, `end`, `reversed`), the
dated values stay as they were calculated, and no writer changes the state it
reads (PRIMER A3).

Implemented in step S1 of the work plan.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from alligator.agt import AgtRow


@dataclass
class Event:
    """One dated interval.

    `a` and `b` are the interval bounds after the floating ends have been dated
    from their nearest fixed neighbour: for a fixed end that is the value from
    the file, for a floating one the *virtual year*.
    """

    id: str
    name: str
    x: float
    y: float
    z: float
    a: float
    b: float
    #: Column 7 as it stands in the file. Does not decide anything (PRIMER A7).
    flag: str
    start_fixed: bool
    end_fixed: bool
    row: AgtRow
    #: The bounds as they stood in the file, before dating.
    a_given: float = 0.0
    b_given: float = 0.0
    #: Nearest fixed neighbour, set only for an end that was floating.
    nn_start_name: str | None = None
    nn_start_id: str | None = None
    nn_start_distance: float | None = None
    nn_end_name: str | None = None
    nn_end_id: str | None = None
    nn_end_distance: float | None = None

    @property
    def fixed(self) -> bool:
        """True when the file dated both ends."""
        return self.start_fixed and self.end_fixed

    @property
    def reversed(self) -> bool:
        """True when dating put the end before the start (PRIMER A8, D-05)."""
        return self.b < self.a

    @property
    def start(self) -> float:
        """The lower bound, as a reader of a timeline would expect it."""
        return min(self.a, self.b)

    @property
    def end(self) -> float:
        """The upper bound."""
        return max(self.a, self.b)

    @property
    def is_point(self) -> bool:
        """True when the interval has no extent. Only ever `=` to anything."""
        return self.a == self.b

    def __str__(self) -> str:
        return f"{self.id} {self.name} {self.a} {self.b}"


@dataclass
class Result:
    """Everything one AGT file yields, before any output format touches it.

    The writers of steps S2 and S3 read this and write nothing back.
    """

    events: tuple[Event, ...]
    #: Distance of every ordered pair, including an event with itself.
    distances: dict[str, dict[str, float]]
    #: The kept Allen sign per ordered pair. An event has no entry for itself
    #: and no entry for an event it is unrelated to (PRIMER A8, D-13).
    relations: dict[str, dict[str, str]]
    #: The scaling actually applied: (1, d2/d1, d3/d1).
    weights: tuple[float, float, float]
    #: The weights as they stood in the file, before scaling.
    weights_given: tuple[float, float, float]
    floating_value: float
    warnings: tuple[str, ...] = field(default_factory=tuple)

    def __len__(self) -> int:
        return len(self.events)

    @property
    def ids(self) -> tuple[str, ...]:
        """Event identifiers in file order, which is the order of every output."""
        return tuple(event.id for event in self.events)

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(event.name for event in self.events)

    def by_id(self, identifier: str) -> Event:
        for event in self.events:
            if event.id == identifier:
                return event
        raise KeyError(f"no event with id {identifier!r}")

    def by_name(self, name: str) -> Event:
        for event in self.events:
            if event.name == name:
                return event
        raise KeyError(f"no event named {name!r}")

    def distance(self, one: str, other: str) -> float:
        """Distance between two event ids."""
        return self.distances[one][other]

    def relation(self, one: str, other: str) -> str | None:
        """Allen sign between two event ids, or None if there is none."""
        return self.relations.get(one, {}).get(other)

    def relation_by_name(self, one: str, other: str) -> str | None:
        return self.relation(self.by_name(one).id, self.by_name(other).id)
