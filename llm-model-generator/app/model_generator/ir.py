"""Intermediate representation: the parsed SHACL shapes the generator builds from.

A SHACL ``NodeShape`` becomes an :class:`EntitySpec` (one data-entry subprocess);
each of its ``sh:property`` shapes becomes a :class:`PropSpec` (one form field).
Keeping this decoupled from rdflib lets the templates build triples from plain
Python and makes the transform easy to unit-test.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PropSpec:
    """One data property of an entity -> one form field + one SHACL property shape."""

    path: str  # full IRI of the data property (sh:path)
    datatype: str | None  # full IRI of the xsd datatype (sh:datatype), or None
    label: str  # human-facing field label (sh:name, else the path local name)
    token: str  # snake_case token used to mint IRIs (field_<entity>_<token>)
    order: int  # display order (sh:order)


@dataclass
class EntitySpec:
    """One SHACL NodeShape -> one data-entry subprocess + its OBOP block/shape."""

    class_uri: str  # sh:targetClass — the class instances are created of
    token: str  # snake_case token used to mint IRIs (insert_<token>, <token>_block)
    label: str  # human-facing entity label
    order: int = 0  # subprocess sequence (sh:order on the NodeShape)
    properties: list[PropSpec] = field(default_factory=list)
