"""Assemble the static GitHub Pages site from the generated output.

The site is a viewer for committed results: it reads docs/data/<dataset>/*.json
and never calls an API. See PRIMER.md, part C, step S4.
"""

from pathlib import Path


def run(output_dir: Path, docs_dir: Path, args) -> list[Path]:
    """Copy the JSON views into docs/ and refresh the dataset index."""
    raise NotImplementedError(
        "The docs phase is step S4 of the work plan. See PRIMER.md, part C."
    )
