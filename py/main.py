"""alligator-py — single entry point for the whole pipeline.

Run from the repository root:

    python py/main.py --list
    python py/main.py ca         --dataset romanempire
    python py/main.py alligator  --dataset romanempire
    python py/main.py docs
    python py/main.py amt        --dataset romanempire
    python py/main.py all        --dataset romanempire

Every phase is also runnable on its own; this script only orchestrates. See
PRIMER.md, part C, for what each phase is meant to do and which step of the
work plan implements it.
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

# Paths are resolved relative to the repository root, so the pipeline runs from
# any working directory.
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
OUTPUT_DIR = ROOT / "output"
DOCS_DIR = ROOT / "docs"

sys.path.insert(0, str(ROOT / "py"))

LOG = logging.getLogger("alligator")


# --------------------------------------------------------------------------
# Phases
# --------------------------------------------------------------------------
# Each entry: key -> (one-line description, PRIMER step, callable).
# A phase returns the list of files it wrote.


def phase_ca(args: argparse.Namespace) -> list[Path]:
    """Correspondence analysis: counts + dates -> *.agt."""
    from ca.ca import run

    return run(
        counts=DATA_DIR / args.dataset / "counts.csv",
        dates=DATA_DIR / args.dataset / "dates.csv",
        out=DATA_DIR / args.dataset / f"{args.dataset}.agt",
        args=args,
    )


def phase_alligator(args: argparse.Namespace) -> list[Path]:
    """Allen transformation: *.agt -> the output formats."""
    from alligator.core import run

    return run(
        agt=DATA_DIR / args.dataset / f"{args.dataset}.agt",
        out_dir=OUTPUT_DIR / args.dataset,
        args=args,
    )


def phase_docs(args: argparse.Namespace) -> list[Path]:
    """Assemble the static GitHub Pages site from output/."""
    from build_docs import run

    return run(output_dir=OUTPUT_DIR, docs_dir=DOCS_DIR, args=args)


def phase_amt(args: argparse.Namespace) -> list[Path]:
    """Hand the AMT Turtle file to AMT.engine for reasoning."""
    from amt_phase import run

    return run(
        ttl=OUTPUT_DIR / args.dataset / f"{args.dataset}_amt.ttl",
        out_dir=OUTPUT_DIR / args.dataset / "amt",
        args=args,
    )


PHASES: dict[str, tuple[str, str, object]] = {
    "ca": ("counts + dates -> *.agt (correspondence analysis)", "S5", phase_ca),
    "alligator": (
        "*.agt -> timeline, graph, matrices, cypher, figures, ttl, amt",
        "S1-S3",
        phase_alligator,
    ),
    "docs": ("output/ -> docs/ (static GitHub Pages site)", "S4", phase_docs),
    "amt": ("AMT ttl -> AMT.engine (validate, reason, export)", "S6", phase_amt),
}

# Order used by `all`. The AMT phase is opt-in, because it needs an optional
# dependency that a plain `pip install -r requirements.txt` does not bring:
# `all` runs it only when `--with-amt` is given.
DEFAULT_ORDER = ["ca", "alligator", "docs"]


# --------------------------------------------------------------------------
# Command line
# --------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python py/main.py",
        description="alligator-py — Allen transformer pipeline.",
    )
    parser.add_argument(
        "phase",
        nargs="?",
        choices=[*PHASES, "all"],
        help="phase to run; 'all' runs %s in order" % ", ".join(DEFAULT_ORDER),
    )
    parser.add_argument("--list", action="store_true", help="list the phases and exit")
    parser.add_argument("--dataset", default="romanempire", help="dataset under data/")
    parser.add_argument("--out", type=Path, default=None, help="override the output directory")
    parser.add_argument("--verbose", action="store_true", help="debug-level logging")
    parser.add_argument(
        "--strict", action="store_true", help="turn warnings into errors and stop"
    )
    parser.add_argument(
        "--with-amt",
        action="store_true",
        help="let 'all' run the amt phase too; needs the optional [amt] extra",
    )

    group = parser.add_argument_group("alligator phase")
    group.add_argument(
        "--floating-value",
        type=float,
        default=None,
        help="override the floating-date marker from the AGT metadata",
    )
    group.add_argument(
        "--dimensions",
        default=None,
        help="override the CA dimension weights, e.g. 0.365|0.149|0.145",
    )
    group.add_argument(
        "--formats",
        default="timeline,graph,matrix,cypher,img,ttl,amt",
        help=(
            "comma-separated list of output formats to write; 'img' draws the "
            "four figures as SVG and JPEG"
        ),
    )
    group.add_argument(
        "--dpi",
        type=int,
        default=300,
        help="resolution of the JPEG figures; the SVG does not have one",
    )
    group.add_argument(
        "--max-neighbour-distance",
        type=float,
        default=200.0,
        help="largest CA distance still accepted as a nearest fixed neighbour",
    )
    group.add_argument(
        "--random-ids",
        action="store_true",
        help="use random Hashids like the Java implementation (not reproducible)",
    )
    return parser


def relative(path: Path | str) -> Path:
    """A path for the log: relative to the repository, absolute if it is outside.

    `--out` may point anywhere, and `Path.relative_to` raises rather than
    falling back, so a run writing outside the repository used to end in a
    traceback after every file had already been written correctly.
    """
    path = Path(path)
    try:
        return path.relative_to(ROOT)
    except ValueError:
        return path


def print_phases() -> None:
    width = max(len(k) for k in PHASES)
    print("Phases (see PRIMER.md, part C):\n")
    for key, (description, step, _) in PHASES.items():
        print(f"  {key:<{width}}  {step:<6}  {description}")
    print(f"\n  {'all':<{width}}  {'':<6}  runs {', '.join(DEFAULT_ORDER)} in order")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)-7s %(message)s",
    )

    if args.list or args.phase is None:
        print_phases()
        return 0

    if args.out is not None:
        globals()["OUTPUT_DIR"] = args.out

    order = DEFAULT_ORDER if args.phase == "all" else [args.phase]
    if args.phase == "all" and args.with_amt:
        order = [*order, "amt"]
    failures = 0

    for number, key in enumerate(order, start=1):
        description, step, function = PHASES[key]
        LOG.info("[%d/%d] %s (%s) — %s", number, len(order), key, step, description)
        started = time.perf_counter()
        try:
            written = function(args) or []
        except NotImplementedError as error:
            LOG.warning("%s", error)
            failures += 1
            if args.strict:
                return 1
            continue
        except Exception as error:
            # An AlligatorError is a diagnosis the code made on purpose -- a
            # missing input, an unusable option, a failed dependency. Printing
            # a traceback over it hides the sentence the user needs to read.
            from alligator.core import AlligatorError

            if isinstance(error, AlligatorError):
                LOG.error("%s", error)
            else:
                LOG.exception("phase %s failed", key)
            return 1
        elapsed = time.perf_counter() - started
        for path in written:
            LOG.info("      wrote %s", relative(path))
        LOG.info("      done in %.1f s", elapsed)

    return 1 if failures and args.strict else 0


if __name__ == "__main__":
    raise SystemExit(main())
