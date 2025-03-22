from fastapi.testclient import TestClient 
from main import app
from owlprocessor.app_engine import AppEngine
import jsonpickle
import logging

client = TestClient(app)
logger = logging.getLogger("ontoui_app")


# Tests should run from the tests directory
class LoadingTest:
    def test_list_of_models(self):
        response = client.get("/read_inner_server_models")
        assert response.status_code == 200
        print (response.json())


    """
    This test checks if the application loads the model from the RDF file.
    and runs the application.
    """
    def test_run_application(caplog):
        logger.debug("Test the whole cycle of the application with the model loaded from the restaurant-model-ttl1.ttl RDF file ")
        logger.debug("1. Load the model from the RDF file restaurant-model-ttl1.ttl ")
        response = client.get("/load_inner_uimodel_from_server?filename=restaurant-model-ttl1.ttl")
        logger.debug("2. Run the application")
        assert response.status_code == 200
        response = client.get("/run_application")
        assert response.status_code == 200
        initiating_message = {
            "message_type": "initiate_exchange",
            "message_content": {}
        }
        logger.debug("3. Send a message to initiate exchange with the application")
        response = client.post("/app_exchange_post", json=initiating_message)
        assert response.status_code == 200
        logger.debug("3. Receive the response from the application")
        response = client.get("/app_exchange_get")
        assert response.status_code == 200
        logger.debug("Data exchange got the following response: ")
        logger.debug(response.json())


    def test_combine_shacl_properties_and_obop_elements():

        """
            Test combining SHACL properties and OBOP elements
        """
        logger.debug("1. Load the model from the RDF file test_combine_properties.ttl ")

        app1: AppEngine = None
        app1 = AppEngine( config = "test")
        app1.read_graph("test_combine_properties.ttl")
        app1.load_inner_app_model()
        assert app1.innerAppModel is not None
        assert app1.innerAppModel.forms is not None
        assert len(app1.innerAppModel.forms) > 0
        logger.debug(f"Form: {jsonpickle.encode(app1.innerAppModel.forms[0], indent=4)}")
        assert app1.innerAppModel.forms[0].node is not None
        for element in app1.innerAppModel.forms[0].elements:
            logger.debug(f"Element: {element}")

        logger.debug("2. Combined SHACL property")
        app1.innerAppModel.forms[0]