# alligator-py

Allen transformer — a Python port of the Java tool
[`leiza-rse/alligator`](https://github.com/leiza-rse/alligator), turned from a
Tomcat web service into a command-line pipeline that writes files.

Part of the **Alpaka** framework: alligator builds the graph of Allen interval
relations, the [Academic Meta Tool](https://github.com/n4o-rse/amt-engine)
reasons over it.

> **Status: skeleton.** Only the pipeline scaffolding exists so far. Every
> phase raises `NotImplementedError` and points at the step of the work plan
> that implements it. See [`PRIMER.md`](PRIMER.md).

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
3. writes the result as RDF/Turtle, AMT Turtle, Neo4j Cypher, a vis.js
   timeline, a vis.js graph and two matrices.

## Repository structure

```
alligator-py/
├── data/<dataset>/          input: counts.csv, dates.csv, <dataset>.agt
├── output/<dataset>/        generated results (version-controlled)
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
│   └── build_docs.py        assembles docs/ from output/
├── tests/
│   └── reference/           golden files from the Java tool
├── CITATION.cff
├── LICENSE
├── PRIMER.md                design decisions and work plan
├── README.md
├── pyproject.toml
└── requirements.txt
```

## How to run

Tested with **Python 3.10+**.

```bash
git clone https://github.com/leiza-rse/alligator-py.git
cd alligator-py

python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux

pip install -r requirements.txt

python py/main.py --list
python py/main.py all --dataset romanempire
```

Each phase runs on its own as well:

```bash
python py/main.py ca         --dataset romanempire
python py/main.py alligator  --dataset romanempire
python py/main.py docs
```

Useful flags: `--verbose`, `--strict`, `--dataset NAME`, `--out DIR`. The
`alligator` phase additionally takes `--floating-value`, `--dimensions`,
`--formats`, `--max-neighbour-distance` and `--random-ids`.

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
