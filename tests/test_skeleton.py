"""Smoke tests for the pipeline scaffolding.

These check that the repository is wired up, not that anything computes. Real
tests arrive with step S1 of the work plan.
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAIN = ROOT / "py" / "main.py"


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


def test_unimplemented_phase_warns_but_does_not_crash():
    result = run_main("alligator", "--dataset", "romanempire")
    assert result.returncode == 0
    assert "S1" in result.stderr or "S1" in result.stdout


def test_strict_makes_an_unimplemented_phase_fail():
    assert run_main("alligator", "--dataset", "romanempire", "--strict").returncode == 1


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
