from fastapi.testclient import TestClient 
from pythonjsonlogger import jsonlogger
from pprint import pprint
from rdflib import Graph
from main import app
from owlprocessor.app import App
import jsonpickle
import logging
import os
import pytest
# Change the current working directory to the parent directory
os.chdir(os.path.dirname(os.getcwd()))


client = TestClient(app)
logger = logging.getLogger("ontoui_app")

# Configure the logging for the pretty print of the json logs
log_format = "%(asctime)s - %(module)s#%(lineno)d - %(levelname)s - %(message)s"
formatter = jsonlogger.JsonFormatter(
    fmt=log_format, rename_fields={"levelname": "level", "asctime": "date"}
)

logger_json = logging.getLogger()

json_h= logging.FileHandler("errors.ndjson", mode="w")
json_h.setFormatter(formatter)
logger_json.addHandler(json_h)
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

def test_read_textual_field_model(caplog):

    """
        Test only one single field 
    """
    caplog.set_level(logging.DEBUG, logger="ontoui_app")
    logger.debug("1. Load the model ")

    app: App = None
    app = App( config = "test")
    app.model_graph = Graph()
    app.model_graph.parse(data = rdf_model)
    app.load_inner_app_model()
    assert app.innerAppModel is not None
    assert app.innerAppModel.forms is not None
    assert len(app.innerAppModel.forms) > 0
    logger.debug(f"Form: {jsonpickle.encode(app.innerAppModel.forms[0], indent=2)}")
    logger.debug("Output")
    app.run_application()
    response = app.app_interaction_model_instance.generate_layout()
    wanted_result ={
            "node": "http://example.org/logicinterface/testing/field_1" ,
            "schema": {
                "type": "object",
                "properties": {
                     "http://example.org/logicinterface/testing/field_1": {
                    "type": "string",
                    "position": 1
                    }
                }
            },
            "uischema": {
                "type": 'VerticalLayout',
                "elements": [
                    
                ]
            }
        }
    assert response == wanted_result  
    assert app.innerAppModel is not None