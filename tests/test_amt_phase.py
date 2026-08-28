"""The AMT phase of step S6: the file, through AMT.engine, into `output/*/amt/`.

Two halves. The first runs without the optional dependency and checks the parts
that are ours -- the classification of consistency violations, the line-ending
fix, the message when the engine is missing. The second is skipped unless the
`[amt]` extra is installed, and runs the real engine over the real file; it is
the only test in the suite that shells out.

The engine's own behaviour is not retested here. What is worth pinning down is
the boundary: that a violation of the known shape stays a warning and anything
else becomes an error, because that decision is what makes a failing
consistency check readable rather than alarming (PRIMER D-19).
"""

from __future__ import annotations

import importlib.util
from types import SimpleNamespace

import amt_phase
import pytest
from alligator.core import AlligatorError

ENGINE_INSTALLED = importlib.util.find_spec("amt") is not None

#: Two lines as the engine prints them, one of each kind.
KNOWN = "  - SelfDisjointAxiom violated: eVFHT5DGC has self-loop via e"
ALSO_KNOWN = "  - SelfDisjointAxiom violated: eNICCMT3N has self-loop via fi"
UNKNOWN = "  - DisjointAxiom violated: eJ3OUJL6G has both b and a to eIR666UI7"


def options(**overrides) -> SimpleNamespace:
    defaults = {"strict": False, "verbose": False, "dataset": "romanempire"}
    return SimpleNamespace(**{**defaults, **overrides})


# ---------------------------------------------------------------------------
# Without the engine
# ---------------------------------------------------------------------------
def test_known_violations_are_a_warning_not_a_failure():
    amt_phase.review([KNOWN, ALSO_KNOWN], strict=False)


def test_an_unexplained_violation_fails():
    with pytest.raises(AlligatorError, match="not explain"):
        amt_phase.review([KNOWN, UNKNOWN], strict=False)


def test_strict_promotes_the_known_ones():
    with pytest.raises(AlligatorError, match="--strict"):
        amt_phase.review([KNOWN], strict=True)


def test_a_clean_run_says_nothing():
    amt_phase.review(["OK   Consistency check passed."], strict=True)


def test_a_disjoint_violation_is_not_a_self_loop_and_stays_unknown():
    """The line the classification exists to draw.

    A self-loop is the axiom block arguing with itself. A DisjointAxiom
    violation says two contradicting relations hold between two *different*
    events, and no axiom explains that -- it would be about the data.
    """
    assert amt_phase.KNOWN_VIOLATION.search(UNKNOWN) is None
    assert amt_phase.KNOWN_VIOLATION.search(KNOWN) is not None


def test_a_missing_input_names_the_phase_that_writes_it(tmp_path):
    with pytest.raises(AlligatorError, match="alligator --dataset romanempire"):
        amt_phase.run(tmp_path / "romanempire_amt.ttl", tmp_path / "amt", options())


def test_the_csv_exports_are_rewritten_to_lf(tmp_path):
    csv = tmp_path / "x.nodes.csv"
    csv.write_bytes(b"iri,label\r\nae:a,Galba\r\n")
    keep = tmp_path / "x.reasoned.ttl"
    keep.write_bytes(b"# left alone\r\n")

    amt_phase.normalise_newlines([csv, keep])

    assert csv.read_bytes() == b"iri,label\nae:a,Galba\n"
    assert keep.read_bytes() == b"# left alone\r\n"


# ---------------------------------------------------------------------------
# With the engine
# ---------------------------------------------------------------------------
needs_engine = pytest.mark.skipif(
    not ENGINE_INSTALLED, reason='AMT.engine is optional: pip install -e ".[amt]"'
)


@pytest.fixture(scope="module")
def engine_run(root, tmp_path_factory):
    if not ENGINE_INSTALLED:
        pytest.skip('AMT.engine is optional: pip install -e ".[amt]"')
    directory = tmp_path_factory.mktemp("amt")
    ttl = root / "output" / "romanempire" / "romanempire_amt.ttl"
    written = amt_phase.run(ttl, directory, options())
    return {path.name.removeprefix("romanempire_amt"): path for path in written}


@needs_engine
def test_the_engine_writes_all_six_formats(engine_run):
    assert set(engine_run) == set(amt_phase.OUTPUT_SUFFIXES)


@needs_engine
def test_the_file_passes_the_shacl_shapes(engine_run):
    """The point of the whole phase: our AMT Turtle is valid AMT."""
    report = engine_run[".report.md"].read_text(encoding="utf-8")
    assert "Validation passed" in report


@needs_engine
def test_reasoning_adds_edges_without_losing_any(engine_run):
    reasoned = engine_run[".reasoned.ttl"].read_text(encoding="utf-8")
    assert reasoned.count("rdf:subject") > 68


@needs_engine
def test_a_strict_run_still_leaves_normalised_files(root, tmp_path):
    """`review` raises last, so a stopped run does not leave CRLF behind."""
    ttl = root / "output" / "romanempire" / "romanempire_amt.ttl"
    with pytest.raises(AlligatorError, match="--strict"):
        amt_phase.run(ttl, tmp_path, options(strict=True))
    assert b"\r\n" not in (tmp_path / "romanempire_amt.nodes.csv").read_bytes()


@needs_engine
def test_a_second_run_is_byte_identical(engine_run, root, tmp_path_factory):
    """Per machine, thanks to PYTHONHASHSEED=0. Not across versions -- D-18."""
    directory = tmp_path_factory.mktemp("amt-again")
    ttl = root / "output" / "romanempire" / "romanempire_amt.ttl"
    again = {p.name.removeprefix("romanempire_amt"): p for p in amt_phase.run(ttl, directory, options())}
    for suffix in (".reasoned.ttl", ".cypher", ".nodes.csv", ".edges.csv"):
        assert again[suffix].read_bytes() == engine_run[suffix].read_bytes(), suffix
