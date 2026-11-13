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

from .meta_shapes import validate_fam_model
from .owl_axioms import shacl_to_owl_axioms
from .shacl_reader import read_shapes
from .templates import DEFAULT_BASE, build_model_graph


@dataclass
class GeneratedModel:
    rdf: str  # Turtle, the source of truth
    jsonld: object  # JSON-LD python object, for the JSONB column


def assemble_model(
    shapes: Graph,
    entities: list,
    base: str = DEFAULT_BASE,
    per_form_validation: bool = True,
    owl_axioms: bool = True,
) -> Graph:
    """Build the full model graph from already-parsed shapes and entities.

    The one assembly path shared by the deterministic generator and the edit
    session (editing.EditSession.render), so every model - generated or
    agent-edited - gets the same OWL axioms, the same embedded shapes and the
    same meta-shape post-condition. ``shapes`` is not mutated.
    """
    model = build_model_graph(entities, base, per_form_validation)
    if owl_axioms:
        # R10: constraint knowledge for the OWL layer (reasoning), parallel
        # to the embedded shapes for the SHACL layer (validation).
        model += shacl_to_owl_axioms(shapes)
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
    embedded = Graph()
    embedded += shapes
    for header in set(embedded.subjects(RDF.type, OWL.Ontology)):
        embedded -= embedded.cbd(header)
    model += embedded
    # Post-condition: the generator's own output must satisfy the FAM
    # meta-shapes. A violation here is a generator bug, never a
    # property of the input — so fail loudly instead of handing a broken
    # model to the engine.
    conforms, report = validate_fam_model(model)
    if not conforms:
        raise ValueError(
            f"generated model violates the FAM meta-shapes (generator bug):\n{report}"
        )
    return model


def generate_model_graph(
    shapes_ttl: str,
    base: str = DEFAULT_BASE,
    per_form_validation: bool = True,
    owl_axioms: bool = True,
) -> Graph:
    """Parse the input SHACL and build the model graph.

    With per_form_validation (the default) every submit routes through a
    per-form SHACL validation task before the data is stored; set it to False
    to validate only once, at the end, over the whole output graph.

    With owl_axioms (the default) the input constraints are additionally
    translated into OWL TBox axioms (R10, see owl_axioms.py), so the engine's
    reasoners see the constraint knowledge that the embedded SHACL - which is
    subtracted from the reasoner input - cannot carry.
    """
    shapes = Graph()
    shapes.parse(data=shapes_ttl, format="turtle")
    entities = read_shapes(shapes)
    if not entities:
        raise ValueError(
            "No SHACL NodeShape with sh:targetClass found in the input shapes."
        )
    return assemble_model(shapes, entities, base, per_form_validation, owl_axioms)


def serialize_model(graph: Graph) -> GeneratedModel:
    """Serialize a model graph into the dual-write pair (Turtle + JSON-LD)."""
    return GeneratedModel(
        rdf=graph.serialize(format="turtle"),
        jsonld=json.loads(graph.serialize(format="json-ld")),
    )


def generate_appmodel_from_shacl(
    shapes_ttl: str,
    base: str = DEFAULT_BASE,
    per_form_validation: bool = True,
    owl_axioms: bool = True,
) -> GeneratedModel:
    """Turn an input SHACL shapes file into a complete, dual-write-ready model."""
    return serialize_model(
        generate_model_graph(shapes_ttl, base, per_form_validation, owl_axioms)
    )
