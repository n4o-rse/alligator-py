"""Reader and writer for the Alligator file format (*.agt).

The format is specified in PRIMER.md, part A7. Parsing is strictly positional:
the header must have exactly seven tab-separated columns and the column names
are never read.

Implemented in step S1 of the work plan.
"""
