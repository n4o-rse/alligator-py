# alligator-py

Allen transformer — a Python port of the Java tool
[`leiza-rse/alligator`](https://github.com/leiza-rse/alligator), turned from a
Tomcat web service into a command-line pipeline that writes files.

Part of the **Alpaka** framework: alligator builds the graph of Allen interval
relations, the [Academic Meta Tool](https://github.com/n4o-rse/amt-engine)
reasons over it.

> **Status: everything but the RDF is written.** Parsing, the CA distance
> model, the dating of floating ends and the Allen relations are in place
> (step S1), and so are the timeline, the graph, both matrices, the Cypher file
> and the figures, all checked against the reference outputs of the Java tool
> (step S2). The two Turtle outputs are step S3 and are still missing; asking
> for them prints a warning and the rest is written anyway. Every phase points
> at the step of the work plan that implements it. See
> [`PRIMER.md`](PRIMER.md).

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
│   └── img/                 the same views as SVG and 300 dpi JPEG
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
```

Useful flags: `--verbose`, `--strict`, `--dataset NAME`, `--out DIR`. The
`alligator` phase additionally takes `--floating-value`, `--dimensions`,
`--formats`, `--dpi`, `--max-neighbour-distance` and `--random-ids`.

### Outputs

| Format | File | |
|---|---|---|
| Timeline | `<ds>_timeline.json` | vis.js items, one per event |
| Graph | `<ds>_graph.json` | vis.js network of the Allen relations |
| Matrices | `<ds>_matrix_allen.*`, `<ds>_matrix_dist.*` | JSON for the web page, CSV for everything else |
| Cypher | `<ds>.cypher` | `CREATE` / `MERGE` / `RETURN`, for Neo4j |
| Figures | `img/<ds>_*.svg`, `img/<ds>_*.jpg` | the same four views, drawn with matplotlib in the palette shared with [`CAA2026-alligator`](https://github.com/leiza-scit/CAA2026-alligator) |
| Turtle | `<ds>.ttl`, `<ds>_amt.ttl` | step S3, not written yet |

`--formats` takes any comma-separated subset of `timeline,graph,matrix,cypher,`
`img,ttl,amt`. The figures are an addition to the interactive page, not a
replacement for it: the page of step S4 stays vis.js and reads the JSON.

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
deterministic identifiers, deterministic ordering, sorted Turtle, fixed number
formats, LF line endings and no timestamps in any generated file. The Java
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
