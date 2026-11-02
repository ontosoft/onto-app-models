"""Public entry point: SHACL shapes (Turtle) -> a complete OntoUI model.

The generated model is self-contained: the per-entity ``sh:NodeShape`` shapes
it emits drive the form generation and the per-form validation, and the
ORIGINAL input shapes are embedded verbatim, so the final runtime validation
checks the output graph against the true input (the round-trip property) - no
separate shapes file is needed at run time. Output is returned in both
serialisations to honour the dual-write invariant (knowledge_graph_rdf +
knowledge_graph_json).
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from rdflib import RDF, Graph
from rdflib.namespace import OWL

from .shacl_reader import read_shapes
from .templates import DEFAULT_BASE, build_model_graph


@dataclass
class GeneratedModel:
    rdf: str  # Turtle, the source of truth
    jsonld: object  # JSON-LD python object, for the JSONB column


def generate_model_graph(
    shapes_ttl: str,
    base: str = DEFAULT_BASE,
    per_form_validation: bool = True,
) -> Graph:
    """Parse the input SHACL and build the model graph.

    With per_form_validation (the default) every submit routes through a
    per-form SHACL validation task before the data is stored; set it to False
    to validate only once, at the end, over the whole output graph.
    """
    shapes = Graph()
    shapes.parse(data=shapes_ttl, format="turtle")
    entities = read_shapes(shapes)
    if not entities:
        raise ValueError(
            "No SHACL NodeShape with sh:targetClass found in the input shapes."
        )
    model = build_model_graph(entities, base, per_form_validation)
    # R9: embed the whole input shapes document, so the final runtime
    # validation checks the output graph against the ORIGINAL input shapes
    # (true round trip), including constraints the form layer cannot enforce
    # yet (sh:in, sh:or, ...).
    # Not embedded: the input's ontology header - the resource (usually one,
    # often none) by which the document describes ITSELF, `<doc> a
    # owl:Ontology ; owl:imports ... ; owl:versionInfo ...`. The generated
    # model is its own document, and a copied owl:imports would make the
    # engine's OWL reasoner fetch external ontologies at load time (the
    # SHACL subtraction there does not help - a header is not a shape).
    for header in set(shapes.subjects(RDF.type, OWL.Ontology)):
        shapes -= shapes.cbd(header)
    model += shapes
    return model


def generate_appmodel_from_shacl(
    shapes_ttl: str,
    base: str = DEFAULT_BASE,
    per_form_validation: bool = True,
) -> GeneratedModel:
    """Turn an input SHACL shapes file into a complete, dual-write-ready model."""
    g = generate_model_graph(shapes_ttl, base, per_form_validation)
    return GeneratedModel(
        rdf=g.serialize(format="turtle"),
        jsonld=json.loads(g.serialize(format="json-ld")),
    )
