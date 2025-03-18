from rdflib import Graph
from .app_interaction_model import AppInteractionModel
from .app_model_factory import UIModelFactory
from .app_model import AppInternalStaticModel
from .communication import FrontEndData
from pathlib import Path
import jsonpickle
import logging

logger = logging.getLogger('ontoui_app')

class App():
    """
    Represents the entry point for the backend model.

    """
    def __init__(self, config = "development") -> None:
        """_summary_

        Attributes:
        - inner_app_static_model (AppInternalModel): The internal representation of the
        application model that is read from an RDF graph 
        and is used to generate the UI and App functionality. It is
        a static model of data and is not changed during the application run.

        - local_app_interaction_model_instance (AppInteractionModel)
         is an object that represents the current state of the application. 
         It is generated from the inner_app_static_model and is used to 
         generate the UI and App functionality. It is a dynamic model of
         data and is changed during the application run.  

        """
        self.inner_app_static_model: AppInternalStaticModel = None 
        self.app_interaction_model_instance: AppInteractionModel = None
        self.model_graph: Graph = None
        self.is_model_graph_read = False
        self.is_inner_app_static_model_loaded = False
        self.model_name = None
        self.model_directory = None
        self.config = config

        if self.config == "development":
            self.model_directory = Path("./app_models")
            logger.debug("The application has a model directory set to the default value. {model_directory}")
        elif self.config == "test":
            self.model_directory = Path("./tests/test_models")
            logger.debug("The application has a model directory set to the default value. {model_directory}")
        elif self.config == "production":
            self.model_directory = Path("/app_models")
        self.model_directory.mkdir(parents=True, exist_ok=True)
    
    def read_graph(self, rdf_file_name: str):
        """
        Reads an RDF file and parses it into the model_graph attribute.

        Args:
            rdf_file (str): The path to the RDF file.
        """
        logger.debug(f"Reading and parsing the RDF file {rdf_file_name}")
        filePath = self.model_directory.joinpath(rdf_file_name)
        self.model_graph = Graph()
        self.model_graph.parse(filePath, format="ttl") 
        self.is_model_graph_read = True

    def load_inner_app_model(self):
        """
             Reads the Application model from the model_graph attribute and 
             assigns it to the inner_app_model attribute.
        """
 
        model_factory = UIModelFactory()
        self.inner_app_static_model = model_factory.rdf_graf_to_uimodel(self.model_graph)
        logger.debug("Application model loaded from the RDF graph.")
        logger.debug(self.inner_app_static_model)
        self.is_inner_app_static_model_loaded = True

    def run_application(self):
        if self is not None and self.is_inner_app_static_model_loaded and \
            self.app_interaction_model_instance is None:
            self.app_interaction_model_instance = AppInteractionModel(self.inner_app_static_model)
            logger.debug("A new application interaction is started.")
            #logger.debug(json.dumps(self.processGenerator.__dict__))
            #logger.debug(jsonpickle.encode(self.localAppInteractionModelInstance))
        else :
            logger.debug("An application is already being running.")
            #logger.debug(json.dumps(self.processGenerator.__dict__))
            logger.debug(jsonpickle.encode(self.app_interaction_model_instance))

    def read_new_model_layout(self):
        """
        Reads the new model layout from the running interaction model instance 
        """
        if self.inner_app_static_model is None:
            return {"message":"An application model is not loaded."}
        elif self.app_interaction_model_instance is None: 
            return {"message":"An application is not running."}
        else:
            newModelLayout = self.app_interaction_model_instance.generate_layout()
        return newModelLayout

    def processReceivedClientData(self, frontend_state: any):
        """
        Precesses and stores the new model data into the output 
        knowledge graph
        TODO better comment  
        """
        if self.inner_app_static_model is None:
            return {"message":"An application model is not loaded."}
        elif self.app_interaction_model_instance is None: 
            return {"message":"An application is not running."}
        else:
            # Parse the JSON data into a FrontEndData object
            received_data = FrontEndData(**frontend_state)
            processing_result = self.app_interaction_model_instance.processReceivedClientData(received_data)
        return processing_result
  
    
