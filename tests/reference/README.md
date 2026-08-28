# Golden files

Reference output from the Java implementation, used to check the port. Two sets,
with different provenance and different coverage.

Both sets share two caveats from `PRIMER.md`:

1. **Identifiers are not comparable.** The Java implementation draws a fresh
   random Hashid per event on every call (A8, D-01), so identifiers differ
   between files and between sets. Comparisons must be keyed on `rdfs:label`,
   `content` or the Cypher `label`, never on the identifier.
2. **Two known intentional deviations.** The Cypher files contain `DURINGi`,
   `MEETSi` and `OVERLAPSi` instead of `CONTAINS`, `MET_BY` and
   `OVERLAPPED_BY` (A8, D-02), and the matrix, graph and Cypher files contain
   self-relations that alligator-py excludes (A8, D-13). Tests name these as
   explicit exception tables rather than loosening the comparison.

## romanempire/

Produced from `data/romanempire/romanempire.agt` at an earlier state of the
service at <https://tools.leiza.de/alligator/>. Six separate API calls, so each
file carries its own identifiers. Covers all seven outputs.

| File | Endpoint |
|---|---|
| `matrix_allen.json` | `/matrixallen` |
| `matrix_dist.json` | `/matrixdist` |
| `timeline.json` | `/timeline` |
| `graph.json` | `/graph` |
| `romanempire.cypher` | `/cypher` |
| `romanempire.ttl` | `/turtle` |
| `romanempire_amt.ttl` | `/amt` |

Two further quirks are visible here and are worth knowing before comparing
literally: the distance matrix uses a comma as the decimal separator, because
the Java `DecimalFormat` picks up the server locale (D-10), and the AMT file
writes untyped weight literals where AMT.engine expects `xsd:decimal` (D-06).

## potterlimes/

Taken on 2026-08-28 from <https://github.com/leiza-scit/grapHNR23> at commit
`d54304e`, where they were published on 2024-04-30 as the supplementary data of
that repository. This is the second, weighted dataset — CA weights
`0.365|0.149|0.145`, and `NoordzeeKust` with a fixed start and a floating end.

| File | Original name in grapHNR23 |
|---|---|
| `potterlimes.agt` | `src/limes_HadriansWall_NoordzeeKust.agt` |
| `potterlimes.cypher` | `data/limes_HadriansWall_NoordzeeKust.cypher` |
| `potterlimes.ttl` | `data/limes_HadriansWall_NoordzeeKust.ttl` |
| `potterlimes_amt.ttl` | `data/limes_HadriansWall_NoordzeeKust_amt.ttl` |

Renamed to the dataset, so the two sets read the same way; nothing else was
touched. Checksums of the files as copied:

```
d737649f153e5eb75da3ce11b9bf158206495a164162d9d2f1d5ada4c9751fa1  potterlimes.agt
be9f1a24ba48e19761133de44fedb10e5440e2c16f32aede03f345a6ceee7240  potterlimes.cypher
39bb159a9c8447f12631f90c3832cdef9d359073cc790406a2059ef0ee6ea56c  potterlimes.ttl
0c3211d18eb096af345038b7210ebdfc588449a7ed1e350315936d097824bfa6  potterlimes_amt.ttl
```

**The input is the same file as `data/potterlimes/potterlimes.agt`**, byte for
byte apart from the header line, which reads `from`/`to` there and `von`/`bis`
here. The parser never reads the column names (A7), so the two are the same
input, and the AGT is kept alongside the outputs to make that checkable.

Three things this set does *not* give us, and one warning:

- **No timeline, graph or matrix.** grapHNR23 published only the Cypher, the
  Turtle and the AMT file. The four JSON outputs are checked against
  `romanempire/` alone.
- **Still one call per file.** Same as the other set: the identifiers differ
  between the three files, so this is not the single-session pull that part D
  of the PRIMER asks for either.
- **No recorded service version.** The files predate this repository and
  `POM.getInfo()` was not captured.
- **The namespaces are inconsistent within grapHNR23 itself.** `potterlimes.ttl`
  uses `alligator: <http://archaeology.link/ontology#>` and
  `ae: <http://data.archaeology.link/data/ae/>`, while the two derived files
  left behind there (`*_Allen.ttl`, `*_s_HadriansWall*.ttl`, not copied) still
  carry `http://rgzm.github.io/alligator/ontology#` and
  `http://example.net/event#`. The main file has therefore been reworked after
  the fact, or produced by a different route. It is a sound reference for the
  *content* — the dating, the relations, the weights — and not for the IRIs.

## To do before step S3 is closed

Pull all seven outputs for both datasets again from
<https://tools.leiza.de/alligator/>, each set in one session from one input
file, and record here:

- **Date** the files were pulled.
- **Service version** — `GET /` on the API returns the Maven coordinates from
  `POM.getInfo()`; paste them verbatim.
- **Input file** and its SHA-256, so the pair can be checked later.

Until that is recorded, both sets are indicative rather than authoritative. That
said, they now agree with each other where they overlap, which is worth more
than either alone: two datasets, two provenances, the same behaviour.
