"""Static figures of the three views, as SVG and as a high-resolution JPEG.

The interactive vis.js page of step S4 stays; these are the same three views as
files that can go into a paper, a poster or a Zenodo record without a browser
(PRIMER A4). Four figures per dataset: the timeline, the relation graph, the
Allen matrix and the distance matrix.

Both formats are written from one matplotlib figure, so they cannot drift apart:
the SVG is the archival copy, the JPEG the one that can be pasted anywhere.
JPEG is lossy, which is why it is written at 300 dpi with chroma subsampling
switched off -- the alternative would be blurred edges on the matrix labels.

The palette is not ours to choose. `leiza-scit/CAA2026-alligator` draws the same
two views for the paper and states in `py/viz/_prelude.py` that a relation has
to be the same colour in the browser figures and in the printed ones; the table
below is that palette, grouped by relation family so the matrix can be read
before the legend is. What is added here is a fill for a pair with no relation
at all, which the published figures never contain because every one of their
clusters relates to every other.

Byte-identical on a second run, like every other output (PRIMER A3). Two of the
three settings that need come from `wd_repro`, the family's shared module: it
pins `svg.hashsalt` and `SOURCE_DATE_EPOCH`, and it sets the salt on
`rcParamsDefault` rather than on `rcParams`, so a later `plt.rcdefaults()`
cannot silently throw it away. The third is local: text is rendered as paths, so
the file does not depend on which fonts the reader has installed.

Byte equality holds for one installed set of versions; a different matplotlib or
libjpeg may lay the same figure out differently, which is why requirements.txt
pins them.

Implemented in step S2 of the work plan.
"""

from __future__ import annotations

import io
import logging
import math
from pathlib import Path

from alligator import allen as allen_module
from alligator.model import Result
from alligator.outputs import files
from alligator.outputs import timeline as timeline_module

LOG = logging.getLogger("alligator.render")

#: Resolution of the JPEG. The SVG is resolution-independent.
DPI = 300

#: Pillow settings for the JPEG. `subsampling=0` keeps the chroma planes at full
#: resolution, which is what saves small text from colour fringes.
JPEG_OPTIONS = {"quality": 95, "subsampling": 0, "optimize": True}

#: Allen sign -> (label written in a matrix cell, colour). Taken from
#: `CAA2026-alligator/py/viz/_prelude.py` and the matrix in
#: `py/alligator_to_clean_rdf.py`, abbreviations included, so that a relation
#: keeps its colour across the family's figures.
RELATIONS: dict[str, tuple[str, str]] = {
    "<": ("before", "#4a90d9"),
    ">": ("after", "#2c5f8a"),
    "m": ("meets", "#7ab3e0"),
    "mi": ("met-by", "#5a9fc5"),
    "o": ("overlaps", "#f0a500"),
    "oi": ("ovlp-by", "#c97d00"),
    "s": ("starts", "#e07070"),
    "si": ("started-by", "#c05050"),
    "f": ("finishes", "#e09090"),
    "fi": ("finished-by", "#b04060"),
    "d": ("during", "#a03030"),
    "di": ("contains", "#d94a4a"),
    "=": ("equals", "#4caf50"),
}

#: The four families, in the order the legend lists them: the colour that stands
#: for the group, and what belongs to it. Reading the matrix by family is the
#: point of the palette -- blue is a sequence, red a containment.
FAMILIES: tuple[tuple[str, str], ...] = (
    ("#4a90d9", "Sequential (before / after / meets / met-by)"),
    ("#f0a500", "Overlapping (overlaps / overlapped-by)"),
    ("#d94a4a", "Containing (contains / during / starts / finishes …)"),
    ("#4caf50", "Equal"),
)

#: Fill of the main diagonal, and the character written on it. An event is not
#: related to itself (PRIMER A8, D-13), and an empty cell there would read as
#: "no relation found" rather than "not asked".
DIAGONAL_FILL = "#dddddd"
DIAGONAL_INK = "#999999"
DIAGONAL_MARK = "—"

#: Fill of a pair that genuinely has no relation -- two point events on
#: different years, for instance. Distinct from the diagonal on purpose.
UNRELATED_FILL = "#f9f9f9"

#: The timeline colours, from `alligator_to_clean_rdf.plot_events_timeline`.
#: Red has no counterpart there: no published dataset has an interval that came
#: out reversed.
COLOURS = {
    timeline_module.BLUE: "#8fa8c8",
    timeline_module.ORANGE: "#f0a500",
    timeline_module.RED: "#bd4136",
}

#: What the colours mean, for the legend.
MEANINGS = {
    timeline_module.BLUE: "both ends dated in the file",
    timeline_module.ORANGE: "both ends from a neighbour",
    timeline_module.RED: "end before start after dating",
}

#: Legend text for the half-dated case, which is drawn as a gradient from the
#: fixed end to the estimated one.
GRADIENT_MEANING = "one end dated, one from a neighbour"

#: Grey of the axes, labels and graph edges.
INK = "#333333"
FAINT = "#b0b0b0"


class RenderError(RuntimeError):
    """The figures cannot be drawn."""


# --------------------------------------------------------------------------
# matplotlib, imported late so that a run without it still writes the data
# --------------------------------------------------------------------------
def _pyplot():
    """Import matplotlib, force the file backend, and pin the settings A3 needs."""
    try:
        import matplotlib
    except ModuleNotFoundError as error:  # pragma: no cover - depends on the install
        raise RenderError(
            "matplotlib is needed for the figures. Install it with "
            "`pip install -r requirements.txt`, or leave 'img' out of --formats."
        ) from error

    matplotlib.use("Agg")
    # The family's shared reproducibility module. Imported for its effect: it
    # pins `svg.hashsalt` on `rcParamsDefault` and sets `SOURCE_DATE_EPOCH`, so
    # the element ids and the date in the SVG metadata stop moving between runs.
    import matplotlib.pyplot as plt
    import wd_repro  # noqa: F401

    matplotlib.rcParams.update(
        {
            # Text as outlines: the SVG then looks the same everywhere, at the
            # price of not being editable as text.
            "svg.fonttype": "path",
            # Ships with matplotlib, so it is present wherever this runs.
            "font.family": "DejaVu Sans",
            "font.size": 8.5,
            "figure.facecolor": "white",
            "savefig.facecolor": "white",
            "axes.edgecolor": INK,
            "axes.labelcolor": INK,
            "text.color": INK,
            "xtick.color": INK,
            "ytick.color": INK,
        }
    )
    return plt


def _save(figure, out_dir: Path, stem: str, dpi: int) -> list[Path]:
    """One figure, written as SVG and as JPEG.

    The SVG goes through the repository's own text writer rather than straight
    out of `savefig`, because matplotlib opens the file in text mode and would
    put CRLF into it on Windows. That contradicts `.gitattributes`, and the file
    would then show up as modified after every run on a Windows machine and
    identical on a Linux one (PRIMER A3, A4). `wd_repro` does not cover this,
    which is the one thing this repository has to add to it.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    svg = out_dir / f"{stem}.svg"
    jpg = out_dir / f"{stem}.jpg"

    buffer = io.BytesIO()
    figure.savefig(buffer, format="svg", bbox_inches="tight")
    files.write_text(svg, buffer.getvalue().decode("utf-8").replace("\r\n", "\n"))

    figure.savefig(
        jpg, format="jpg", dpi=dpi, bbox_inches="tight", pil_kwargs=JPEG_OPTIONS
    )
    return [svg, jpg]


def _legend_handles(plt, entries):
    """Legend entries as colour patches, so no data has to be drawn twice."""
    from matplotlib.patches import Patch

    return [Patch(facecolor=colour, edgecolor="none", label=label) for colour, label in entries]


# --------------------------------------------------------------------------
# the four figures
# --------------------------------------------------------------------------
def timeline_figure(result: Result, plt):
    """A bar per event, at its dated position, coloured as in the timeline JSON.

    Events keep the order of the file rather than being sorted by date, so the
    figure can be read against the AGT file, the matrices and the graph.
    """
    events = result.events
    figure, axes = plt.subplots(figsize=(8.5, max(2.2, 0.32 * len(events) + 1.4)))

    half = [event for event in events if event.start_fixed != event.end_fixed]

    for index, event in enumerate(events):
        y = len(events) - 1 - index
        colour = COLOURS[timeline_module.class_name(event)]
        if event.is_point:
            axes.plot(
                [event.start], [y], marker="D", markersize=4.5, color=colour, zorder=3
            )
        elif event in half and not event.reversed:
            _gradient_bar(axes, event, y, plt)
        else:
            axes.barh(
                y,
                event.end - event.start,
                left=event.start,
                height=0.58,
                color=colour,
                zorder=3,
            )

    axes.set_yticks(range(len(events)))
    axes.set_yticklabels([event.name for event in reversed(events)])
    axes.set_ylim(-0.7, len(events) - 0.3)
    axes.set_xlabel("year")
    axes.grid(axis="x", color=FAINT, linewidth=0.5, zorder=0)
    axes.set_axisbelow(True)
    for side in ("top", "right", "left"):
        axes.spines[side].set_visible(False)

    from matplotlib.legend_handler import HandlerTuple
    from matplotlib.patches import Patch

    used = {timeline_module.class_name(event) for event in events}
    entries = [
        (COLOURS[name], MEANINGS[name])
        for name in (timeline_module.BLUE, timeline_module.ORANGE, timeline_module.RED)
        if name in used
    ]
    handles = _legend_handles(plt, entries)
    labels = [label for _, label in entries]
    if half:
        # Two swatches in one slot, so the half-dated entry does not read as a
        # second flat orange. A flat patch there would say the wrong thing.
        handles.append(
            (
                Patch(facecolor=COLOURS[timeline_module.BLUE], edgecolor="none"),
                Patch(facecolor=COLOURS[timeline_module.ORANGE], edgecolor="none"),
            )
        )
        labels.append(GRADIENT_MEANING)
    axes.legend(
        handles=handles,
        labels=labels,
        handler_map={tuple: HandlerTuple(ndivide=None, pad=0)},
        loc="lower center",
        bbox_to_anchor=(0.5, 1.01),
        ncol=min(len(handles), 3),
        frameon=False,
        fontsize=7.5,
    )
    return figure


def _gradient_bar(axes, event, y, plt) -> None:
    """A bar that fades from the dated end to the one taken from a neighbour.

    `NoordzeeKust` in `potterlimes` is the case: the file gives the start, the
    end comes from `Wetteraulimes`. Drawing it in plain orange would say the
    whole interval is an estimate, and drawing it blue would say none of it is.
    The published timeline in `CAA2026-alligator` makes the same distinction.
    """
    import numpy as np
    from matplotlib.colors import LinearSegmentedColormap

    fixed = COLOURS[timeline_module.BLUE]
    estimated = COLOURS[timeline_module.ORANGE]
    order = (fixed, estimated) if event.start_fixed else (estimated, fixed)
    axes.imshow(
        np.linspace(0, 1, 256).reshape(1, -1),
        cmap=LinearSegmentedColormap.from_list("fade", order),
        extent=(event.start, event.end, y - 0.29, y + 0.29),
        aspect="auto",
        zorder=3,
    )


def graph_figure(result: Result, plt):
    """The relation graph on a circle, edges coloured by Allen sign.

    A circle rather than a force-directed layout, because a layout that starts
    from a random seed is not reproducible and one that starts from a fixed seed
    only looks reproducible. With twelve events and 68 edges no layout untangles
    this; the colours and the legend are what make it readable, so the edges
    carry no text.
    """
    from matplotlib.patches import FancyArrowPatch

    events = result.events
    count = len(events)
    figure, axes = plt.subplots(figsize=(7.5, 7.5))

    positions = {}
    for index, event in enumerate(events):
        angle = math.pi / 2 - 2 * math.pi * index / count
        positions[event.id] = (math.cos(angle), math.sin(angle))

    signs = [
        sign
        for sign in allen_module.SIGNS
        if any(sign in row.values() for row in result.relations.values())
    ]
    colour_of = {sign: colour for sign, (_, colour) in RELATIONS.items()}

    for one in events:
        for other in events:
            sign = result.relation(one.id, other.id)
            if sign is None:
                continue
            axes.add_patch(
                FancyArrowPatch(
                    positions[one.id],
                    positions[other.id],
                    connectionstyle="arc3,rad=0.14",
                    arrowstyle="-|>",
                    mutation_scale=7,
                    linewidth=0.7,
                    color=colour_of[sign],
                    alpha=0.7,
                    shrinkA=9,
                    shrinkB=9,
                    zorder=1,
                )
            )

    for index, event in enumerate(events):
        x, y = positions[event.id]
        axes.plot([x], [y], marker="o", markersize=7, color="white", zorder=2)
        axes.plot(
            [x],
            [y],
            marker="o",
            markersize=7,
            markerfacecolor="none",
            markeredgecolor=INK,
            markeredgewidth=0.9,
            zorder=3,
        )
        angle = math.pi / 2 - 2 * math.pi * index / count
        axes.text(
            x * 1.13,
            y * 1.13,
            event.name,
            ha="left" if math.cos(angle) > 0.05 else ("right" if math.cos(angle) < -0.05 else "center"),
            va="center",
            fontsize=8,
            zorder=4,
        )

    axes.set_xlim(-1.65, 1.65)
    axes.set_ylim(-1.35, 1.35)
    axes.set_aspect("equal")
    axes.axis("off")
    axes.legend(
        handles=_legend_handles(
            plt,
            [(colour_of[sign], f"{sign}  {RELATIONS[sign][0]}") for sign in signs],
        ),
        loc="lower center",
        bbox_to_anchor=(0.5, -0.06),
        ncol=min(len(signs), 5),
        frameon=False,
        fontsize=7.5,
    )
    return figure


def _ink_on(colour: str | tuple) -> str:
    """Black or white, whichever stands out on that fill.

    Rec. 709 luminance. The published matrix writes white on every cell, which
    is thin on the three palest reds; picking per cell keeps the palette and
    fixes the contrast.
    """
    if isinstance(colour, str):
        red, green, blue = (int(colour[index : index + 2], 16) / 255 for index in (1, 3, 5))
    else:
        red, green, blue = colour[:3]
    return "#1a1a1a" if 0.2126 * red + 0.7152 * green + 0.0722 * blue > 0.55 else "white"


def _matrix_axes(result: Result, plt, size: float):
    figure, axes = plt.subplots(figsize=(size, size))
    names = list(result.names)
    axes.set_xticks(range(len(names)))
    axes.set_yticks(range(len(names)))
    axes.set_xticklabels(names, rotation=90, fontsize=7.5)
    axes.set_yticklabels(names, fontsize=7.5)
    axes.xaxis.set_ticks_position("top")
    axes.set_xticks([x - 0.5 for x in range(len(names) + 1)], minor=True)
    axes.set_yticks([y - 0.5 for y in range(len(names) + 1)], minor=True)
    axes.grid(which="minor", color="white", linewidth=1.0)
    axes.tick_params(which="minor", length=0)
    axes.tick_params(which="major", length=0)
    return figure, axes, names


def matrix_allen_figure(result: Result, plt):
    """The Allen matrix as a coloured table, read as row-relates-to-column.

    Three kinds of cell, and the difference between the last two is the point:
    a relation in its family colour with the name written in; the main diagonal
    in grey with a dash, because an event is not related to itself and the
    question was never asked (D-13); and a pale cell where the question *was*
    asked and there is no answer -- two point events on different years, which
    the Java original leaves blank as well.
    """
    from matplotlib.patches import Rectangle

    count = len(result)
    figure, axes = plt.subplots(figsize=(max(5.5, 0.62 * count + 2.4),) * 2)
    axes.set_facecolor(UNRELATED_FILL)

    for row, one in enumerate(result.events):
        for column, other in enumerate(result.events):
            top = count - row - 1
            if one.id == other.id:
                fill, mark, ink, weight = DIAGONAL_FILL, DIAGONAL_MARK, DIAGONAL_INK, "normal"
            else:
                sign = result.relation(one.id, other.id)
                if sign is None:
                    continue
                mark, fill = RELATIONS[sign]
                ink, weight = _ink_on(fill), "bold"
            axes.add_patch(
                Rectangle(
                    (column, top), 1, 1, facecolor=fill, edgecolor="white", linewidth=1.4
                )
            )
            axes.text(
                column + 0.5,
                top + 0.5,
                mark,
                ha="center",
                va="center",
                fontsize=7,
                color=ink,
                fontweight=weight,
            )

    names = list(result.names)
    axes.set_xlim(0, count)
    axes.set_ylim(0, count)
    axes.set_xticks([index + 0.5 for index in range(count)])
    axes.set_yticks([index + 0.5 for index in range(count)])
    axes.set_xticklabels(names, rotation=45, ha="left", fontsize=7.5)
    axes.set_yticklabels(list(reversed(names)), fontsize=7.5)
    axes.xaxis.set_ticks_position("top")
    axes.xaxis.set_label_position("top")
    axes.tick_params(length=0)
    for spine in axes.spines.values():
        spine.set_visible(False)

    axes.legend(
        handles=_legend_handles(
            plt,
            [
                *FAMILIES,
                (DIAGONAL_FILL, "Not asked (an event against itself)"),
                (UNRELATED_FILL, "Asked, no relation holds"),
            ],
        ),
        loc="upper center",
        bbox_to_anchor=(0.5, -0.02),
        ncol=2,
        fontsize=7.5,
        framealpha=0.9,
        facecolor="white",
        edgecolor=FAINT,
    )
    return figure


def matrix_dist_figure(result: Result, plt):
    """The CA distance matrix as a heat map, values written in where they fit."""
    import numpy as np

    figure, axes, _ = _matrix_axes(result, plt, max(5.0, 0.42 * len(result) + 2.4))
    values = np.array(
        [
            [result.distance(one.id, other.id) for other in result.events]
            for one in result.events
        ]
    )
    image = axes.imshow(values, cmap="cividis", interpolation="nearest")
    if len(result) <= 20:
        limit = values.max()
        for row in range(len(result)):
            for column in range(len(result)):
                value = values[row][column]
                axes.text(
                    column,
                    row,
                    f"{value:.2f}",
                    ha="center",
                    va="center",
                    fontsize=6.5,
                    color="white" if value < limit * 0.55 else "#1a1a1a",
                )
    bar = figure.colorbar(image, ax=axes, fraction=0.045, pad=0.03)
    bar.set_label("weighted CA distance", fontsize=8)
    bar.outline.set_edgecolor(INK)
    return figure


#: Figure name -> the function that draws it. The names match the stems of the
#: data files, so `romanempire_graph.json` and `romanempire_graph.svg` are two
#: views of the same thing.
FIGURES = {
    "timeline": timeline_figure,
    "graph": graph_figure,
    "matrix_allen": matrix_allen_figure,
    "matrix_dist": matrix_dist_figure,
}


def write(result: Result, out_dir: Path, dataset: str, dpi: int = DPI) -> list[Path]:
    """Draw all four figures, each as SVG and JPEG, into `out_dir/img`."""
    plt = _pyplot()
    target = out_dir / "img"
    written: list[Path] = []
    for name, draw in FIGURES.items():
        figure = draw(result, plt)
        try:
            written.extend(_save(figure, target, f"{dataset}_{name}", dpi))
        finally:
            plt.close(figure)
    return written
