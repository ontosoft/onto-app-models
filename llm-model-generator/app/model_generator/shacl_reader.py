"""Parse an input SHACL shapes graph into the generator's IR.

Only the structural facts the generator needs are read: each ``sh:NodeShape``
with a ``sh:targetClass``, and its ``sh:property`` shapes (path, datatype, name,
order). A property shape whose ``sh:node`` points at another read NodeShape —
or whose ``sh:class`` matches another shape's ``sh:targetClass`` — is a
*relationship* between two entities (-> :class:`RelationSpec`, generated as an
obop:Connection), not a form field. Anything else in the shapes (constraints
like sh:minCount, sh:pattern, etc.) is preserved as the *runtime* validation
SHACL elsewhere; here we only need enough to lay out the forms.
"""

from __future__ import annotations

import logging
import re

from rdflib import RDF, Graph, Namespace

from .ir import EntitySpec, PropSpec, RelationSpec

SH = Namespace("http://www.w3.org/ns/shacl#")

logger = logging.getLogger("ontoui_app")


def _local(uri: object) -> str:
    """Local name of an IRI (after the last '/' or '#')."""
    return re.split(r"[/#]", str(uri))[-1]


def _snake(name: str) -> str:
    """camelCase / PascalCase / kebab / spaces -> snake_case token.

    Word boundaries are lower/digit->upper and the last capital of an acronym
    run, so all-caps names stay whole: ``BusinessEntity`` -> ``business_entity``,
    ``ENVO_01000934`` -> ``envo_01000934`` (not ``e_n_v_o_...``).
    """
    s = re.sub(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])", "_", name)
    s = re.sub(r"[-\s]+", "_", s)
    return re.sub(r"[^0-9a-zA-Z_]", "", s).lower()


def _entity_iri_token_by_shape(graph: Graph) -> dict:
    """Map each NodeShape (with a target class) to its entity's unique iri_token.

    Built as a first pass so a property shape's ``sh:node`` object can be
    resolved to the entity it points at, regardless of the order shapes appear
    in the input. Tokens are de-duplicated deterministically (``menu``,
    ``menu_2``, ...): with arbitrary input, two shapes may target classes that
    share a local name (e.g. schema:Menu and myont:Menu), and colliding tokens
    would mint colliding IRIs — a silently broken model.
    """
    # Sort shapes for a deterministic iteration order (=> deterministic suffixes).
    shapes = sorted(
        (
            shape
            for shape in graph.subjects(RDF.type, SH.NodeShape)
            if any(True for _ in graph.objects(shape, SH.targetClass))
        ),
        key=str,
    )
    iri_tokens: dict = {}
    used: set[str] = set()
    for shape in shapes:
        target_classes = sorted(str(t) for t in graph.objects(shape, SH.targetClass))
        base = _snake(_local(target_classes[0])) or "entity"
        iri_token = base
        n = 2
        while iri_token in used:
            iri_token = f"{base}_{n}"
            n += 1
        if iri_token != base:
            logger.warning(
                f"Entity iri_token collision on '{base}' (shape {shape}); "
                f"using '{iri_token}'."
            )
        used.add(iri_token)
        iri_tokens[shape] = iri_token
    return iri_tokens


def _entity_iri_token_by_class(graph: Graph, iri_token_by_shape: dict) -> dict:
    """Map each ``sh:targetClass`` IRI to its entity's iri_token.

    Lets a property shape reference its target entity by class instead of by
    shape (``[ sh:path ... ; sh:class schema:Menu ]``). If several shapes
    target the same class, the first in deterministic shape order wins (with a
    warning) — ``iri_token_by_shape`` already iterates in that order.
    """
    iri_tokens: dict = {}
    for shape, iri_token in iri_token_by_shape.items():
        for cls in sorted(graph.objects(shape, SH.targetClass), key=str):
            if cls in iri_tokens:
                if iri_tokens[cls] != iri_token:
                    logger.warning(
                        f"Several NodeShapes target class {cls}; sh:class "
                        f"relationships resolve to entity '{iri_tokens[cls]}'."
                    )
                continue
            iri_tokens[cls] = iri_token
    return iri_tokens


def read_shapes(graph: Graph) -> list[EntitySpec]:
    """Return one EntitySpec per SHACL NodeShape (sorted for determinism).

    Entities are sorted by iri_token so the same input always yields the same
    model (stable output for tests). Explicit cross-entity ordering is a later
    concern.
    """
    iri_token_by_shape = _entity_iri_token_by_shape(graph)
    iri_token_by_class = _entity_iri_token_by_class(graph, iri_token_by_shape)

    entities: list[EntitySpec] = []
    for shape, iri_token in iri_token_by_shape.items():
        # A shape may declare several target classes; pick deterministically.
        target_classes = sorted(str(t) for t in graph.objects(shape, SH.targetClass))
        target_class = target_classes[0]
        shape_order = graph.value(shape, SH.order)

        props: list[PropSpec] = []
        rels: list[RelationSpec] = []
        for prop in graph.objects(shape, SH.property):
            path = graph.value(prop, SH.path)
            if path is None:
                continue
            order = graph.value(prop, SH.order)
            node = graph.value(prop, SH.node)
            cls = graph.value(prop, SH["class"])
            if node is not None or cls is not None:
                # A relationship to another entity, never a form field.
                # sh:node names the target shape directly; sh:class resolves
                # through the shapes' target classes (sh:node wins if both).
                target_iri_token = iri_token_by_shape.get(node)
                if target_iri_token is None and cls is not None:
                    target_iri_token = iri_token_by_class.get(cls)
                if target_iri_token is not None:
                    max_count = graph.value(prop, SH.maxCount)
                    rels.append(
                        RelationSpec(
                            path=str(path),
                            iri_token=_snake(_local(path)),
                            target_iri_token=target_iri_token,
                            order=int(order) if order is not None else len(rels),
                            # unbounded (or >1) cardinality -> the target entity
                            # may be instantiated several times
                            multiple=max_count is None or int(max_count) > 1,
                        )
                    )
                else:
                    logger.warning(
                        f"Property shape on {shape} references "
                        f"{node if node is not None else cls} (sh:node/sh:class), "
                        "which no NodeShape with a sh:targetClass in this input "
                        "matches; skipping the relationship."
                    )
                continue
            datatype = graph.value(prop, SH.datatype)
            name = graph.value(prop, SH.name)
            props.append(
                PropSpec(
                    path=str(path),
                    datatype=str(datatype) if datatype is not None else None,
                    label=str(name) if name is not None else _local(path),
                    iri_token=_snake(_local(path)),
                    order=int(order) if order is not None else len(props),
                )
            )
        props.sort(key=lambda p: (p.order, p.iri_token))
        rels.sort(key=lambda r: (r.order, r.iri_token, r.target_iri_token))

        entities.append(
            EntitySpec(
                class_uri=str(target_class),
                iri_token=iri_token,
                label=_local(target_class),
                order=int(shape_order) if shape_order is not None else 0,
                properties=props,
                relationships=rels,
            )
        )

    # An entity targeted by an unbounded relationship is loopable: its
    # subprocess gets an "Add another <label>" loop so N instances can be made.
    entity_by_token = {e.iri_token: e for e in entities}
    for entity in entities:
        for rel in entity.relationships:
            if rel.multiple:
                entity_by_token[rel.target_iri_token].looped = True

    # Order subprocesses by the shape's sh:order (then iri_token for stability).
    entities.sort(key=lambda e: (e.order, e.iri_token))
    return entities
