"""Shared fixtures.

`py/` is put on the path here rather than in every test module, which is also
what `python py/main.py` does at runtime.
"""

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "py"))

REFERENCE = ROOT / "tests" / "reference"


@pytest.fixture(scope="session")
def root() -> Path:
    return ROOT


@pytest.fixture(scope="session")
def romanempire():
    """The calculated result for the twelve Roman events."""
    from alligator.core import calculate_file

    return calculate_file(ROOT / "data" / "romanempire" / "romanempire.agt")


@pytest.fixture(scope="session")
def potterlimes():
    """The eight limes events, with real CA weights and one half-floating event."""
    from alligator.core import calculate_file

    return calculate_file(ROOT / "data" / "potterlimes" / "potterlimes.agt")


def _load(dataset: str, name: str):
    path = REFERENCE / dataset / name
    if path.suffix == ".json":
        return json.loads(path.read_text(encoding="utf-8"))
    return path.read_text(encoding="utf-8")


@pytest.fixture(scope="session")
def golden():
    """The Java reference outputs for `romanempire`, by short name.

    All seven formats. Six separate API calls, so the identifiers differ from
    file to file (PRIMER A8, D-01).
    """
    return {
        "matrix_allen": _load("romanempire", "matrix_allen.json"),
        "matrix_dist": _load("romanempire", "matrix_dist.json"),
        "timeline": _load("romanempire", "timeline.json"),
        "graph": _load("romanempire", "graph.json"),
        "cypher": _load("romanempire", "romanempire.cypher"),
        "ttl": _load("romanempire", "romanempire.ttl"),
        "amt": _load("romanempire", "romanempire_amt.ttl"),
    }


@pytest.fixture(scope="session")
def golden_potterlimes():
    """The Java reference outputs for `potterlimes`, from grapHNR23.

    Only three formats: that repository published the Cypher, the Turtle and
    the AMT file and nothing else. See tests/reference/README.md.
    """
    return {
        "cypher": _load("potterlimes", "potterlimes.cypher"),
        "ttl": _load("potterlimes", "potterlimes.ttl"),
        "amt": _load("potterlimes", "potterlimes_amt.ttl"),
        "agt": _load("potterlimes", "potterlimes.agt"),
    }
