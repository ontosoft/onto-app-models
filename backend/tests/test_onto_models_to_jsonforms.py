from fastapi.testclient import TestClient
from pythonjsonlogger import jsonlogger
from rdflib import Literal, Graph, URIRef
from rdflib.namespace import XSD
from main import app
from owlprocessor.app_engine import AppEngine
from owlprocessor.communication import AppExchangeGetOutput
import jsonpickle
import logging
from deepdiff import DeepDiff

client = TestClient(app)
logger = logging.getLogger("ontoui_app")

# Configure the logging for the pretty print of the json logs
log_format = "%(asctime)s - %(module)s#%(lineno)d - %(levelname)s - %(message)s"
formatter = jsonlogger.JsonFormatter(
    fmt=log_format, rename_fields={"levelname": "level", "asctime": "date"}
)


def test_read_textual_field_model(caplog):
    """
    Test only one single imput field in a form
    """

    rdf_model = """
        @prefix : <http://example.org/logicinterface/testing/> .
        @prefix dc: <http://purl.org/dc/elements/1.1/> .
        @prefix v1: <http://purl.org/goodrelations/v1#> .
        @prefix obo: <http://purl.obolibrary.org/obo/> .
        @prefix owl: <http://www.w3.org/2002/07/owl#> .
        @prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
        @prefix xml: <http://www.w3.org/XML/1998/namespace> .
        @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
        @prefix dash: <http://datashapes.org/dash#> .
        @prefix obop: <http://purl.org/net/obop/> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
        @prefix chebi: <http://purl.obolibrary.org/obo/chebi/> .
        @prefix shacl: <http://www.w3.org/ns/shacl#> .
        @prefix schema: <http://schema.org/> .
        @base <http://example.org/logicinterface/testing/> .

        <http://example.org/logicinterface/testing> rdf:type owl:Ontology .


        ###  http://example.org/logicinterface/testing/block_1
        :block_1 rdf:type owl:NamedIndividual ,
                          obop:Block ;
                 obop:hasPositionNumber "1"^^xsd:int ;
                 dc:title "block_1 for Form"^^rdfs:Literal .


        ###  http://example.org/logicinterface/testing/field_1

        :field_1 rdf:type owl:NamedIndividual ,
                            obop:Field ;
                   obop:belongsTo :block_1 ;
                   obop:containsDatatype v1:legalName ;
                   obop:hasLabel "Label name" ;
                   obop:hasPositionNumber "1"^^xsd:int ;
                   dc:title "field name" .
    """

    caplog.set_level(logging.DEBUG, logger="ontoui_app")
    logger.debug("1. Load the model ")

    app: AppEngine = AppEngine()
    app.model_graph = Graph()
    app.model_graph.parse(data=rdf_model)
    app.load_inner_app_model()
    assert app.inner_app_static_model is not None
    assert app.inner_app_static_model.forms is not None
    assert len(app.inner_app_static_model.forms) > 0
    logger.debug(
        f"Form: {jsonpickle.encode(app.inner_app_static_model.forms[0], indent=2)}"
    )
    app.run_application()
    response = app.app_interaction_model_instance.generate_layout()
    logger.debug("Output dictionary")
    logger.debug(jsonpickle.encode(response, indent=2))
    wanted_result = AppExchangeGetOutput(
        message_type="form",
        layout_type="form",
        message_content={
            "node": "http://example.org/logicinterface/testing/block_1",
            "schema": {
                "type": "object",
                "properties": {"Label name": {"type": "string", "position": 1}},
            },
            "uischema": {
                "type": "VerticalLayout",
                "elements": [{"type": "Control", "scope": "#/properties/Label name"}],
            },
        },
    )
    logger.debug("The difference is:")
    logger.debug(DeepDiff(response, wanted_result))
    assert response == wanted_result


def test_form_with_two_fields_and_a_button(caplog):
    """
    Test only two field and button in a form
    """

    rdf_model = """
        @prefix : <http://example.org/logicinterface/testing/> .
        @prefix dc: <http://purl.org/dc/elements/1.1/> .
        @prefix v1: <http://purl.org/goodrelations/v1#> .
        @prefix obo: <http://purl.obolibrary.org/obo/> .
        @prefix owl: <http://www.w3.org/2002/07/owl#> .
        @prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
        @prefix xml: <http://www.w3.org/XML/1998/namespace> .
        @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
        @prefix dash: <http://datashapes.org/dash#> .
        @prefix obop: <http://purl.org/net/obop/> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
        @prefix chebi: <http://purl.obolibrary.org/obo/chebi/> .
        @prefix shacl: <http://www.w3.org/ns/shacl#> .
        @prefix schema: <http://schema.org/> .
        @base <http://example.org/logicinterface/testing/> .

        <http://example.org/logicinterface/testing> rdf:type owl:Ontology .


        ###  http://example.org/logicinterface/testing/block_1
        :block_1 rdf:type owl:NamedIndividual ,
                          obop:Block ;
                 obop:hasPositionNumber "1"^^xsd:int ;
                 dc:title "block_1 for Form"^^rdfs:Literal .


        ###  http://example.org/logicinterface/testing/field_1

        :field_1 rdf:type owl:NamedIndividual ,
                            obop:Field ;
                   obop:belongsTo :block_1 ;
                   obop:containsDatatype v1:legalName ;
                   obop:hasLabel "Field 1" ;
                   obop:hasPositionNumber "1"^^xsd:int ;
                   dc:title "field name" .

    ###  http://example.org/logicinterface/testing/field_2

        :field_2 rdf:type owl:NamedIndividual ,
                            obop:Field ;
                   obop:belongsTo :block_1 ;
                   obop:containsDatatype v1:legalName ;
                   obop:hasLabel "Field 2" ;
                   obop:hasPositionNumber "2"^^xsd:int .

    """
    caplog.set_level(logging.DEBUG, logger="ontoui_app")
    logger.debug("1. Load the model ")

    app: AppEngine = None
    app = AppEngine(config="test")
    app.model_graph = Graph()
    app.model_graph.parse(data=rdf_model)
    app.load_inner_app_model()
    assert app.inner_app_static_model is not None
    assert app.inner_app_static_model.forms is not None
    assert len(app.inner_app_static_model.forms) > 0
    logger.debug(
        f"Form: {jsonpickle.encode(app.inner_app_static_model.forms[0], indent=2)}"
    )
    app.run_application()
    response = app.app_interaction_model_instance.generate_layout()
    logger.debug("Output dictionary")
    logger.debug(jsonpickle.encode(response, indent=2))
    wanted_result = AppExchangeGetOutput(
        message_type="form",
        layout_type="form",
        message_content={
            "node": "http://example.org/logicinterface/testing/block_1",
            "schema": {
                "type": "object",
                "properties": {
                    "Field 1": {"type": "string", "position": 1},
                    "Field 2": {"type": "string", "position": 2},
                },
            },
            "uischema": {
                "type": "VerticalLayout",
                "elements": [
                    {"type": "Control", "scope": "#/properties/Field 1"},
                    {"type": "Control", "scope": "#/properties/Field 2"},
                ],
            },
        },
    )
    logger.debug("The difference is:")
    logger.debug(DeepDiff(response, wanted_result))
    assert response == wanted_result


def test_form_with_two_fields_and_vertical_layout(caplog):
    """
    There is only one block (form) with the corresponding  vertical layout
    and two fields in the form. The layout is generated with the vertical layout.
    """

    rdf_model = """
        @prefix : <http://example.org/logicinterface/testing/> .
        @prefix dc: <http://purl.org/dc/elements/1.1/> .
        @prefix v1: <http://purl.org/goodrelations/v1#> .
        @prefix obo: <http://purl.obolibrary.org/obo/> .
        @prefix owl: <http://www.w3.org/2002/07/owl#> .
        @prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
        @prefix xml: <http://www.w3.org/XML/1998/namespace> .
        @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
        @prefix dash: <http://datashapes.org/dash#> .
        @prefix obop: <http://purl.org/net/obop/> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
        @prefix chebi: <http://purl.obolibrary.org/obo/chebi/> .
        @prefix shacl: <http://www.w3.org/ns/shacl#> .
        @prefix schema: <http://schema.org/> .
        @base <http://example.org/logicinterface/testing/> .

        <http://example.org/logicinterface/testing> rdf:type owl:Ontology .


        ###  http://example.org/logicinterface/testing/block_1
        :block_1 rdf:type owl:NamedIndividual ,
                          obop:Block ;
                 obop:hasPositionNumber "0"^^xsd:int ;
                 dc:title "block_1 for Form"^^rdfs:Literal .

        ###  http://example.org/logicinterface/testing/vertical_layout_1
        :vertical_layout_1 rdf:type owl:NamedIndividual ,
                          obop:VerticalLayout ;
                 obop:belongsTo :block_1 ;
                 obop:hasPositionNumber "0"^^xsd:int ;
                 dc:title "Main vertical layout for the Form"^^rdfs:Literal .

               


        ###  http://example.org/logicinterface/testing/field_1

        :field_1 rdf:type owl:NamedIndividual ,
                            obop:Field ;
                   obop:belongsTo :block_1 ;
                   obop:belongsToVisual :vertical_layout_1 ;
                   obop:containsDatatype v1:legalName ;
                   obop:hasLabel "Field 1" ;
                   obop:hasPositionNumber "0"^^xsd:int ;
                   dc:title "field name" .

    ###  http://example.org/logicinterface/testing/field_2

        :field_2 rdf:type owl:NamedIndividual ,
                            obop:Field ;
                   obop:belongsTo :block_1 ;
                   obop:belongsToVisual :vertical_layout_1 ;
                   obop:containsDatatype v1:legalName ;
                   obop:hasLabel "Field 2" ;
                   obop:hasPositionNumber "1"^^xsd:int .

    """
    caplog.set_level(logging.DEBUG, logger="ontoui_app")
    logger.debug("1. Load the model ")

    # AppEngine is configured on testing settings through pytest.ini
    app: AppEngine = AppEngine()
    app.load_inner_app_model(rdf_string=rdf_model)
    assert app.inner_app_static_model is not None
    assert app.inner_app_static_model.forms is not None
    assert len(app.inner_app_static_model.forms) > 0
    # logger.debug(f"Form: {jsonpickle.encode(app.inner_app_static_model.forms[0], indent=2)}")
    # logger.debug(f"Layout: {jsonpickle.encode(app.inner_app_static_model.layouts[0], indent=2)}")
    app.run_application()
    response = app.app_interaction_model_instance.generate_layout()
    assert app.inner_app_static_model.layouts[0].type == "VerticalLayout"
    assert app.inner_app_static_model.layouts[0].position == Literal(
        "0", datatype=XSD.int
    )
    assert app.inner_app_static_model.layouts[0].graph_node == URIRef(
        "http://example.org/logicinterface/testing/vertical_layout_1"
    )
    assert (
        app.inner_app_static_model.layouts[0].owner_form
        == app.inner_app_static_model.forms[0]
    )
    logger.debug("Output dictionary")
    logger.debug(jsonpickle.encode(response, indent=2))
    wanted_result = AppExchangeGetOutput(
        message_type="layout",
        layout_type="form",
        message_content={
            "graph_node": "http://example.org/logicinterface/testing/block_1",
            "schema": {
                "type": "object",
                "properties": {
                    "Field 1": {"type": "string", "position": 0},
                    "Field 2": {"type": "string", "position": 1},
                },
            },
            "uischema": {
                "type": "VerticalLayout",
                "elements": [
                    {"type": "Control", "scope": "#/properties/Field 1"},
                    {"type": "Control", "scope": "#/properties/Field 2"},
                ],
            },
            "data": {},
        },
    )
    logger.debug("The difference is:")
    logger.debug(DeepDiff(response, wanted_result))
    assert response == wanted_result


def test_form_with_one_field_and_two_buttons_in_nested_horizontal_layout(caplog):
    """
    There is only one block (form) with the corresponding  vertical layout
    and one imput field in the form. The layout is generated with the vertical layout
    and nested horizontal layout for submit and cancel buttons.
    """

    caplog.set_level(logging.DEBUG, logger="ontoui_app")
    logger.debug("1. Load the model ")

    # AppEngine is configured on testing settings through pytest.ini
    app: AppEngine = AppEngine()
    # Reading the model from the file
    app.load_inner_app_model(file_name="test_submit_cancel_buttons.ttl")
    assert app.inner_app_static_model is not None
    assert app.inner_app_static_model.forms is not None
    assert len(app.inner_app_static_model.forms) > 0
    # logger.debug(f"Form: {jsonpickle.encode(app.inner_app_static_model.forms[0], indent=2)}")
    # logger.debug(f"Layout: {jsonpickle.encode(app.inner_app_static_model.layouts[0], indent=2)}")
    app.run_application()
    response = app.app_interaction_model_instance.generate_layout()
    logger.debug("Output dictionary")
    logger.debug(jsonpickle.encode(response, indent=2))
    wanted_result = AppExchangeGetOutput(
        message_type="layout",
        layout_type="form",
        message_content={
            "graph_node": "http://example.org/logicinterface/testing/block_1",
            "schema": {
                "type": "object",
                "properties": {
                    "Field 1": {"type": "string", "position": 0},
                },
            },
            "uischema": {
                "type": "VerticalLayout",
                "elements": [
                    {"type": "Control", 
                     "scope": "#/properties/Field 1"},
                    {
                        "type": "HorizontalLayout",
                        "elements": [
                            {"type": "Control", "scope": "#/properties/Submit"},
                            {"type": "Control", "scope": "#/properties/Cancel"},
                        ],
                    },
                ],
            },
            "data": {},
        },
    )
    logger.debug("The difference is:")
    logger.debug(DeepDiff(response, wanted_result))
    assert response == wanted_result
