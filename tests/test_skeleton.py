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


def test_the_alligator_phase_writes_its_s2_outputs():
    """S2 is implemented; the RDF formats are still S3 and only warn."""
    result = run_main("alligator", "--dataset", "romanempire")
    assert result.returncode == 0
    assert "romanempire_timeline.json" in result.stderr + result.stdout
    assert "S3" in result.stderr + result.stdout


def test_unimplemented_phase_warns_but_does_not_crash():
    result = run_main("amt", "--dataset", "romanempire")
    assert result.returncode == 0
    assert "S6" in result.stderr + result.stdout


def test_strict_makes_an_unimplemented_phase_fail():
    assert run_main("amt", "--dataset", "romanempire", "--strict").returncode == 1


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
