from rdflib import Graph
import logging
from owlprocessor.process_generator import ProcessGenerator
from owlprocessor.ui_model_factory import UIModelFactory
from owlprocessor.uimodel import UIInternalModel

logger = logging.getLogger('ontoui_app')
logger.setLevel(logging.DEBUG)
class ApplicationModel():
    """
    Represents the application model.

    Attributes:
        uiModel (UIInternalModel): The internal representation of the UI model
                        that is generated from the RDF graph and is used to generate the UI.
    """
    def __init__(self) -> None:
        self.uiModel: UIInternalModel = None 
        self.processGenerator: ProcessGenerator = None
        self.graphRead = False
        self.modelLoaded = False
        self.modelName = None
    
    def readGraph(self, rdf_file: str):
        """
        Reads an RDF file and parses it into the modelGraph attribute.

        Args:
            rdf_file (str): The path to the RDF file.
        """
        self.modelGraph = Graph()
        self.modelGraph.parse(rdf_file) 
        self.graphRead = True

    def loadUIModel(self):
        """
             Reads the UI model from the modelGraph attribute and 
             assigns it to the uiModel attribute.
        """
 
        modelFactory = UIModelFactory()
        self.uiModel = modelFactory.rdf_graf_to_uimodel(self.modelGraph)
        logging.debug("UI Model loaded from the RDF graph.")
        logging.debug(self.uiModel)
        self.modelLoaded = True

    def runApplication(self):
        if self.processGenerator is None:
            self.processGenerator = ProcessGenerator(self.uiModel)
            logging.debug("Process generator created.")
       

    def readNewModelLayout(self):
        """
        Reads the new model layout from the modelGraph attribute 
        """
        if self.uiModel is None:
            return "RDF model is not loaded"
        elif self.processGenerator is None: 
            return "Process generator is not created"

        newModelLayout = self.processGenerator.generateLayout()
        return newModelLayout


    
