from .process_engine import ProcessEngine
from .app_model_factory import AppStaticModelFactory
from .app_model import AppInternalStaticModel
from .communication import AppExchangeFrontEndData, AppExchangeGetOutput
from pathlib import Path
import logging
from app.core.config import settings, Settings


logger = logging.getLogger('ontoui_app')

class AppEngine():
    """
    One loaded application: its static model plus the running process.
    Represents the entry point for the OWL processor.

    The entry point the API/session layer talks to. Lifecycle:
    'load_inner_app_model' parses the RDF model into the static model,
    'run_application' starts a ProcessEngine over it, and the
    'app_exchange' calls drive that process until it finishes or
    'reset' drops it.

    Attributes:
        internal_app_static_model (AppInternalStaticModel): The internal
            representation of the application model that is read from an RDF graph
            (UI blocks, SHACL shapes, BBO controls) and is used to generate the UI
            and App functionality. This is a static model of data which is not
            changed during the application execution.
        process_engine_instance (ProcessEngine): An object that represents
            the current state of the running application.
            It is generated from the internal_app_static_model and is used to
            generate the UI and App functionality. It is a dynamic representation of
            the application model and is changed during the application run.
            It is an execution of the BPMN process.
        model_name (str | None): Name of the loaded model, used in status
            and user-facing messages; set by load_inner_app_model from the
            given model name or the file name.
        model_directory (Path): Directory where model files are looked up
            when a model is loaded by file name; taken from
            settings.MODEL_DIRECTORY.
    """
    def __init__(self) -> None:

        self.internal_app_static_model: AppInternalStaticModel = None
        self.process_engine_instance: ProcessEngine = None
        self.model_name = None
        self.model_directory : Path = settings.MODEL_DIRECTORY

    def load_inner_app_model(
        self, file_name: Path = None, rdf_string: str = None, model_name: str = None
    ):
        """
             Loads the Application model from the rdf graph either in the file or
             as a string. Only one of the two parameters can be used at a time.
             ``model_name`` optionally names the model for status()/messages
             (e.g. the AppModel title on DB runs); file loads default to the
             file name.
        """

        logger.debug("Loading the server-side static application model.")
        # Record what is being loaded so status()/user-facing messages can name
        # it (previously never assigned -> "The model is loaded None by force.").
        self.model_name = model_name or (
            str(file_name) if file_name is not None else None
        )
        model_factory = AppStaticModelFactory()
        filePath : Path = file_name
        if file_name is not None:
            filePath = self.model_directory/file_name
        self.internal_app_static_model = model_factory.rdf_graf_to_uimodel(rdf_model_file=filePath, rdf_text_ttl=rdf_string)

    def reset(self) -> None:
        """Drop the running process engine so this engine can start a fresh run.

        Called when a session id is reused (or a new model loaded) so that
        run_application (which only creates a ProcessEngine when the instance is
        None) starts clean instead of returning "already running".
        """
        self.process_engine_instance = None

    def run_application(self)-> None:
        """
        Starts the process_engine_instance which is the application interaction model instance.

        """
        if self is not None and self.internal_app_static_model is not None and \
            self.internal_app_static_model.is_loaded and \
            self.process_engine_instance is None:
            self.process_engine_instance = ProcessEngine(self.internal_app_static_model)
            logger.debug("A new proceess engine instance is started.")
            # The application state is updated to indicate that the application is running
            # and is waiting to get initiated data from the frontend
            self.process_engine_instance.app_state.set_running_initiated()
        elif self is not None and self.internal_app_static_model is not None and \
            self.internal_app_static_model.is_loaded and \
            self.process_engine_instance is not None and \
                 self.process_engine_instance.app_state.is_running_initiated:
            logger.debug("The application is already running.")
            #logger.debug(json.dumps(self.processGenerator.__dict__))
            #logger.debug(jsonpickle.encode(self.app_interaction_model_instance))

    def read_new_model_layout(self)-> AppExchangeGetOutput:
        """
        Reads the new model layout from the running interaction model instance (process engine).
        """
        if self.internal_app_static_model is None:

            return AppExchangeGetOutput(
                message_type ="error",
                layout_type="message_box",
                message_content = {"message" : "An application model is not loaded."})
        elif self.process_engine_instance is None:
            return AppExchangeGetOutput(
                message_type ="notification",
                layout_type="message_box",
                message_content = {"message" : "An application model is not running. Run the corresponding model."})
        else:
            newModelLayout : AppExchangeGetOutput = self.process_engine_instance.generate_layout()
        return newModelLayout

    def process_received_client_data(self, frontend_state: any):
        """
        Precesses the new data from the frontend and stores it into the output
        knowledge graph
        """
        if self.internal_app_static_model is None:
            return AppExchangeGetOutput(
                message_type ="error",
                layout_type="message_box",
                message_content = {"message" : "An application model is not loaded."})


        elif self.process_engine_instance is None:
            return AppExchangeGetOutput(
                message_type ="error",
                layout_type="message_box",
                message_content = {"message" : "An application is not running."})
        else:
            # Parse the JSON data into a AppExchangeFrontEndData object
            received_data = AppExchangeFrontEndData(**frontend_state)
            processing_result = self.process_engine_instance.process_received_client_data(received_data)
        return processing_result


