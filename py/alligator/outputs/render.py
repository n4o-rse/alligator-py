"""Static figures of the three views, as SVG and as a high-resolution JPEG.

The interactive vis.js page of step S4 stays; these are the same three views as
files that can go into a paper, a poster or a Zenodo record without a browser
(PRIMER A4). Four figures per dataset: the timeline, the relation graph, the
Allen matrix and the distance matrix.

Both formats are written from one matplotlib figure, so they cannot drift apart:
the SVG is the archival copy, the JPEG the one that can be pasted anywhere.
JPEG is lossy, which is why it is written at 300 dpi with chroma subsampling
switched off -- the alternative would be blurred edges on the matrix labels.

Byte-identical on a second run, like every other output (PRIMER A3), which needs
three settings that are not matplotlib's defaults: a fixed `svg.hashsalt` so the
generated element identifiers do not move, `Date: None` so no creation date is
written into the SVG metadata, and text rendered as paths so the file does not
depend on which fonts the reader has installed. Byte equality holds for one
installed set of versions; a different matplotlib or libjpeg may lay the same
figure out differently, which is why requirements.txt pins them.

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

#: Fixed salt for the identifiers matplotlib generates inside an SVG. Without
#: it they are drawn from the process and no two runs agree.
HASH_SALT = "alligator-py"

#: The three timeline colours, as the vis.js stylesheet of alligator-app has
#: them, darkened enough to stay legible in print.
COLOURS = {
    timeline_module.BLUE: "#3d6fa5",
    timeline_module.ORANGE: "#dd8a24",
    timeline_module.RED: "#bd4136",
}

#: What the three colours mean, for the legend.
MEANINGS = {
    timeline_module.BLUE: "both ends dated in the file",
    timeline_module.ORANGE: "at least one end from a neighbour",
    timeline_module.RED: "end before start after dating",
}

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
    import matplotlib.pyplot as plt

    matplotlib.rcParams.update(
        {
            "svg.hashsalt": HASH_SALT,
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
    identical on a Linux one (PRIMER A3, A4).
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    svg = out_dir / f"{stem}.svg"
    jpg = out_dir / f"{stem}.jpg"

    buffer = io.BytesIO()
    figure.savefig(buffer, format="svg", bbox_inches="tight", metadata={"Date": None})
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

    for index, event in enumerate(events):
        y = len(events) - 1 - index
        colour = COLOURS[timeline_module.class_name(event)]
        if event.is_point:
            axes.plot(
                [event.start], [y], marker="D", markersize=4.5, color=colour, zorder=3
            )
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

    used = {timeline_module.class_name(event) for event in events}
    axes.legend(
        handles=_legend_handles(
            plt,
            [(COLOURS[name], MEANINGS[name]) for name in (timeline_module.BLUE, timeline_module.ORANGE, timeline_module.RED) if name in used],
        ),
        loc="lower center",
        bbox_to_anchor=(0.5, 1.01),
        ncol=3,
        frameon=False,
        fontsize=7.5,
    )
    return figure


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
    palette = plt.get_cmap("tab20")
    colour_of = {sign: palette(index % 20) for index, sign in enumerate(allen_module.SIGNS)}

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
            [
                (colour_of[sign], f"{sign}  {allen_module.DESCRIPTIONS[sign]}")
                for sign in signs
            ],
        ),
        loc="lower center",
        bbox_to_anchor=(0.5, -0.06),
        ncol=min(len(signs), 5),
        frameon=False,
        fontsize=7.5,
    )
    return figure


def _ink_on(colour) -> str:
    """Black or white, whichever stands out on that cell.

    Rec. 709 luminance. Without this the darker half of the categorical palette
    swallows the sign written on top of it.
    """
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

    The main diagonal is blank, which is the visible half of D-13: an interval
    equalling itself is not a statement about chronology.
    """
    import numpy as np
    from matplotlib.colors import ListedColormap

    figure, axes, _ = _matrix_axes(result, plt, max(5.0, 0.42 * len(result) + 2.2))
    palette = plt.get_cmap("tab20")
    colours = [palette(index % 20) for index in range(len(allen_module.SIGNS))]
    colour_of_sign = dict(zip(allen_module.SIGNS, colours))
    colourmap = ListedColormap(colours)
    colourmap.set_bad("#f2f2f2")

    codes = np.full((len(result), len(result)), np.nan)
    for row, one in enumerate(result.events):
        for column, other in enumerate(result.events):
            sign = result.relation(one.id, other.id)
            if sign is not None:
                codes[row][column] = allen_module.SIGNS.index(sign)

    axes.imshow(
        np.ma.masked_invalid(codes),
        cmap=colourmap,
        vmin=-0.5,
        vmax=len(allen_module.SIGNS) - 0.5,
        interpolation="nearest",
    )
    for row, one in enumerate(result.events):
        for column, other in enumerate(result.events):
            sign = result.relation(one.id, other.id)
            if sign is not None:
                axes.text(
                    column,
                    row,
                    sign,
                    ha="center",
                    va="center",
                    fontsize=7.5,
                    color=_ink_on(colour_of_sign[sign]),
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
