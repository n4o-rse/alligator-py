# alligator-py

Allen transformer — a Python port of the Java tool
[`leiza-rse/alligator`](https://github.com/leiza-rse/alligator), turned from a
Tomcat web service into a command-line pipeline that writes files.

Part of the **Alpaka** framework: alligator builds the graph of Allen interval
relations, the [Academic Meta Tool](https://github.com/n4o-rse/amt-engine)
reasons over it.

> **Status: the `alligator` phase is complete.** Parsing, the CA distance
> model, the dating of floating ends and the Allen relations are in place
> (step S1); the timeline, the graph, both matrices, the Cypher file and the
> figures follow (step S2); and so do the two Turtle outputs, the Alligator
> graph and the Academic Meta Tool file (step S3). All seven are checked
> against the reference outputs of the Java tool. The `amt` phase hands the
> last of them to AMT.engine and closes the Alpaka chain (step S6). Still
> missing are the static web page (S4) and the correspondence analysis that
> writes an `*.agt` (S5); those two phases point at the step of the work plan
> that implements them. See [`PRIMER.md`](PRIMER.md).

## What it does

```
counts.csv + dates.csv  ──[ca]──▶  *.agt  ──[alligator]──▶  output/  ──[docs]──▶  docs/
                                                                │
                                                                └──[amt]──▶  AMT.engine
```

Given an Alligator file (`*.agt`) holding three correspondence-analysis
coordinates and a date range per event, the tool

1. dates every event whose start or end is unknown from its nearest fixed
   neighbour in CA space,
2. derives the Allen interval relation between every pair of events,
3. writes the result as a vis.js timeline, a vis.js graph, two matrices, a
   Neo4j Cypher script, RDF/Turtle and AMT Turtle,
4. and draws the first four of those as figures, each as SVG and as a 300 dpi
   JPEG, for use outside a browser.

## Repository structure

```
alligator-py/
├── data/<dataset>/          input: counts.csv, dates.csv, <dataset>.agt
├── output/<dataset>/        generated results (version-controlled)
│   ├── img/                 the same views as SVG and 300 dpi JPEG
│   └── amt/                 AMT.engine output (reproduced, not archived)
├── docs/                    static GitHub Pages site (generated)
├── py/
│   ├── main.py              single entry point
│   ├── alligator/           the ported logic
│   │   ├── agt.py           AGT reader and writer
│   │   ├── model.py         the event record
│   │   ├── allen.py         Allen interval algebra
│   │   ├── ids.py           deterministic identifiers
│   │   ├── core.py          the transformation
│   │   ├── outputs/         one module per output format
│   │   └── vocab/           static ontology assets
│   ├── ca/ca.py             correspondence analysis
│   ├── wd_repro.py          byte-reproducible matplotlib (shared, verbatim)
│   ├── amt_phase.py         runs AMT.engine over the AMT Turtle
│   └── build_docs.py        assembles docs/ from output/
├── tests/
│   └── reference/           golden files from the Java tool, two datasets
├── reference/
│   └── alligator-java/      the Java sources, vendored for reference only
├── CITATION.cff
├── LICENSE
├── PRIMER.md                design decisions and work plan
├── README.md
├── pyproject.toml
├── requirements.txt         what the pipeline needs
└── requirements-dev.txt     what the tests need
```

## How to run

Tested with **Python 3.10+**.

```bash
git clone https://github.com/n4o-rse/alligator-py.git
cd alligator-py

python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux

pip install -r requirements.txt

python py/main.py --list
python py/main.py all --dataset romanempire
```

Note the `-r`: `pip install requirements.txt` looks for a package of that name
and fails.

### Tests

The test runner is not needed to run the pipeline, so it lives in a separate
file:

```bash
pip install -r requirements-dev.txt
python -m pytest -q
```

Each phase runs on its own as well:

```bash
python py/main.py ca         --dataset romanempire
python py/main.py alligator  --dataset romanempire
python py/main.py docs
python py/main.py amt        --dataset romanempire
```

Useful flags: `--verbose`, `--strict`, `--dataset NAME`, `--out DIR`. The
`alligator` phase additionally takes `--floating-value`, `--dimensions`,
`--formats`, `--dpi`, `--max-neighbour-distance` and `--random-ids`. `all`
takes `--with-amt`.

### Outputs

| Format | File | |
|---|---|---|
| Timeline | `<ds>_timeline.json` | vis.js items, one per event |
| Graph | `<ds>_graph.json` | vis.js network of the Allen relations |
| Matrices | `<ds>_matrix_allen.*`, `<ds>_matrix_dist.*` | JSON for the web page, CSV for everything else |
| Cypher | `<ds>.cypher` | `CREATE` / `MERGE` / `RETURN`, for Neo4j |
| Figures | `img/<ds>_*.svg`, `img/<ds>_*.jpg` | the same four views, drawn with matplotlib in the palette shared with [`CAA2026-alligator`](https://github.com/leiza-scit/CAA2026-alligator) |
| Turtle | `<ds>.ttl` | the events and their Allen relations, OWL-Time |
| AMT | `<ds>_amt.ttl` | the same relations reified and weighted, for AMT.engine |

`--formats` takes any comma-separated subset of `timeline,graph,matrix,cypher,`
`img,ttl,amt`. The figures are an addition to the interactive page, not a
replacement for it: the page of step S4 stays vis.js and reads the JSON.

### The AMT phase

`<ds>_amt.ttl` is written for the [Academic Meta
Tool](https://github.com/n4o-rse/amt-engine), and the `amt` phase is what
actually sends it there. The engine is an optional dependency, so it is not
installed by default:

```bash
pip install -e ".[amt]"
python py/main.py amt --dataset romanempire
```

The engine validates the file against its SHACL shapes, checks the graph for
consistency, applies the Allen composition table as fuzzy role chains and
exports the reasoned graph six ways into `output/<ds>/amt/`: `*.reasoned.ttl`,
`*.cypher`, `*.nodes.csv`, `*.edges.csv`, an interactive `*.html` and a
Markdown run report. On `romanempire` the 68 asserted relations become 138.

Two things are worth knowing before reading the output.

**Validation and the consistency check both pass** — but only since the Allen
axiom block was corrected. Running it through the engine is what exposed two
defects it had carried over from the Java implementation: two
`amt:SelfDisjointAxiom` over roles that are reflexive by definition, and three
rows of the composition table yielding the inverse role where composing with
`equals` must yield the identity. The second of those had turned every
"finishes" relation between events with a shared end into its opposite, which
cost `potterlimes` 22 wrongly inferred edges. Five triples in
`py/alligator/vocab/amt_allen_axioms.ttl`; both are registered as deviations
from the reference and checked against it triple for triple. See `PRIMER.md`,
D-19 and D-20.

**The engine's output is not version-controlled.** It is reproduced by the
command above, not archived, because the engine loads its axioms out of a set
and the order of the `amt:provenance` lists therefore follows string hashing.
The phase pins `PYTHONHASHSEED=0`, which makes a rerun byte-identical on one
machine but not across Python versions. See `PRIMER.md`, D-18.

## The AGT format

```
#9999                                   value marking a floating (unknown) date
#true                                   use the CA dimension weights?
#1.0|1.0|1.0                            weights x|y|z
#data
name	x	y	z	von	bis	fixed       exactly seven tab-separated columns
Vespasian	0.0810	-0.1420	-0.1450	69	79	fixed
DomitianConsulate2	-0.2646	-0.8560	1.0336	9999	9999	floating
```

Parsing is strictly positional — the column names are never read, and both
`von`/`bis`/`fixed` and `from`/`to`/`floating` occur in the wild. A date equal
to the floating value marks that end of the interval as unknown; the two ends
are judged independently, so `120 … 9999` is legal. The full specification is
in [`PRIMER.md`](PRIMER.md), part A7.

## Datasets

| Dataset | Contents |
|---|---|
| `romanempire` | 12 events, one of them floating; the standard smoke test |
| `potterlimes` | the Roman limes correspondence analysis, with real CA weights |

`data/romanempire/counts.csv` and `data/romanempire/romanempire.agt` are both
taken from `alligator-ca`, but they are **not** the same run: one count differs,
so the AGT cannot be reproduced from the CSV. Both are kept as test material;
neither is an acceptance case for the `ca` phase. See `PRIMER.md`, part D.

## Reproducibility

Identical inputs give byte-identical outputs, so `git status` stays clean after
a second run and a diff always means something changed. This requires
deterministic identifiers, deterministic ordering, deterministic blank node
labels, fixed number formats, LF line endings and no timestamps in any
generated file. Turtle is written by `outputs/turtle.py` rather than by
`rdflib.Graph.serialize`, which draws blank node labels from a per-process
counter and so writes a different file every time. The Java
implementation satisfies none of these — the differences are registered in
`PRIMER.md`, part A8.

## Relation to the Java tool

The Java service is still running at <https://tools.leiza.de/alligator/> and is
the reference for the golden files in `tests/reference/`. This is a port, not a
fork: the algorithm is reproduced faithfully, and every intentional deviation
carries a registered reason.

## AI usage

Parts of the Python code in this repository were written with the assistance of
Claude (Anthropic). All AI-assisted code was reviewed, validated and supervised
by Florian Thiery (research software engineering).

## Authors and licence

© 2018–2026 Florian Thiery and Allard W. Mees, LEIZA. Released under the MIT
Licence — see [`LICENSE`](LICENSE).

The Alligator vocabulary in `py/alligator/vocab/alligator.ttl` is published
under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

## Citation

If you use this software, please cite it using the metadata in
[`CITATION.cff`](CITATION.cff).

## Acknowledgements

This work is part of the DFG-funded NFDI initiative, specifically the
[Research Data Infrastructure for the Material Remains of Human History
(NFDI4Objects)](https://www.nfdi4objects.net/) — DFG project number
**501836407**.
