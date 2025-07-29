from .app_interaction_model import AppInteractionModel
from .app_model_factory import AppStaticModelFactory
from .app_model import AppInternalStaticModel
from .communication import AppExchangeFrontEndData, AppExchangeGetOutput
from pathlib import Path
import jsonpickle
import logging
from config.settings import get_settings, Settings 


settings:Settings = get_settings()
logger = logging.getLogger('ontoui_app')

class AppEngine():
    """
    Represents the entry point for the backend model.

    """
    def __init__(self) -> None:
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
        # The interaction model instance is created from the inner_app_static_model
        # and is used to represents the running application. It is basically a dynamic
        # representation of the application model
        self.model_name = None
        self.model_directory : Path = settings.MODEL_DIRECTORY

    def load_inner_app_model(self, file_name: Path = None, rdf_string: str = None):
        """
             Loads the Application model from the rdf graph either in the file or
             as a string. Only one of the two parameters can be used at a time.
        """
 
        logger.debug("Loading the server-side application model.")
        model_factory = AppStaticModelFactory()
        filePath : Path = file_name
        if file_name is not None:
            filePath = self.model_directory/file_name
        self.inner_app_static_model = model_factory.rdf_graf_to_uimodel(rdf_model_file=filePath, rdf_text_ttl=rdf_string)

    def run_application(self)-> None:
        """
        Starts the application interaction model instance. The main part is 
        the process that generates an instance of the application interaction model
        
        """
        if self is not None and self.inner_app_static_model is not None and \
            self.inner_app_static_model.is_loaded and \
            self.app_interaction_model_instance is None:
            self.app_interaction_model_instance = AppInteractionModel(self.inner_app_static_model)
            logger.debug("A new application interaction is started.")
            # The application state is updated to indicate that the application is running
            # and is waiting to get initiated data from the frontend 
            self.app_interaction_model_instance.app_state.setRunningInitiated()
            self.app_interaction_model_instance.app_state.setAppExchangeWaitingToSendData()  
        elif self is not None and self.inner_app_static_model is not None and \
            self.inner_app_static_model.is_loaded and \
            self.app_interaction_model_instance is not None and \
                 self.app_interaction_model_instance.app_state.is_running_initiated: 
            logger.debug("The application is already running.")
            #logger.debug(json.dumps(self.processGenerator.__dict__))
            #logger.debug(jsonpickle.encode(self.app_interaction_model_instance))

    def read_new_model_layout(self)-> AppExchangeGetOutput:
        """
        Reads the new model layout from the running interaction model instance 
        """
        if self.inner_app_static_model is None:

            return AppExchangeGetOutput(
                message_type ="error",
                layout_type="message_box",
                message_content = {"message" : "An application model is not loaded."})
        elif self.app_interaction_model_instance is None: 
            return AppExchangeGetOutput(
                message_type ="notification",
                layout_type="",
                message_content = {"message" : "An application model is not loaded. Load the corresponding model."})
        else:
            newModelLayout : AppExchangeGetOutput = self.app_interaction_model_instance.generate_layout()
        return newModelLayout

    def processReceivedClientData(self, frontend_state: any):
        """
        Precesses the new data from the frontend and stores it into the output 
        knowledge graph
        """
        if self.inner_app_static_model is None:
            return AppExchangeGetOutput(
                message_type ="error",
                layout_type="message_box",
                message_content = {"message" : "An application model is not loaded."})


        elif self.app_interaction_model_instance is None: 
            return AppExchangeGetOutput(
                message_type ="error",
                layout_type="message_box",
                message_content = {"message" : "An application is not running."})
        else:
            # Parse the JSON data into a AppExchangeFrontEndData object
            received_data = AppExchangeFrontEndData(**frontend_state)
            processing_result = self.app_interaction_model_instance.processReceivedClientData(received_data)
        return processing_result
  
    
