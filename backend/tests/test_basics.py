from fastapi.testclient import TestClient 
from pythonjsonlogger import jsonlogger
from pprint import pprint
from main import app
import logging
import json
import os
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

def test_list_of_models():
    response = client.get("/read_inner_server_models")
    assert response.status_code == 200
    print (response.json())


"""
This test checks if the application loads the model from the RDF file.
and runs the application.
"""
def test_run_application(caplog):
    caplog.set_level(logging.DEBUG, logger="ontoui_app")
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
    logger_json.debug(response.json())

