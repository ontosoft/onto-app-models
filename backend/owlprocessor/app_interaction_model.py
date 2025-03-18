from .forms import Form
from .app_model import AppInternalStaticModel as AppStaticModel
from .communication import FrontEndData
import json
import logging
import jsonpickle
from collections.abc import Mapping

logger = logging.getLogger('ontoui_app')

class AppInteractionModel:
    """
    This class represents the running application. It is reposible for
    generating the next layout in the control flow of the application. 
    """
    def __init__(self, uimodel):
        self.inner_app_static_model:AppStaticModel = uimodel
        self.app_state: ApplicationState = ApplicationState()

    def processReceivedClientData(self, frontend_state : FrontEndData):
        """
        Processes the data received from the frontend.
        """
        logger.debug(f"Message from the frontend has the type:\n {frontend_state.message_type}")
        logger.debug(f"Message from the frontend has the content:\n {frontend_state.message_content}") 
        self.app_state.setRunningInitiated()
        self.app_state.setAppExchangeWaitingToSendData()
        return True
 
    def generate_layout(self):
        """
        Generates the next layout in the control flow of the application
        A layout is, for example, a description of an HTML form block that contains a 
        list of actions that can be performed on the form.
        """
        if self.app_state.current_form_index == -1:
            # Checking if we are at the start of the application execution
            self.app_state.current_form_index = 0
        # TODO: This should be changed to a more sophisticated 
        #  way of checking the end of
        if self.app_state.current_form_index >= len(self.inner_app_static_model.forms):
            return "No more forms"
        form_object : Form = self.inner_app_static_model.forms[self.app_state.current_form_index]
        json_form = form_object.create_json_form_schemas(self.app_state) 
        logger.debug(f" Created form is {jsonpickle.encode(json_form, indent=2)}")
        message = { 
            "message_type": "form",
            "layout_type": "form",
            "message_content": json_form }
        self.app_state.is_waiting_for_form_data = True 
        return json.dumps(message)



class ApplicationState:
    def __init__(self):
        self._current_form_index = -1 # The index of the current form
        self._is_waiting_for_form_data = False
        self._running_initiated = False
        self._app_exchange_waiting_to_send_data = False
        self._current_json_form_name_mapping : JSONFormNameMapping = {}

    @property
    def current_form_index(self):
        return self._current_form_index
    
    @current_form_index.setter
    def current_form_index(self, value):
        self._current_form_index = value

    @property
    def is_waiting_for_form_data(self):
        return self._is_waiting_for_form_data

    @is_waiting_for_form_data.setter
    def is_waiting_for_form_data(self, value):
        self._is_waiting_for_form_data = value

    @property
    def current_json_form_name_mapping(self):
        return self._current_json_form_name_mapping

    @current_json_form_name_mapping.setter
    def current_json_form_name_mapping(self, value):
        self._current_json_form_name_mapping = value
    
    def setRunningInitiated(self):
        self._running_initiated = True

    def setAppExchangeWaitingToSendData(self):
        self._app_exchange_waiting_to_send_data = True
    
    def setAppExchangeWaitingToSendDataFalse(self):
        self._app_exchange_waiting_to_send_data = False


class JSONFormNameMapping(Mapping):
    """ 
    This dictionary stores the temporary mapping of property 
    names for the JSONForm generation.
    After the frontend returns inserted form data this mapping is 
    used to identify correct Ontology concepts such as anindividual 
    of a specific Ontology class.
    The reason for this mapping is that the form names such as 
    "http://example.org/logicinterface/testing/field_1" are not
    allowed in a JSONForm schema.
    """
    def __init__(self, name_mapping: dict):
        super().__init__()
        self._name_mapping = name_mapping
    def __getitem__(self, key):
        if key not in self and len(key) > 1:
            raise KeyError(key)
        return self._name_mapping(key)
    def __setitem__(self, key, value):
        self._name_mapping[key] = value
    def __iter__(self):
            return iter(self._name_mapping)
    def __len__(self):
        return len(self._name_mapping) 
