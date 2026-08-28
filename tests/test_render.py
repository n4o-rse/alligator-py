"""The figures of step S2: four views, each as SVG and as a high-resolution JPEG.

There is no golden file here -- the Java tool never drew anything, the vis.js
app did that in a browser. What can be checked is that the files are what they
claim to be, that they carry the data they are drawn from, and that a second run
produces the same bytes (PRIMER A3), which is the property that lets them be
version controlled at all.

The whole module is skipped where matplotlib is not installed, because a run of
the pipeline without the figures is a supported state: `--formats` can leave
`img` out, and `core.write` degrades to a warning rather than an error.
"""

from __future__ import annotations

from xml.etree import ElementTree

import pytest
from alligator.core import parse_formats, write

pytest.importorskip("matplotlib", reason="the figures need matplotlib")

import wd_repro
from alligator import allen as allen_module
from alligator.outputs import render

#: First bytes of a JFIF file, and the end-of-image marker.
JPEG_MAGIC = b"\xff\xd8\xff"
JPEG_END = b"\xff\xd9"

SVG_ROOT = "{http://www.w3.org/2000/svg}svg"


@pytest.fixture(scope="module")
def figures(romanempire, tmp_path_factory):
    directory = tmp_path_factory.mktemp("figures")
    paths = render.write(romanempire, directory, "romanempire", dpi=150)
    return {path.name: path for path in paths}


def test_all_four_views_are_drawn_in_both_formats(figures):
    assert sorted(figures) == [
        "romanempire_graph.jpg",
        "romanempire_graph.svg",
        "romanempire_matrix_allen.jpg",
        "romanempire_matrix_allen.svg",
        "romanempire_matrix_dist.jpg",
        "romanempire_matrix_dist.svg",
        "romanempire_timeline.jpg",
        "romanempire_timeline.svg",
    ]


def test_the_figure_names_match_the_data_file_names(figures):
    """`romanempire_graph.json` and `romanempire_graph.svg` are one thing twice."""
    assert set(render.FIGURES) == {"timeline", "graph", "matrix_allen", "matrix_dist"}


def test_they_go_into_their_own_directory(romanempire, tmp_path):
    paths = render.write(romanempire, tmp_path, "romanempire", dpi=100)
    assert {path.parent for path in paths} == {tmp_path / "img"}


def test_the_svgs_parse_and_are_svg(figures):
    for name, path in figures.items():
        if path.suffix != ".svg":
            continue
        root = ElementTree.fromstring(path.read_text(encoding="utf-8"))
        assert root.tag == SVG_ROOT, name


def test_the_jpegs_are_jpegs(figures):
    for name, path in figures.items():
        if path.suffix != ".jpg":
            continue
        raw = path.read_bytes()
        assert raw.startswith(JPEG_MAGIC), name
        assert raw.endswith(JPEG_END), name


def test_the_svgs_carry_the_fixed_epoch_rather_than_the_clock(figures):
    """`wd_repro` sets SOURCE_DATE_EPOCH=0, so the date is obviously synthetic.

    A real timestamp here would rewrite one line of every figure on every run,
    which is the failure mode PRIMER A3 exists to prevent.
    """
    for name, path in figures.items():
        if path.suffix != ".svg":
            continue
        text = path.read_text(encoding="utf-8")
        assert "<dc:date>1970-01-01" in text, name


def test_the_hash_salt_survives_a_call_to_rcdefaults():
    """The trap `wd_repro` exists for: rcdefaults() would reset a plain rcParam."""
    import matplotlib

    plt = render._pyplot()
    plt.rcdefaults()
    assert matplotlib.rcParams["svg.hashsalt"] == wd_repro.HASHSALT


def test_two_runs_are_byte_identical(romanempire, tmp_path):
    first = render.write(romanempire, tmp_path / "one", "romanempire", dpi=100)
    second = render.write(romanempire, tmp_path / "two", "romanempire", dpi=100)
    for one, other in zip(first, second):
        assert one.read_bytes() == other.read_bytes(), one.name


def test_a_higher_dpi_gives_a_bigger_jpeg_and_the_same_svg(romanempire, tmp_path):
    low = {p.name: p for p in render.write(romanempire, tmp_path / "low", "r", dpi=100)}
    high = {p.name: p for p in render.write(romanempire, tmp_path / "high", "r", dpi=300)}
    assert high["r_timeline.jpg"].stat().st_size > low["r_timeline.jpg"].stat().st_size
    assert high["r_timeline.svg"].read_bytes() == low["r_timeline.svg"].read_bytes()


def test_the_timeline_figure_draws_one_row_per_event(romanempire):
    plt = render._pyplot()
    figure = render.timeline_figure(romanempire, plt)
    try:
        axes = figure.axes[0]
        assert [label.get_text() for label in axes.get_yticklabels()] == list(
            reversed(romanempire.names)
        )
    finally:
        plt.close(figure)


def test_the_matrix_figures_label_both_axes_with_the_event_names(romanempire):
    """Both matrices, both axes. The Allen matrix draws its rows top-down, so
    its y labels run in reverse; the heat map uses `imshow`, which already
    does."""
    plt = render._pyplot()
    names = list(romanempire.names)
    for draw, y_labels in (
        (render.matrix_allen_figure, list(reversed(names))),
        (render.matrix_dist_figure, names),
    ):
        figure = draw(romanempire, plt)
        try:
            axes = figure.axes[0]
            assert [label.get_text() for label in axes.get_xticklabels()] == names
            assert [label.get_text() for label in axes.get_yticklabels()] == y_labels
        finally:
            plt.close(figure)


def test_the_allen_figure_marks_the_diagonal_as_not_asked(romanempire):
    """The visible half of D-13.

    Not a blank cell: blank is what a pair with no relation gets, and the two
    have to stay apart. The diagonal carries a dash on grey, and there is one
    per event.
    """
    plt = render._pyplot()
    count = len(romanempire)
    figure = render.matrix_allen_figure(romanempire, plt)
    try:
        written = {
            (round(text.get_position()[0] - 0.5), round(text.get_position()[1] - 0.5)):
            text.get_text()
            for text in figure.axes[0].texts
        }
        for index in range(count):
            assert written[(index, count - index - 1)] == render.DIAGONAL_MARK
        relations = sum(len(row) for row in romanempire.relations.values())
        assert len(written) == relations + count
        assert list(written.values()).count(render.DIAGONAL_MARK) == count
    finally:
        plt.close(figure)


def test_the_cells_use_the_shared_family_palette(romanempire):
    """The palette is CAA2026-alligator's, so a relation keeps its colour."""
    assert render.RELATIONS["<"] == ("before", "#4a90d9")
    assert render.RELATIONS["di"] == ("contains", "#d94a4a")
    assert render.RELATIONS["="] == ("equals", "#4caf50")
    assert set(render.RELATIONS) == set(allen_module.SIGNS)


def test_a_half_dated_interval_is_drawn_as_a_gradient(potterlimes):
    """`NoordzeeKust`: fixed start, estimated end. One bar fewer, one image more."""
    plt = render._pyplot()
    figure = render.timeline_figure(potterlimes, plt)
    try:
        assert len(figure.axes[0].images) == 1
    finally:
        plt.close(figure)


def test_the_graph_figure_labels_every_node(romanempire):
    plt = render._pyplot()
    figure = render.graph_figure(romanempire, plt)
    try:
        labels = {text.get_text() for text in figure.axes[0].texts}
        assert labels == set(romanempire.names)
    finally:
        plt.close(figure)


def test_the_img_format_is_written_through_the_phase(romanempire, tmp_path):
    paths = write(romanempire, tmp_path, "romanempire", parse_formats("img"), dpi=100)
    assert len(paths) == 2 * len(render.FIGURES)
    assert all(path.parent.name == "img" for path in paths)
