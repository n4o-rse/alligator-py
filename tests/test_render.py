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


def test_the_svgs_carry_no_creation_date(figures):
    """`metadata={"Date": None}`; otherwise every run would differ (PRIMER A3)."""
    for name, path in figures.items():
        if path.suffix == ".svg":
            assert "dc:date" not in path.read_text(encoding="utf-8"), name


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
    plt = render._pyplot()
    for draw in (render.matrix_allen_figure, render.matrix_dist_figure):
        figure = draw(romanempire, plt)
        try:
            axes = figure.axes[0]
            names = list(romanempire.names)
            assert [label.get_text() for label in axes.get_xticklabels()] == names
            assert [label.get_text() for label in axes.get_yticklabels()] == names
        finally:
            plt.close(figure)


def test_the_allen_figure_leaves_the_diagonal_blank(romanempire):
    """The visible half of D-13: no `=` where a row meets its own column."""
    plt = render._pyplot()
    figure = render.matrix_allen_figure(romanempire, plt)
    try:
        axes = figure.axes[0]
        written = {(round(text.get_position()[0]), round(text.get_position()[1])) for text in axes.texts}
        assert all((index, index) not in written for index in range(len(romanempire)))
        assert len(axes.texts) == sum(len(row) for row in romanempire.relations.values())
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
