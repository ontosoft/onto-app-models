from .forms import FormEncoder
from .uimodel import UIInternalModel
import json

class ProcessGenerator:
    def __init__(self, uimodel):
        self.uimodel:UIInternalModel = uimodel
        self.app_state: ApplicationState = ApplicationState()

    def generateLayout(self):
        """
        Generates the next layout in the control flow of the application
        A layout is, for example, an HTML form block that contains a 
        list of actions that can be performed on the form.
        """
        if self.app_state.current_form == -1:
            # check if we are at the start of the application
            self.app_state.current_form = 0
        if self.app_state.current_form >= len(self.uimodel.forms):
            return "No more forms"
        form_object = self.uimodel.forms[self.app_state.current_form]
        json_form = json.dumps(form_object, cls = FormEncoder)
        return json_form



class ApplicationState:
    def __init__(self):
        self._current_form = -1 # The index of the current form
        self._is_waiting_for_form_data = False

    @property
    def current_form(self):
        return self._current_form
    
    @current_form.setter
    def current_form(self, value):
        self._current_form = value

    @property
    def is_waiting_for_form_data(self):
        return self._is_waiting_for_form_data

    @is_waiting_for_form_data.setter
    def is_waiting_for_form_data(self, value):
        self._is_waiting_for_form_data = value
