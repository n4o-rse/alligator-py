"""Hand the generated AMT Turtle file to AMT.engine.

This is the last link of the chain: the `alligator` phase writes
`<dataset>_amt.ttl`, and this phase lets the engine validate it against the AMT
SHACL shapes, run the fuzzy reasoning over the Allen axioms and export the
result. See PRIMER.md, part C, step S6.

Why not a copy of `run_amt.py`
------------------------------
`amt-runner` exists for projects without a packaging setup: it clones the
engine into a cache and pip-installs three packages into the running
interpreter, every time, from inside the script. Both are side effects this
repository cannot afford -- part A3 asks that a fresh clone plus one install
step reproduce every file, and a build script that installs packages while it
runs is the opposite of that. We have a `pyproject.toml`, so the engine is
declared where dependencies belong, as the optional extra `[amt]` pinned to a
commit. What is left is the small part: point the engine at one file, put its
output where the rest of the pipeline puts output, and read its exit report.

`python -m amt.runner`, not the library API
-------------------------------------------
The engine loads its axioms through `for atype in axiom_types:` over a `set`
of URIRefs (`amt/core.py`), so the order in which RoleChain and Inverse axioms
are applied follows string hashing. The reasoned graph is the same either way,
but the order of the `amt:provenance` lists is not, and three of the six output
files carry provenance. `PYTHONHASHSEED=0` pins it -- and an environment
variable has to be set before the interpreter starts, which is why this phase
spends a subprocess instead of importing the engine.

That makes a run repeatable on one machine, not across Python versions: the
seeded string hash changed algorithm in 3.11. So the engine's output stays
git-ignored for now (`.gitignore`, PRIMER D-18). The fix belongs upstream and
is one word -- `sorted(axiom_types, key=str)` -- after which this phase can
drop the environment variable and the output can be versioned like everything
else.

Consistency violations
----------------------
There are none, for either dataset, and that is the result of step S6b rather
than of this phase. Running the file through the engine is what exposed the two
defects the Allen axiom block had inherited from the Java implementation: two
`SelfDisjointAxiom` over reflexive roles, and three rows of the composition
table yielding the inverse role where they should yield the identity. Both are
corrected in `vocab/amt_allen_axioms.ttl` and registered as PRIMER D-19 and
D-20.

`review` stays as a guard, and it distinguishes two kinds. A self-loop is the
axiom block arguing with itself; if one reappears, it is a warning and
`--strict` makes it a failure. A `DisjointAxiom` violation is a failure
regardless, because it says two contradicting relations hold between two
*different* events, which no axiom explains and which would be about our data.

Implemented in step S6 of the work plan.
"""

from __future__ import annotations

import importlib.util
import logging
import os
import re
import subprocess
import sys
from pathlib import Path

from alligator.core import AlligatorError

LOG = logging.getLogger("alligator.amt")

#: The engine's own full-pipeline entry point: validate, load, check, reason,
#: export. Running it rather than the six library calls means a new export
#: format upstream arrives here without a change.
ENGINE_ENTRY = "amt.runner"

#: Shown when the optional extra is not installed.
INSTALL_HINT = 'pip install -e ".[amt]"'

#: What the engine writes, named after the stem of its input. The order is the
#: one it writes them in.
OUTPUT_SUFFIXES = (
    ".reasoned.ttl",
    ".cypher",
    ".nodes.csv",
    ".edges.csv",
    ".html",
    ".report.md",
)

#: Text outputs that the engine writes with CRLF. Rewritten to LF so the files
#: match the rest of the repository (PRIMER A3, `outputs/files.py`).
CRLF_SUFFIXES = (".nodes.csv", ".edges.csv")

#: A violation that would follow from the axiom block rather than from our
#: data. Every self-loop does: it means the block derives reflexivity for a
#: role and forbids it in the same breath, which is what D-19 and D-20 were.
#: Nothing matches this today; it is here so that a regression reads as one.
KNOWN_VIOLATION = re.compile(r"SelfDisjointAxiom violated: \S+ has self-loop via \S+$")

#: Lines of the engine's own log worth repeating at info level. Everything
#: else is kept for `--verbose`.
INTERESTING = ("OK ", "FAIL", "WARN", "VAL ")


def run(ttl: Path, out_dir: Path, args) -> list[Path]:
    """Validate, reason and export one AMT Turtle file. Returns what was written."""
    ttl = Path(ttl)
    out_dir = Path(out_dir)
    strict = getattr(args, "strict", False)
    verbose = getattr(args, "verbose", False)

    if not ttl.is_file():
        raise AlligatorError(
            f"no AMT Turtle file at {ttl}. Run the alligator phase first: "
            f"python py/main.py alligator --dataset {ttl.stem.removesuffix('_amt')}"
        )
    require_engine()

    out_dir.mkdir(parents=True, exist_ok=True)
    lines = invoke(ttl, out_dir, verbose=verbose)

    written = [
        path for path in (out_dir / (ttl.stem + s) for s in OUTPUT_SUFFIXES) if path.is_file()
    ]
    # Before the review, not after: `review` raises under --strict, and a run
    # that stops there would otherwise leave the CSVs behind with the line
    # endings the engine happened to write.
    normalise_newlines(written)

    review(lines, strict=strict)
    return written


def require_engine() -> None:
    """Fail with the install command rather than with an ImportError."""
    if importlib.util.find_spec("amt") is None:
        raise AlligatorError(
            f"AMT.engine is not installed. It is an optional dependency: {INSTALL_HINT}"
        )
    LOG.debug("      engine %s", engine_version() or "of unknown version")


def engine_version() -> str | None:
    """The installed engine version, or None if it does not report one."""
    try:
        from importlib.metadata import PackageNotFoundError, version

        return version("amt")
    except (ImportError, PackageNotFoundError):
        return None


def invoke(ttl: Path, out_dir: Path, *, verbose: bool) -> list[str]:
    """Run the engine in a subprocess and return its output, line by line.

    The engine empties its output directory before writing, so every run
    leaves exactly the six files of `OUTPUT_SUFFIXES` behind and nothing from
    a previous dataset.
    """
    command = [sys.executable, "-m", ENGINE_ENTRY, str(ttl), "-o", str(out_dir)]
    environment = {**os.environ, "PYTHONHASHSEED": "0"}
    LOG.debug("      $ PYTHONHASHSEED=0 %s", " ".join(command))

    completed = subprocess.run(
        command,
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    lines = [line.rstrip() for line in (completed.stdout + completed.stderr).splitlines()]

    for line in lines:
        if verbose:
            LOG.debug("      | %s", line)
        elif line.startswith(INTERESTING) and " wrote " not in line:
            # The engine names its outputs with absolute paths; main.py lists
            # the same six files relative to the repository afterwards.
            LOG.info("      %s", line)

    if completed.returncode != 0:
        raise AlligatorError(
            f"AMT.engine exited with {completed.returncode}. "
            f"Re-run with --verbose to see its full output."
        )
    return lines


def review(lines: list[str], *, strict: bool) -> None:
    """Sort the reported consistency violations into known and unknown ones."""
    violations = [
        line.strip()
        for line in lines
        if line.strip().startswith("- ") and "violated" in line
    ]
    if not violations:
        return

    known = [v for v in violations if KNOWN_VIOLATION.search(v)]
    unknown = [v for v in violations if v not in known]

    if known:
        LOG.warning(
            "      %d self-loop(s): the axiom block derives a reflexive role "
            "and forbids it at once, as in PRIMER D-19 and D-20",
            len(known),
        )
    for violation in unknown:
        LOG.error("      %s", violation)

    if unknown:
        raise AlligatorError(
            f"{len(unknown)} consistency violation(s) that the axiom block does "
            f"not explain. These are about the data, not about the axioms."
        )
    if strict:
        raise AlligatorError(f"{len(known)} self-loop(s), and --strict was given.")


def normalise_newlines(paths: list[Path]) -> None:
    """Rewrite the engine's CRLF exports to LF, in place.

    Only the two CSV files are affected; `csv.writer` on the engine's side
    writes `\\r\\n` on every platform. Git would normalise them on commit
    anyway (`.gitattributes`), but the promise of part A3 is about the working
    tree, not about the index.
    """
    for path in paths:
        if not path.name.endswith(CRLF_SUFFIXES):
            continue
        raw = path.read_bytes()
        if b"\r\n" in raw:
            path.write_bytes(raw.replace(b"\r\n", b"\n"))
            LOG.debug("      normalised line endings in %s", path.name)
