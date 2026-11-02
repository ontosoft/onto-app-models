"""model_generator contract: SHACL shapes in -> a valid, runnable model out.

Locks the Phase-1 guarantee: the generated model parses, has zero structural
validation issues, and the engine can drive it from the first form to the
completion screen.
"""

from pathlib import Path

from rdflib import RDF, Graph, Literal, Namespace, URIRef

import model_generator
from model_generator import generate_appmodel_from_shacl
from app_engine.app_engine import AppEngine
from app_engine.validate_model import validate_model

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


# Like SHAPES, but the property carries real value constraints (R9 input).
CONSTRAINED_SHAPES = """
@prefix sh:  <http://www.w3.org/ns/shacl#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix v1:  <http://purl.org/goodrelations/v1#> .

<http://example.org/generated/string-form/BusinessEntityShape>
    a sh:NodeShape ;
    sh:targetClass v1:BusinessEntity ;
    sh:property [
        sh:path      v1:legalName ;
        sh:datatype  xsd:string ;
        sh:name      "Legal name" ;
        sh:order     0 ;
        sh:minCount  1 ;
        sh:maxLength 50 ;
        sh:pattern   "^[A-Z].*" ;
    ] .
"""

OBOP = Namespace("http://purl.org/net/obop/")
SH = Namespace("http://www.w3.org/ns/shacl#")
DASH = Namespace("http://datashapes.org/dash#")


def test_input_property_constraints_are_copied():
    """R9: the embedded property shape carries exactly the input's constraints.

    Copied verbatim: sh:minCount/maxLength/pattern. Not invented: the input has
    no sh:maxCount and no dash:singleLine, so the generated shape must not
    claim them either.
    """
    gm = generate_appmodel_from_shacl(CONSTRAINED_SHAPES)
    g = Graph()
    g.parse(data=gm.rdf, format="turtle")

    field = URIRef(f"{BASE}field_business_entity_legal_name")
    prop_shapes = list(g.subjects(OBOP.specifiedBy, field))
    assert len(prop_shapes) == 1  # exactly one shape specifies this field
    ps = prop_shapes[0]

    assert (ps, SH.minCount, Literal(1)) in g
    assert (ps, SH.maxLength, Literal(50)) in g
    assert (ps, SH.pattern, Literal("^[A-Z].*")) in g
    assert g.value(ps, SH.maxCount) is None
    assert g.value(ps, DASH.singleLine) is None


def test_copied_constraints_actually_validate():
    """The embedded shapes are effective, not just triples: pySHACL run
    against the generated model rejects a violating instance and accepts a
    conforming one. (The engine wiring them into the final validation task
    is the next step; this pins the generator half.)
    """
    from pyshacl import validate as shacl_validate

    gm = generate_appmodel_from_shacl(CONSTRAINED_SHAPES)
    shapes_graph = Graph()
    shapes_graph.parse(data=gm.rdf, format="turtle")

    v1 = Namespace("http://purl.org/goodrelations/v1#")

    def output_graph(legal_name: str) -> Graph:
        data = Graph()
        inst = URIRef("http://example.org/data/be1")
        data.add((inst, RDF.type, v1.BusinessEntity))
        data.add((inst, v1.legalName, Literal(legal_name)))
        return data

    # violates sh:pattern "^[A-Z].*" (lowercase start)
    conforms, _, _ = shacl_validate(output_graph("acme"), shacl_graph=shapes_graph)
    assert not conforms
    # conforming value passes
    conforms, _, _ = shacl_validate(output_graph("Acme"), shacl_graph=shapes_graph)
    assert conforms


def test_form_schema_carries_shape_constraints():
    """R9: the field's copied constraints surface in the JSONForms schema
    (pattern/maxLength + required), so the frontend validates while the
    user types."""
    gm = generate_appmodel_from_shacl(CONSTRAINED_SHAPES)
    eng = AppEngine()
    eng.load_inner_app_model(rdf_string=gm.rdf)
    eng.run_application()
    eng.process_received_client_data(
        {"message_type": "initiate_exchange", "message_content": {}}
    )
    out = eng.read_new_model_layout()
    schema = out.message_content["schema"]
    assert schema["properties"]["Legal name"]["pattern"] == "^[A-Z].*"
    assert schema["properties"]["Legal name"]["maxLength"] == 50
    assert schema["required"] == ["Legal name"]


def test_input_shapes_document_is_embedded_whole():
    """R9: the original input shapes are merged into the model verbatim, so
    the final validation checks the round trip against the true input - but
    the input's ontology header (owl:imports!) must not come along."""
    shapes_with_header = CONSTRAINED_SHAPES + """
<http://example.org/generated/string-form>
    a <http://www.w3.org/2002/07/owl#Ontology> ;
    <http://www.w3.org/2002/07/owl#imports> <http://example.org/some/vocab> .
"""
    gm = generate_appmodel_from_shacl(shapes_with_header)
    g = Graph()
    g.parse(data=gm.rdf, format="turtle")

    v1 = Namespace("http://purl.org/goodrelations/v1#")
    owl = Namespace("http://www.w3.org/2002/07/owl#")
    input_shape = URIRef(
        "http://example.org/generated/string-form/BusinessEntityShape"
    )
    assert (input_shape, SH.targetClass, v1.BusinessEntity) in g
    ps = g.value(input_shape, SH.property)
    assert g.value(ps, SH.pattern) == Literal("^[A-Z].*")
    assert g.value(predicate=RDF.type, object=owl.Ontology) is None
    assert list(g.subjects(owl.imports, None)) == []


def test_engine_final_validation_uses_embedded_shapes():
    """R9 step 2: the engine's final SHACLValidation task really validates the
    output graph against the embedded shapes (it used to run with
    shacl_graph=None, which conforms vacuously)."""

    gm = generate_appmodel_from_shacl(CONSTRAINED_SHAPES)
    v1 = Namespace("http://purl.org/goodrelations/v1#")

    def validation_text(legal_name: str) -> str:
        eng = AppEngine()
        eng.load_inner_app_model(rdf_string=gm.rdf)
        eng.run_application()
        pe = eng.process_engine_instance
        inst = URIRef("http://example.org/data/be1")
        pe.output_graph_store.add((inst, RDF.type, v1.BusinessEntity))
        pe.output_graph_store.add((inst, v1.legalName, Literal(legal_name)))
        pe.validate_output_knowledge_graph()
        return pe.app_state.json_form["uischema"]["elements"][0]["text"]

    # violates sh:pattern "^[A-Z].*" (lowercase start)
    assert "Conforms: False" in validation_text("acme")
    assert "Conforms: True" in validation_text("Acme")


def test_round_trip_catches_constraints_the_form_layer_cannot_enforce():
    """R9 step 3: the round trip fails on a real violation, end to end.

    sh:in is list-valued, so the generator drops it from the copied field
    shape - the form schema and the per-form validation cannot enforce it.
    But the ORIGINAL input shapes are embedded whole, and the engine's own
    final-validation task (reached through the normal flow, not called by
    hand) must report the stored value against them."""
    shapes = """
    @prefix sh:  <http://www.w3.org/ns/shacl#> .
    @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
    @prefix v1:  <http://purl.org/goodrelations/v1#> .

    <http://example.org/generated/string-form/BusinessEntityShape>
        a sh:NodeShape ;
        sh:targetClass v1:BusinessEntity ;
        sh:property [
            sh:path     v1:legalName ;
            sh:datatype xsd:string ;
            sh:name     "Legal name" ;
            sh:order    0 ;
            sh:in       ("Acme" "Globex") ;
        ] .
    """

    def final_validation_text(legal_name: str) -> str:
        gm = generate_appmodel_from_shacl(shapes)
        eng = AppEngine()
        eng.load_inner_app_model(rdf_string=gm.rdf)
        eng.run_application()
        eng.process_received_client_data(
            {"message_type": "initiate_exchange", "message_content": {}}
        )
        mc = eng.read_new_model_layout().message_content
        # the dropped sh:in never reaches the form schema ...
        assert "enum" not in mc["schema"]["properties"]["Legal name"]
        eng.process_received_client_data({
            "message_type": "action",
            "message_content": {
                "action_type": "submit",
                "action_graph_node": f"{BASE}submit_action_business_entity",
                "form_graph_node": str(mc["graph_node"]),
                "form_data": {"Legal name": legal_name},
            },
        })
        # ... and the per-form validation (field shapes only) lets any string
        # through: the next screen is the saved notification, not the form
        out = eng.read_new_model_layout()
        assert "_notification_" in str(out.message_content.get("graph_node", "")), (
            "per-form validation unexpectedly rejected the value"
        )
        eng.process_received_client_data({
            "message_type": "action",
            "message_content": {
                "action_type": "other",
                "action_graph_node": f"{BASE}continue_action",
            },
        })
        # Continue ends the subprocess; the final-validation ScriptTask runs
        # and its message box reports the result against the embedded input
        out = eng.read_new_model_layout()
        assert out.layout_type == "message-box"
        return out.message_content["uischema"]["elements"][0]["text"]

    report = final_validation_text("Trattoria")  # not in sh:in ("Acme" "Globex")
    assert "Conforms: False" in report
    assert "InConstraintComponent" in report
    assert "Conforms: True" in final_validation_text("Acme")


def test_per_form_validation_rejects_then_accepts():
    """R9 2b: the submit routes through a per-form SHACL validation BEFORE the
    data is stored. A violating submit sends the same form back with the
    entered values and the report (nothing stored); a conforming resubmit is
    stored and the app completes."""
    gm = generate_appmodel_from_shacl(CONSTRAINED_SHAPES)
    g = Graph()
    g.parse(data=gm.rdf, format="turtle")
    # the validation machinery is generated by default
    assert (URIRef(f"{BASE}validate_form_business_entity"), None, None) in g
    assert (URIRef(f"{BASE}validation_gateway_business_entity"), None, None) in g
    assert validate_model(g) == []

    eng = AppEngine()
    eng.load_inner_app_model(rdf_string=gm.rdf)
    eng.run_application()
    eng.process_received_client_data(
        {"message_type": "initiate_exchange", "message_content": {}}
    )
    mc = eng.read_new_model_layout().message_content
    block = str(mc["graph_node"])

    def submit(data):
        eng.process_received_client_data({
            "message_type": "action",
            "message_content": {
                "action_type": "submit",
                "action_graph_node": f"{BASE}submit_action_business_entity",
                "form_graph_node": block,
                "form_data": data,
            },
        })

    # violates sh:pattern "^[A-Z].*" (lowercase start)
    submit({"Legal name": "acme"})
    out = eng.read_new_model_layout()
    assert out.layout_type == "form"  # the same form again, not the notification
    mc = out.message_content
    assert mc["data"] == {"Legal name": "acme"}  # entered values are kept
    labels = [
        e for e in mc["uischema"]["elements"] if e.get("type") == "Label"
    ]
    assert any("Conforms: False" in e.get("text", "") for e in labels)
    v1 = Namespace("http://purl.org/goodrelations/v1#")
    out_graph = eng.process_engine_instance.output_graph_store
    assert list(out_graph.subjects(RDF.type, v1.BusinessEntity)) == []

    # a conforming resubmit is stored and the app runs to completion
    submit({"Legal name": "Acme"})
    assert _walk_to_completion(eng) is True
    assert len(list(out_graph.subjects(RDF.type, v1.BusinessEntity))) == 1
    assert (None, v1.legalName, Literal("Acme")) in out_graph


def test_per_form_validation_can_be_omitted():
    """per_form_validation=False: no validation task is generated, a violating
    submit is stored unchecked, and only the FINAL whole-graph validation
    reports the violation."""
    gm = generate_appmodel_from_shacl(CONSTRAINED_SHAPES, per_form_validation=False)
    g = Graph()
    g.parse(data=gm.rdf, format="turtle")
    assert (URIRef(f"{BASE}validate_form_business_entity"), None, None) not in g
    assert validate_model(g) == []

    eng = AppEngine()
    eng.load_inner_app_model(rdf_string=gm.rdf)
    eng.run_application()
    eng.process_received_client_data(
        {"message_type": "initiate_exchange", "message_content": {}}
    )
    mc = eng.read_new_model_layout().message_content
    eng.process_received_client_data({
        "message_type": "action",
        "message_content": {
            "action_type": "submit",
            "action_graph_node": f"{BASE}submit_action_business_entity",
            "form_graph_node": str(mc["graph_node"]),
            "form_data": {"Legal name": "acme"},
        },
    })
    # the violating value went straight into the store ...
    v1 = Namespace("http://purl.org/goodrelations/v1#")
    out_graph = eng.process_engine_instance.output_graph_store
    assert (None, v1.legalName, Literal("acme")) in out_graph
    # ... and only the final validation reports it
    pe = eng.process_engine_instance
    pe.validate_output_knowledge_graph()
    report = pe.app_state.json_form["uischema"]["elements"][0]["text"]
    assert "Conforms: False" in report


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
        elif "Continue" in btns:
            # looped entities also show "Add another <label>"; default walk
            # always continues (no extra iterations)
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
    assert not field_paths & {
        SCHEMA.hasMenu, GR.offers, R.belongsToMenu, R.hasIngredient
    }

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

    # sh:class resolves through the target class: dish->ingredient
    di = URIRef(f"{BASE}dish_ingredient_connection")
    assert (di, OBOP.connectionHasSource, URIRef(f"{BASE}dish_shape")) in g
    assert (di, OBOP.connectionHasTarget, URIRef(f"{BASE}ingredient_shape")) in g

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
    assert len(list(out.subject_objects(R.hasIngredient))) == 1
    ((restaurant, menu),) = out.subject_objects(SCHEMA.hasMenu)
    assert (restaurant, RDF.type, GR.BusinessEntity) in out
    assert (menu, RDF.type, R.Menu) in out
    assert (restaurant, GR.offers, menu) in out


def test_looped_entity_creates_multiple_instances_and_links():
    """Multiplicity: menu is the target of the unbounded hasMenu/offers, so its
    subprocess loops ("Add another Menu"); each iteration creates a NEW menu
    instance and connects it to the restaurant."""
    SCHEMA = Namespace("http://schema.org/")
    GR = Namespace("http://purl.org/goodrelations/v1#")
    R = Namespace("http://example.org/generated/restaurant/")

    shapes = (EXAMPLES / "restaurant.shapes.ttl").read_text(encoding="utf-8")
    gm = generate_appmodel_from_shacl(shapes)

    g = Graph()
    g.parse(data=gm.rdf, format="turtle")
    # the loop machinery is generated for the looped entity
    assert (URIRef(f"{BASE}loop_gateway_menu"), None, None) in g
    assert (URIRef(f"{BASE}add_another_action_menu"), None, None) in g
    assert validate_model(g) == []

    eng = AppEngine()
    eng.load_inner_app_model(rdf_string=gm.rdf)
    eng.run_application()
    eng.process_received_client_data(
        {"message_type": "initiate_exchange", "message_content": {}}
    )

    def act(action_type, node, form_node="", data=None):
        eng.process_received_client_data({
            "message_type": "action",
            "message_content": {
                "action_type": action_type,
                "action_graph_node": node,
                "form_graph_node": form_node,
                "form_data": data or {},
            },
        })

    def submit(block_token, data):
        mc = eng.read_new_model_layout().message_content
        block = str(mc.get("graph_node", ""))
        assert block.endswith(f"{block_token}_block"), block
        act("submit", f"{BASE}submit_action_{block_token}", block, data)

    def press(action_node):
        eng.read_new_model_layout()  # consume the notification screen
        act("other", action_node)

    submit("business_entity", {"Restaurant name": "Trattoria"})
    press(f"{BASE}continue_action")
    submit("menu", {"Menu name": "Lunch"})
    press(f"{BASE}add_another_action_menu")  # loop back for a second menu
    submit("menu", {"Menu name": "Dinner"})
    press(f"{BASE}continue_action")
    assert _walk_to_completion(eng, max_steps=24) is True

    out = eng.process_engine_instance.output_graph_store
    menus = set(out.subjects(RDF.type, R.Menu))
    assert len(menus) == 2  # two distinct Menu instances, nothing overwritten
    names = {str(o) for m in menus for o in out.objects(m, R.menuName)}
    assert names == {"Lunch", "Dinner"}

    # the restaurant is linked to BOTH menus, via both connectors
    restaurant = next(out.subjects(RDF.type, GR.BusinessEntity))
    assert set(out.objects(restaurant, SCHEMA.hasMenu)) == menus
    assert set(out.objects(restaurant, GR.offers)) == menus

    # dish -> menu uses latest-instance semantics: linked to the newest menu
    dish = next(out.subjects(RDF.type, R.Dish))
    (linked_menu,) = list(out.objects(dish, R.belongsToMenu))
    assert str(next(out.objects(linked_menu, R.menuName))) == "Dinner"


def test_instance_picker_links_chosen_instance():
    """The generated dish form offers a picker over ALL menu instances found in
    the output graph; choosing one overrides the latest-instance default."""
    R = Namespace("http://example.org/generated/restaurant/")

    shapes = (EXAMPLES / "restaurant.shapes.ttl").read_text(encoding="utf-8")
    gm = generate_appmodel_from_shacl(shapes)
    g = Graph()
    g.parse(data=gm.rdf, format="turtle")
    # the generator emitted a picker ListField tied to the dish->menu connection
    picker = URIRef(f"{BASE}picker_dish_dish_menu")
    assert (picker, None, URIRef(f"{BASE}dish_menu_connection")) in g

    eng = AppEngine()
    eng.load_inner_app_model(rdf_string=gm.rdf)
    eng.run_application()
    eng.process_received_client_data(
        {"message_type": "initiate_exchange", "message_content": {}}
    )

    def act(action_type, node, form_node="", data=None):
        eng.process_received_client_data({
            "message_type": "action",
            "message_content": {
                "action_type": action_type,
                "action_graph_node": node,
                "form_graph_node": form_node,
                "form_data": data or {},
            },
        })

    def submit(block_token, data):
        mc = eng.read_new_model_layout().message_content
        block = str(mc.get("graph_node", ""))
        assert block.endswith(f"{block_token}_block"), block
        act("submit", f"{BASE}submit_action_{block_token}", block, data)
        return mc

    def press(action_node):
        eng.read_new_model_layout()
        act("other", action_node)

    submit("business_entity", {"Restaurant name": "Trattoria"})
    press(f"{BASE}continue_action")
    submit("menu", {"Menu name": "Lunch"})
    press(f"{BASE}add_another_action_menu")
    submit("menu", {"Menu name": "Dinner"})
    press(f"{BASE}continue_action")

    # the dish form carries the picker, listing BOTH menus from the graph;
    # the user picks "Lunch" — NOT the latest ("Dinner")
    mc = eng.read_new_model_layout().message_content
    props = mc["schema"]["properties"]
    assert "Menu" in props
    assert set(props["Menu"]["enum"]) == {"Lunch", "Dinner"}
    act(
        "submit", f"{BASE}submit_action_dish", mc["graph_node"],
        {"Dish name": "Pasta", "Menu": "Lunch"},
    )
    assert _walk_to_completion(eng, max_steps=24) is True

    out = eng.process_engine_instance.output_graph_store
    dish = next(out.subjects(RDF.type, R.Dish))
    (linked_menu,) = list(out.objects(dish, R.belongsToMenu))
    assert str(next(out.objects(linked_menu, R.menuName))) == "Lunch"
