from rdflib import Graph
from .app_interaction_model import AppInteractionModel
from .app_model_factory import UIModelFactory
from .app_model import AppInternalModel
from .communication import FrontEndData
import json
import jsonpickle
import logging

logger = logging.getLogger('ontoui_app')

class App():
    """
    Represents the entry point for the backend model.

    """
    def __init__(self) -> None:
        """_summary_

        Attributes:
        - innerAppStaticModel (AppInternalModel): The internal representation of the
        application model that is read from an RDF graph 
        and is used to generate the UI and App functionality. It is a 
        static model of data and is not changed during the application run.

        - localAppInteractionModelInstance (AppInteractionModel): an object that represents the current state of the application. It is generated from the innerAppModel and is used to generate the UI and App functionality. It is a dynamic model of data and is changed during the application run.  

        """
        self.innerAppStaticModel: AppInternalModel = None 
        self.localAppInteractionModelInstance: AppInteractionModel = None
        self.modelGraph = None
        self.modelGraphRead = False
        self.isInnerAppModelLoaded = False
        self.modelName = None
    
    def readGraph(self, rdf_file: str):
        """
        Reads an RDF file and parses it into the modelGraph attribute.

        Args:
            rdf_file (str): The path to the RDF file.
        """
        logger.debug(f"Reading and parsing the RDF file {rdf_file}")
        self.modelGraph = Graph()
        self.modelGraph.parse(rdf_file) 
        self.modelGraphRead = True

    def loadInnerAppModel(self):
        """
             Reads the Application model from the modelGraph attribute and 
             assigns it to the innerAppModel attribute.
        """
 
        modelFactory = UIModelFactory()
        self.innerAppModel = modelFactory.rdf_graf_to_uimodel(self.modelGraph)
        logger.debug("Application model loaded from the RDF graph.")
        logger.debug(self.innerAppModel)
        self.isInnerAppModelLoaded = True

    def runApplication(self):
        if self is not None and self.isInnerAppModelLoaded and \
            self.localAppInteractionModelInstance is None:
            self.localAppInteractionModelInstance = AppInteractionModel(self.innerAppModel)
            logger.debug("A new application interaction is started.")
            #logger.debug(json.dumps(self.processGenerator.__dict__))
            #logger.debug(jsonpickle.encode(self.localAppInteractionModelInstance))
        else :
            logger.debug("An application is already being running.")
            #logger.debug(json.dumps(self.processGenerator.__dict__))
            logger.debug(jsonpickle.encode(self.localAppInteractionModelInstance))

    def readNewModelLayout(self):
        """
        Reads the new model layout from the modelGraph attribute 
        """
        if self.innerAppModel is None:
            return {"message":"An application model is not loaded."}
        elif self.localAppInteractionModelInstance is None: 
            return {"message":"An application is not running."}
        else:
            newModelLayout = self.localAppInteractionModelInstance.generateLayout()
        return newModelLayout

    def processReceivedClientData(self, frontend_state: any):
        """
        Precesses and stores the new model data to the modelGraph.  
        """
        if self.innerAppModel is None:
            return {"message":"An application model is not loaded."}
        elif self.localAppInteractionModelInstance is None: 
            return {"message":"An application is not running."}
        else:
            # Parse the JSON data into a FrontEndData object
            received_data = FrontEndData(**frontend_state)
            resultOfProcessing = self.localAppInteractionModelInstance.processReceivedClientData(received_data)
        return resultOfProcessing
  
    
