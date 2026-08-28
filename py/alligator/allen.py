"""Allen interval algebra.

Port of de.rgzm.alligator.allen.AllenInttervalAlgebra. The thirteen relations
and their OWL-Time properties are tabulated in PRIMER.md, part C, step S1.

Freksa's semi-interval relations exist in the Java class but are never called
from the pipeline; they are not ported (PRIMER A8, D-09). The AMT axioms do
reference their roles, which is a different matter — see part D.

Implemented in step S1 of the work plan.
"""
