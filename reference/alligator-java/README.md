# alligator (Java) — reference copy

This is the implementation alligator-py is ported from, kept here **for reading
only**. It is not built, not run and not modified by anything in this
repository; it exists so that a question about the original behaviour can be
answered from the same checkout as the answer.

## Origin

| | |
|---|---|
| Source | <https://github.com/leiza-rse/alligator> |
| Running service | <https://tools.leiza.de/alligator/> |
| Licence | MIT, © 2018–2026 Florian Thiery / LEIZA |
| Vendored | 2026-08-28 |
| Upstream commit | **TODO** — record the commit SHA this copy was taken from |

The upstream commit matters: without it, a difference between the Python and the
Java behaviour cannot be told apart from a change made upstream after this copy
was taken. Fill it in before the first release.

## What was left out

Only the parts that are consulted while porting were vendored. Omitted from
upstream: `docs/` (generated Maven and Javadoc output), `logo/`, the bundled
PDF, `nbproject/` and the NetBeans configuration files.

Kept, and why:

| Path | Why |
|---|---|
| `src/main/java/` | the algorithm — 21 classes, ~3 900 lines |
| `src/main/resources/` | `config.properties`, `prefixes.csv`, `pom.properties` |
| `src/main/webapp/` | `openapi.yaml` documents the six endpoints the ported CLI replaces |
| `pom.xml` | shows which libraries the Java version pulled in (Hashids, json-simple, Jena, RDF4J) |
| `CITATION.cff`, `LICENSE` | the upstream metadata this port cites and continues |

## Where to look

| Question | Class |
|---|---|
| How is an AGT file parsed? | `rest/AlligatorAPI.java` (metadata split) and `functions/Alligator.java` (`writeToAlligatorEventList`) |
| How are distances weighted? | `functions/Alligator.java`, `distance3D` |
| How are floating dates resolved? | `functions/Alligator.java`, `getNextFixedNeighbours` |
| Which Allen relation holds? | `allen/AllenInttervalAlgebra.java` |
| What does an output format contain? | `functions/{Timeline,Graph,MatrixAllen,MatrixDist,Cypher,RDFEvents,AMTEvents}.java` |
| Where do the AMT axioms come from? | `functions/AMTEvents.java`, the hard-coded Turtle in `writeRDFAsText` |

The known defects in this code are registered in `PRIMER.md`, part A8, with the
evidence for each. Read that table before concluding that a difference in
alligator-py is a porting mistake.

## Upstream README

The original project README is preserved as `README.upstream.md`.
