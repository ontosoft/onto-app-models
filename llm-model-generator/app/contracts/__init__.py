"""Shared, dependency-light contracts crossing the API <-> engine boundary.

Kept deliberately free of engine/reasoner imports so both the API tier and the
(Stage 2) engine worker can depend on it without pulling in owlprocessor.
"""
