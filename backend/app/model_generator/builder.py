"""Public entry point: SHACL shapes (Turtle) -> a complete OntoUI model.

The generated model is self-contained: the per-entity ``sh:NodeShape`` shapes it
emits drive both the form generation AND the final runtime SHACL validation, so
no separate shapes file is needed at run time. Output is returned in both
serialisations to honour the dual-write invariant (knowledge_graph_rdf +
knowledge_graph_json).
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from rdflib import Graph

from .shacl_reader import read_shapes
from .templates import DEFAULT_BASE, build_model_graph


@dataclass
class GeneratedModel:
    rdf: str  # Turtle, the source of truth
    jsonld: object  # JSON-LD python object, for the JSONB column


def generate_model_graph(shapes_ttl: str, base: str = DEFAULT_BASE) -> Graph:
    """Parse the input SHACL and build the model graph."""
    shapes = Graph()
    shapes.parse(data=shapes_ttl, format="turtle")
    entities = read_shapes(shapes)
    if not entities:
        raise ValueError(
            "No SHACL NodeShape with sh:targetClass found in the input shapes."
        )
    return build_model_graph(entities, base)


def generate_appmodel_from_shacl(
    shapes_ttl: str, base: str = DEFAULT_BASE
) -> GeneratedModel:
    """Turn an input SHACL shapes file into a complete, dual-write-ready model."""
    g = generate_model_graph(shapes_ttl, base)
    return GeneratedModel(
        rdf=g.serialize(format="turtle"),
        jsonld=json.loads(g.serialize(format="json-ld")),
    )
