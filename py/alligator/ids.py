"""Deterministic event identifiers.

The Java implementation derives a Hashid from a fresh random UUID per event, so
no two runs produce the same file. This module replaces that with an identifier
derived from the event's own AGT row (PRIMER A8, D-01).

Implemented in step S1 of the work plan.
"""
