# Golden files

Reference output from the Java implementation at
<https://tools.leiza.de/alligator/>, used to check the port.

## romanempire/

Produced from `data/romanempire/romanempire.agt` at an earlier state of the
service. Two caveats, both from `PRIMER.md`:

1. **Each file has different identifiers.** They come from six separate API
   calls, and the Java implementation draws a fresh random Hashid per event on
   every call (A8, D-01). Comparisons must be keyed on `rdfs:label` or
   `content`, never on the identifier.
2. **Two known intentional deviations.** The Cypher file contains `DURINGi`,
   `MEETSi` and `OVERLAPSi` instead of `CONTAINS`, `MET_BY` and
   `OVERLAPPED_BY` (A8, D-02), and the matrix, graph and Cypher files contain
   self-relations that alligator-py excludes (A8, D-13). Tests must name these
   as explicit exceptions rather than loosening the comparison.

Two further quirks are visible here and are worth knowing before comparing
literally: the distance matrix uses a comma as the decimal separator, because
the Java `DecimalFormat` picks up the server locale (D-10), and the AMT file
writes untyped weight literals where AMT.engine expects `xsd:decimal` (D-06).

| File | Endpoint |
|---|---|
| `matrix_allen.json` | `/matrixallen` |
| `matrix_dist.json` | `/matrixdist` |
| `timeline.json` | `/timeline` |
| `graph.json` | `/graph` |
| `romanempire.cypher` | `/cypher` |
| `romanempire.ttl` | `/turtle` |
| `romanempire_amt.ttl` | `/amt` |

**To do before step S1 is closed:** pull all seven outputs again in one
session, from one input file, and record which version of the service produced
them. Until then these files are indicative, not authoritative.
