"""The transformation itself: parse, measure, date, relate.

Port of de.rgzm.alligator.functions.Alligator.

Implemented in steps S1 to S3 of the work plan — see PRIMER.md, part C.
"""

from pathlib import Path


def run(agt: Path, out_dir: Path, args) -> list[Path]:
    """Read an AGT file and write the requested output formats."""
    raise NotImplementedError(
        "The alligator phase is steps S1-S3 of the work plan. See PRIMER.md, part C."
    )
