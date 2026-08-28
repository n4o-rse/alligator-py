# output/

Generated results, one directory per dataset. These files **are** version
controlled: that is the point of the repository, and it only works because
identical inputs give byte-identical outputs (`PRIMER.md`, part A3).

```
output/<dataset>/
├── <dataset>_timeline.json        vis.js timeline items
├── <dataset>_graph.json           vis.js network, nodes and edges
├── <dataset>_matrix_allen.json    the Allen matrix, for the web page
├── <dataset>_matrix_allen.csv     the same cells, for anything else
├── <dataset>_matrix_dist.json     the weighted CA distances
├── <dataset>_matrix_dist.csv
├── <dataset>.cypher               CREATE / MERGE / RETURN, for Neo4j
└── img/                           the same four views as figures
    ├── <dataset>_timeline.svg     archival copy
    ├── <dataset>_timeline.jpg     300 dpi, for slides and papers
    └── ...                        graph, matrix_allen, matrix_dist
```

Written by `python py/main.py alligator --dataset <name>`. The two Turtle
outputs are step S3 of the work plan and are not written yet.
