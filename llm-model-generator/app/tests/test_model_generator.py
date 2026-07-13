"""model_generator contract: SHACL shapes in -> a valid, runnable model out.

Locks the Phase-1 guarantee: the generated model parses, has zero structural
validation issues, and the engine can drive it from the first form to the
completion screen.
"""

from pathlib import Path

from rdflib import RDF, Graph, Namespace, URIRef

import model_generator
from model_generator import generate_appmodel_from_shacl
from owlprocessor.app_engine import AppEngine
from owlprocessor.validate_model import validate_model

EXAMPLES = Path(model_generator.__file__).parent / "examples"

# Minimal input: one entity, one string field.
SHAPES = """
@prefix sh:  <http://www.w3.org/ns/shacl#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix v1:  <http://purl.org/goodrelations/v1#> .

<http://example.org/generated/string-form/BusinessEntityShape>
    a sh:NodeShape ;
    sh:targetClass v1:BusinessEntity ;
    sh:property [
        sh:path     v1:legalName ;
        sh:datatype xsd:string ;
        sh:name     "Field 1" ;
        sh:order    0 ;
    ] .
"""

BASE = "http://example.org/generated/"


def test_generated_model_parses_and_validates():
    gm = generate_appmodel_from_shacl(SHAPES)
    g = Graph()
    g.parse(data=gm.rdf, format="turtle")  # must be valid Turtle
    assert isinstance(gm.jsonld, list) and gm.jsonld  # dual-write payload present
    assert validate_model(g) == []  # zero structural issues


def _walk_to_completion(eng: AppEngine, max_steps: int = 12) -> bool:
    """Drive the running app: submit forms, Continue notifications, OK the rest."""

    def buttons(mc):
        out = []

        def w(e):
            if isinstance(e, dict):
                if e.get("type") == "button":
                    out.append(e.get("label"))
                for v in e.values():
                    w(v)
            elif isinstance(e, list):
                for v in e:
                    w(v)

        if isinstance(mc, dict):
            w(mc.get("uischema", {}))
        return out

    eng.process_received_client_data(
        {"message_type": "initiate_exchange", "message_content": {}}
    )
    for _ in range(max_steps):
        out = eng.read_new_model_layout()
        if eng.process_engine_instance.app_state.app_finished:
            return True
        mc = out.message_content
        block = str(mc.get("graph_node", "")) if isinstance(mc, dict) else ""
        btns = buttons(mc)
        if block.endswith("_block") and "_notification_" not in block:
            # a data form -> submit it (the block name maps to its submit action)
            name = block.rsplit("/", 1)[-1][: -len("_block")]
            eng.process_received_client_data({
                "message_type": "action",
                "message_content": {
                    "action_type": "submit",
                    "action_graph_node": f"{BASE}submit_action_{name}",
                    "form_graph_node": block,
                    "form_data": {},
                },
            })
        elif btns == ["Continue"]:
            eng.process_received_client_data({
                "message_type": "action",
                "message_content": {
                    "action_type": "other",
                    "action_graph_node": f"{BASE}continue_action",
                },
            })
        else:
            # validation result OK button (empty action node) -> proceed
            eng.process_received_client_data({
                "message_type": "action",
                "message_content": {"action_type": "other", "action_graph_node": ""},
            })
    return eng.process_engine_instance.app_state.app_finished


def test_generated_model_runs_to_completion():
    gm = generate_appmodel_from_shacl(SHAPES)
    eng = AppEngine()
    eng.load_inner_app_model(rdf_string=gm.rdf)
    eng.run_application()
    assert _walk_to_completion(eng) is True


def test_multi_entity_restaurant_generates_and_runs():
    """Phase 2: the 4-shape restaurant fixture -> a valid, runnable multi-form app."""
    shapes = (EXAMPLES / "restaurant.shapes.ttl").read_text(encoding="utf-8")
    gm = generate_appmodel_from_shacl(shapes)

    g = Graph()
    g.parse(data=gm.rdf, format="turtle")
    assert validate_model(g) == []

    eng = AppEngine()
    eng.load_inner_app_model(rdf_string=gm.rdf)
    eng.run_application()
    blocks = {str(f.graph_node).rsplit("/", 1)[-1] for f in eng.internal_app_static_model.forms}
    # one data form per entity
    for expected in ("business_entity_block", "menu_block", "dish_block", "ingredient_block"):
        assert expected in blocks
    assert _walk_to_completion(eng, max_steps=24) is True


def test_relationships_generate_connections_and_link_instances():
    """A sh:property with sh:node -> an obop:Connection, no form field, and the
    engine creates the object-property triples between the two instances."""
    OBOP = Namespace("http://purl.org/net/obop/")
    SH = Namespace("http://www.w3.org/ns/shacl#")
    GR = Namespace("http://purl.org/goodrelations/v1#")
    SCHEMA = Namespace("http://schema.org/")
    R = Namespace("http://example.org/generated/restaurant/")

    shapes = (EXAMPLES / "restaurant.shapes.ttl").read_text(encoding="utf-8")
    gm = generate_appmodel_from_shacl(shapes)
    g = Graph()
    g.parse(data=gm.rdf, format="turtle")

    # relationship properties never become form fields
    field_paths = {
        o for f in g.subjects(RDF.type, OBOP.Field)
        for o in g.objects(f, OBOP.containsDatatype)
    }
    assert not field_paths & {SCHEMA.hasMenu, GR.offers, R.belongsToMenu}

    # one Connection per (source, target) pair; restaurant->menu carries BOTH connectors
    be_menu = URIRef(f"{BASE}business_entity_menu_connection")
    assert (be_menu, OBOP.connectionHasSource, URIRef(f"{BASE}business_entity_shape")) in g
    assert (be_menu, OBOP.connectionHasTarget, URIRef(f"{BASE}menu_shape")) in g
    connector_paths = {
        o for c in g.objects(be_menu, OBOP.hasConnector) for o in g.objects(c, SH.path)
    }
    assert connector_paths == {SCHEMA.hasMenu, GR.offers}

    # dish->menu: the SOURCE subprocess runs later, so its task lives in insert_dish
    task = URIRef(f"{BASE}make_connection_dish_menu")
    assert (task, None, URIRef(f"{BASE}insert_dish")) in g

    # the source shape declares the relationship (validation-only property shape)
    rel_nodes = {
        o for ps in g.objects(URIRef(f"{BASE}business_entity_shape"), SH.property)
        for o in g.objects(ps, SH.node)
    }
    assert URIRef(f"{BASE}menu_shape") in rel_nodes

    # runtime: after a full walk, the instances are linked
    eng = AppEngine()
    eng.load_inner_app_model(rdf_string=gm.rdf)
    eng.run_application()
    assert _walk_to_completion(eng, max_steps=24) is True
    out = eng.process_engine_instance.output_graph_store
    assert len(list(out.subject_objects(SCHEMA.hasMenu))) == 1
    assert len(list(out.subject_objects(GR.offers))) == 1
    assert len(list(out.subject_objects(R.belongsToMenu))) == 1
    ((restaurant, menu),) = out.subject_objects(SCHEMA.hasMenu)
    assert (restaurant, RDF.type, GR.BusinessEntity) in out
    assert (menu, RDF.type, R.Menu) in out
    assert (restaurant, GR.offers, menu) in out
