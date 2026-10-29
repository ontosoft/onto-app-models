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


@dataclass(frozen=True)
class ConstraintSpec:
    """One SHACL/DASH constraint copied verbatim from the input property shape.

    Kept as plain strings (predicate IRI + lexical value) so the IR stays
    rdflib-free; ``datatype``/``is_iri`` preserve enough typing to re-emit the
    exact triple (``sh:minCount 1`` stays an ``xsd:integer``).
    """

    pred: str  # full IRI of the constraint predicate (e.g. sh:minCount)
    value: str  # lexical form of a literal, or the IRI when is_iri
    is_iri: bool = False  # True: value is an IRI (e.g. sh:nodeKind sh:Literal)
    datatype: str | None = None  # literal datatype IRI (None = plain string)


@dataclass
class PropSpec:
    """One data property of an entity -> one form field + one SHACL property shape."""

    path: str  # full IRI of the data property (sh:path)
    datatype: str | None  # full IRI of the xsd datatype (sh:datatype), or None
    label: str  # human-facing field label (sh:name, else the path local name)
    iri_token: str  # snake_case fragment minting IRIs (field_<entity>_<iri_token>)
    order: int  # display order (sh:order)
    # Input constraints copied onto the generated property shape (R9): the
    # embedded shapes must demand exactly what the input shapes demand.
    constraints: list[ConstraintSpec] = field(default_factory=list)


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
    multiple: bool = False  # sh:maxCount absent or >1 -> many target instances


@dataclass
class EntitySpec:
    """One SHACL NodeShape -> one data-entry subprocess + its OBOP block/shape."""

    class_uri: str  # sh:targetClass — the class instances are created of
    iri_token: str  # snake_case fragment minting IRIs (insert_<t>, <t>_block)
    label: str  # human-facing entity label
    order: int = 0  # subprocess sequence (sh:order on the NodeShape)
    properties: list[PropSpec] = field(default_factory=list)
    relationships: list[RelationSpec] = field(default_factory=list)
    # True when some relationship with multiple=True targets this entity: its
    # subprocess then loops ("Add another <label>") so N instances can be made.
    looped: bool = False
