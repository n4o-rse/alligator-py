"""Correspondence analysis, ported from the ADP R script.

Origin: alligator-ca/R/2021-05-27_ca_script.R by Allard Mees, the version
running at https://www4.leiza.de/adp/ under "Korrespondenzanalyse".

Runnable on its own:

    python py/ca/ca.py data/romanempire/counts.csv --dates data/romanempire/dates.csv

Implemented in step S5 of the work plan — see PRIMER.md, part C.
"""

from pathlib import Path


def run(counts: Path, dates: Path, out: Path, args) -> list[Path]:
    """Compute the correspondence analysis and write an AGT file."""
    raise NotImplementedError(
        "The ca phase is step S5 of the work plan. See PRIMER.md, part C."
    )
