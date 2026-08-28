# vocab/

Static ontology assets, loaded and merged at run time. These are data, not
code, and are not edited by the pipeline.

| File | Origin |
|---|---|
| `alligator.ttl` | `leiza-rse/alligator`, `ontology/alligator.ttl` — the Alligator vocabulary, Triceratops Edition, CC BY 4.0 |
| `amt_allen_axioms.ttl` | **to be extracted** in step S3 from the hard-coded Turtle in `AMTEvents.java`: 33 `amt:Role`, 29 `amt:InverseAxiom`, 127 `amt:RoleChainAxiom`, 32 `amt:SelfDisjointAxiom`, 7 `amt:DisjointAxiom` |

The general AMT vocabulary is deliberately absent: AMT.engine loads its own
`ontology/amt.ttl`, so repeating it here would only invite the two copies to
drift apart.
