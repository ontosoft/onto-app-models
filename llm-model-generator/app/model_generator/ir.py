"""Intermediate representation: the parsed SHACL shapes the generator builds from.

A SHACL ``NodeShape`` becomes an :class:`EntitySpec` (one data-entry subprocess);
each of its ``sh:property`` shapes becomes a :class:`PropSpec` (one form field),
except property shapes with ``sh:node`` pointing at another read NodeShape, which
become :class:`RelationSpec` (an obop:Connection between the two entities' runtime
instances, not a field). Keeping this decoupled from rdflib lets the templates
build triples from plain Python and makes the transform easy to unit-test.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PropSpec:
    """One data property of an entity -> one form field + one SHACL property shape."""

    path: str  # full IRI of the data property (sh:path)
    datatype: str | None  # full IRI of the xsd datatype (sh:datatype), or None
    label: str  # human-facing field label (sh:name, else the path local name)
    iri_token: str  # snake_case fragment minting IRIs (field_<entity>_<iri_token>)
    order: int  # display order (sh:order)


@dataclass
class RelationSpec:
    """One object property linking two entities: a ``sh:property`` carrying
    ``sh:node`` (the target shape) or ``sh:class`` (a class some shape targets).

    Not a form field: it becomes a validation-only property shape on the source
    NodeShape plus one obop:Connector on the generated obop:Connection, so the
    engine creates the (source_instance, path, target_instance) triple at runtime.
    """

    path: str  # full IRI of the object property (sh:path)
    iri_token: str  # snake_case fragment minting IRIs (connector_<...>_<iri_token>)
    target_iri_token: str  # iri_token of the entity pointed at (sh:node/sh:class)
    order: int  # deterministic ordering among the entity's relationships


@dataclass
class EntitySpec:
    """One SHACL NodeShape -> one data-entry subprocess + its OBOP block/shape."""

    class_uri: str  # sh:targetClass — the class instances are created of
    iri_token: str  # snake_case fragment minting IRIs (insert_<t>, <t>_block)
    label: str  # human-facing entity label
    order: int = 0  # subprocess sequence (sh:order on the NodeShape)
    properties: list[PropSpec] = field(default_factory=list)
    relationships: list[RelationSpec] = field(default_factory=list)
