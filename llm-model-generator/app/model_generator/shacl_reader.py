"""Parse an input SHACL shapes graph into the generator's IR.

Only the structural facts the generator needs are read: each ``sh:NodeShape``
with a ``sh:targetClass``, and its ``sh:property`` shapes (path, datatype, name,
order). Anything else in the shapes (constraints like sh:minCount, sh:pattern,
etc.) is preserved as the *runtime* validation SHACL elsewhere; here we only need
enough to lay out the forms.
"""

from __future__ import annotations

import re

from rdflib import RDF, Graph, Namespace

from .ir import EntitySpec, PropSpec

SH = Namespace("http://www.w3.org/ns/shacl#")


def _local(uri: object) -> str:
    """Local name of an IRI (after the last '/' or '#')."""
    return re.split(r"[/#]", str(uri))[-1]


def _snake(name: str) -> str:
    """camelCase / PascalCase / kebab / spaces -> snake_case token."""
    s = re.sub(r"(?<!^)(?=[A-Z])", "_", name)
    s = re.sub(r"[-\s]+", "_", s)
    return re.sub(r"[^0-9a-zA-Z_]", "", s).lower()


def read_shapes(graph: Graph) -> list[EntitySpec]:
    """Return one EntitySpec per SHACL NodeShape (sorted for determinism).

    Entities are sorted by token so the same input always yields the same model
    (stable output for tests). Explicit cross-entity ordering is a later concern.
    """
    entities: list[EntitySpec] = []
    for shape in graph.subjects(RDF.type, SH.NodeShape):
        # A shape may declare several target classes; pick deterministically.
        target_classes = sorted(str(t) for t in graph.objects(shape, SH.targetClass))
        if not target_classes:
            continue
        target_class = target_classes[0]
        shape_order = graph.value(shape, SH.order)

        props: list[PropSpec] = []
        for prop in graph.objects(shape, SH.property):
            path = graph.value(prop, SH.path)
            if path is None:
                continue
            datatype = graph.value(prop, SH.datatype)
            name = graph.value(prop, SH.name)
            order = graph.value(prop, SH.order)
            props.append(
                PropSpec(
                    path=str(path),
                    datatype=str(datatype) if datatype is not None else None,
                    label=str(name) if name is not None else _local(path),
                    token=_snake(_local(path)),
                    order=int(order) if order is not None else len(props),
                )
            )
        props.sort(key=lambda p: (p.order, p.token))

        entities.append(
            EntitySpec(
                class_uri=str(target_class),
                token=_snake(_local(target_class)),
                label=_local(target_class),
                order=int(shape_order) if shape_order is not None else 0,
                properties=props,
            )
        )

    # Order subprocesses by the shape's sh:order (then token for stability).
    entities.sort(key=lambda e: (e.order, e.token))
    return entities
