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

REFERENCE = ROOT / "tests" / "reference" / "romanempire"


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


@pytest.fixture(scope="session")
def golden():
    """The Java reference outputs, by short name."""

    def load(name: str):
        path = REFERENCE / name
        if path.suffix == ".json":
            return json.loads(path.read_text(encoding="utf-8"))
        return path.read_text(encoding="utf-8")

    return {
        "matrix_allen": load("matrix_allen.json"),
        "matrix_dist": load("matrix_dist.json"),
        "timeline": load("timeline.json"),
        "graph": load("graph.json"),
    }
