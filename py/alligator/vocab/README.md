# vocab/

Static ontology assets, loaded and merged at run time. These are data, not
code, and are not edited by the pipeline.

| File | Origin |
|---|---|
| `alligator.ttl` | `leiza-rse/alligator`, `ontology/alligator.ttl` — the Alligator vocabulary, Triceratops Edition, CC BY 4.0 |
| `amt_allen_axioms.ttl` | extracted in step S3 from the Turtle hard-coded twice in `AMTEvents.java`: 921 triples, 1 `amt:Concept`, 31 `amt:Role`, 28 `amt:InverseAxiom`, 126 `amt:RoleChainAxiom`, 31 `amt:SelfDisjointAxiom`, 6 `amt:DisjointAxiom`. Both copies in the Java file are identical and both agree, triple for triple, with the block in the published reference outputs |

The general AMT vocabulary is deliberately absent: AMT.engine loads its own
`ontology/amt.ttl`, so repeating it here would only invite the two copies to
drift apart. Those thirteen triples — `amt:Concept rdfs:subClassOf rdfs:Class`
and the twelve beside it — are the whole difference between
`amt_allen_axioms.ttl` and the Java block.

`amt_allen_axioms.ttl` keeps the layout of the published file: section
comments, one triple per line, single-quoted labels. It is read and appended
verbatim, never reformatted, so that a diff against an existing AMT file stays
readable. The counts above are asserted in `tests/test_rdf.py`, which is what
notices if an edit here loses a role.
