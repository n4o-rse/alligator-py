"""Smoke tests for the pipeline as a whole.

These check that the repository is wired up and that each phase runs from the
command line, not that anything computes -- the per-module tests do that. The
`amt` phase is the one that needs an optional dependency, so its tests skip
rather than fail when the engine is absent.
"""

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
MAIN = ROOT / "py" / "main.py"

#: The `amt` phase needs an optional dependency; the rest of the pipeline does
#: not. See PRIMER.md, part C, step S6.
ENGINE_INSTALLED = importlib.util.find_spec("amt") is not None


def run_main(*argv: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(MAIN), *argv],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )


def test_list_names_every_phase():
    result = run_main("--list")
    assert result.returncode == 0
    for phase in ("ca", "alligator", "docs", "amt"):
        assert phase in result.stdout


def test_bare_call_lists_phases():
    assert run_main().returncode == 0


def test_the_alligator_phase_writes_every_format(tmp_path):
    """All seven formats are implemented, so a run warns about nothing.

    `--out` keeps the run out of the versioned `output/`: a test that rewrites
    files the repository archives would make `git status` a report about the
    last pytest run rather than about the last change.
    """
    result = run_main("alligator", "--dataset", "romanempire", "--out", str(tmp_path))
    output = result.stderr + result.stdout
    assert result.returncode == 0
    assert "romanempire_timeline.json" in output
    assert "romanempire_amt.ttl" in output
    assert "WARNING" not in output


def test_the_amt_phase_runs_when_the_engine_is_there():
    """Reads `output/`, writes `output/romanempire/amt/`, which is ignored."""
    if not ENGINE_INSTALLED:
        pytest.skip('AMT.engine is optional: pip install -e ".[amt]"')
    result = run_main("amt", "--dataset", "romanempire")
    output = result.stderr + result.stdout
    assert result.returncode == 0
    assert "Validation passed" in output


def test_the_consistency_check_passes_for_both_datasets():
    """Since S6b, once the two axiom defects of D-19 and D-20 were corrected."""
    if not ENGINE_INSTALLED:
        pytest.skip('AMT.engine is optional: pip install -e ".[amt]"')
    for dataset in ("romanempire", "potterlimes"):
        result = run_main("amt", "--dataset", dataset, "--strict")
        output = result.stderr + result.stdout
        assert result.returncode == 0, output
        assert "Consistency check passed" in output
        assert "WARNING" not in output


def test_a_missing_engine_names_the_install_command():
    if ENGINE_INSTALLED:
        pytest.skip("the engine is installed, so the message cannot be provoked")
    result = run_main("amt", "--dataset", "romanempire")
    assert result.returncode == 1
    assert 'pip install -e ".[amt]"' in result.stderr + result.stdout


def test_datasets_are_present():
    for dataset in ("romanempire", "potterlimes"):
        assert (ROOT / "data" / dataset / "counts.csv").is_file()
        assert (ROOT / "data" / dataset / "dates.csv").is_file()


def test_romanempire_agt_has_the_expected_shape():
    text = (ROOT / "data" / "romanempire" / "romanempire.agt").read_text(encoding="utf-8")
    head, _, body = text.partition("#data")
    assert head.replace("\r\n", "").replace("\n", "").split("#")[1:] == ["9999", "true", "1.0|1.0|1.0"]
    rows = [line for line in body.strip().splitlines() if line.strip()]
    assert len(rows) == 13  # header plus twelve events
    assert all(len(row.split("\t")) == 7 for row in rows)


def test_reference_files_are_present():
    reference = ROOT / "tests" / "reference" / "romanempire"
    for name in (
        "matrix_allen.json",
        "matrix_dist.json",
        "timeline.json",
        "graph.json",
        "romanempire.cypher",
        "romanempire.ttl",
        "romanempire_amt.ttl",
    ):
        assert (reference / name).is_file()


def test_an_output_directory_outside_the_repository_is_accepted(tmp_path):
    """`--out` may point anywhere; the log must not raise on the way out."""
    result = run_main(
        "alligator", "--dataset", "romanempire", "--out", str(tmp_path), "--formats", "cypher"
    )
    assert result.returncode == 0, result.stderr
    assert "Traceback" not in result.stderr
    assert (tmp_path / "romanempire" / "romanempire.cypher").is_file()
