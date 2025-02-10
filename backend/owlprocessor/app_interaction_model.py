from .forms import FormEncoder
from .app_model import AppInternalModel
from .communication import FrontEndData
import json
import logging

logger = logging.getLogger('ontoui_app')

class AppInteractionModel:
    """
    This class represents the running application. It is reposible for
    generating the next layout in the control flow of the application. 
    """
    def __init__(self, uimodel):
        self.uimodel:AppInternalModel = uimodel
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
 
    def generateLayout(self):
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
        if self.app_state.current_form_index >= len(self.uimodel.forms):
            return "No more forms"
        form_object = self.uimodel.forms[self.app_state.current_form_index]
        json_form = json.dumps(form_object, cls = FormEncoder)
        message = { 
            "message_type": "form",
            "layout_type": "form",
            "message_content": json_form }
        self.app_state.is_waiting_for_form_data = True 
        logger.debug("Message to the frontend has the content:\n" + json.dumps(message))
 
        return json.dumps(message)



class ApplicationState:
    def __init__(self):
        self._current_form_index = -1 # The index of the current form
        self._is_waiting_for_form_data = False
        self._running_initiated = False
        self._app_exchange_waiting_to_send_data = False

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
    
    def setRunningInitiated(self):
        self._running_initiated = True

    def setAppExchangeWaitingToSendData(self):
        self._app_exchange_waiting_to_send_data = True
    
    def setAppExchangeWaitingToSendDataFalse(self):
        self._app_exchange_waiting_to_send_data = False
