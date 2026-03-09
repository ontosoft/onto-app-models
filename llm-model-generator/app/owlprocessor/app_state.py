import logging
from .app_model import AppInternalStaticModel
from .forms import FunctionalJSONForm
from .bbo_elements import BBOFlowElementsContainer, BBOFlowElement, BBOProcessStartEvent
from .forms import ActiveForm
from .forms import JSONFormNameMapping
from .obop_action import OBOPAction
from .communication import AppExchangeGetOutput
from .communication import AppExchangeFrontEndData
from typing import Literal


logger = logging.getLogger('ontoui_app')
LayoutTypes = Literal["form", "message-box", ""]

class ApplicationState:
    def __init__(self, inner_app_static_model: AppInternalStaticModel = None):
        self._inner_app_static_model: AppInternalStaticModel = \
            inner_app_static_model
        self._current_flow_element_container : BBOFlowElementsContainer = \
            self.inner_app_static_model.main_bbo_process
        # The current control flow element is 
        # used to keep track of the current control flow in the application
        # When the process starts, a token is placed at the
        # ProcessStartEvent by assigning the process start event
        # to the current flow element
        self.current_flow_element : BBOFlowElement = next((e for e in self. \
            current_flow_element_container.flow_elements 
            if isinstance(e, BBOProcessStartEvent)), None)
        self._is_waiting_for_form_data = False
        # This flag indicates if the backend is waiting for form data from the frontend
        self._is_waiting_to_send_data = False
        # This flag indicates if the backend is waiting to send data to the frontend
        self.is_waiting_to_process_front_end_data = False
        # This flag indicates that the frontend data has to be processed
        self._running_initiated = False
        self._layout_type : LayoutTypes = None
        # The message type is used to specify what kind of message
        # is sent to the frontend. 
        self._current_json_form_name_mapping : JSONFormNameMapping = {}
        self._json_form : FunctionalJSONForm = None
        self._list_of_active_forms: list[ActiveForm]= []  # List of forms sent to the frontend for editing
        #This list of forms is used to keep track of named individuaals
        # that are created during the previous form exchanges
        # If a form has a named individual here it means that properties are only being
        # changed and shouldn't be created again. 
        self._received_action : OBOPAction = None
        self._frontend_message: AppExchangeFrontEndData
        self._output_messaage: AppExchangeGetOutput = None
        self._app_finished: bool = False

    @property
    def inner_app_static_model(self) -> AppInternalStaticModel:
        return self._inner_app_static_model
    @inner_app_static_model.setter
    def inner_app_static_model(self, value: AppInternalStaticModel):
        self._inner_app_static_model = value
    @property
    def current_flow_element_container(self)-> BBOFlowElementsContainer:
        return self._current_flow_element_container
    @current_flow_element_container.setter
    def current_flow_element_container(self, value: BBOFlowElementsContainer):
        self._current_flow_element_container = value
    
    @property
    def current_flow_element(self)-> BBOFlowElement:
        return self._current_flow_element
    @current_flow_element.setter
    def current_flow_element(self, value: BBOFlowElement):
        self._current_flow_element = value
    def current_form_index(self, value):
        self._current_form_index = value

    @property
    def is_waiting_for_form_data(self)-> bool:
        return self._is_waiting_for_form_data

    @is_waiting_for_form_data.setter
    def is_waiting_for_form_data(self, value):
        self._is_waiting_for_form_data = value

    @property
    def is_waiting_to_send_data(self)-> bool:
        return self._is_waiting_to_send_data 
    
    @is_waiting_to_send_data.setter
    def is_waiting_to_send_data(self, value: bool):
        self._is_waiting_to_send_data = value

    @property
    def is_waiting_to_process_front_end_data(self)-> bool:
        return self._is_waiting_to_process_front_end_data

    @is_waiting_to_process_front_end_data.setter
    def is_waiting_to_process_front_end_data(self, value:bool):
        self._is_waiting_to_process_front_end_data = value

    @property
    def current_json_form_name_mapping(self):
        return self._current_json_form_name_mapping

    @current_json_form_name_mapping.setter
    def current_json_form_name_mapping(self, value):
        self._current_json_form_name_mapping = value

    @property
    def json_form(self)-> FunctionalJSONForm:
        return self._json_form
    @json_form.setter
    def json_form(self, value: FunctionalJSONForm):
        self._json_form = value

    @property
    def list_of_active_forms(self):
        return self._list_of_active_forms

    @list_of_active_forms.setter
    def list_of_active_forms(self, value: list["ActiveForm"]):
        self._list_of_active_forms = value

    def set_running_initiated(self):
        self._running_initiated = True

    @property
    def layout_type(self)-> LayoutTypes:
        return self._layout_type

    @layout_type.setter
    def layout_type(self, value: LayoutTypes):
        self._layout_type = value

    @property
    def received_action(self)-> OBOPAction:
        return self._received_action

    @received_action.setter
    def received_action(self, value: OBOPAction):
        self._received_action = value

    @property
    def frontend_message(self)-> AppExchangeFrontEndData:
        return self._frontend_message
    
    @frontend_message.setter
    def frontend_message(self, value : AppExchangeFrontEndData):
        self._frontend_message = value
    
    @property
    def output_message(self)-> AppExchangeGetOutput:
        return self._output_messaage

    @output_message.setter
    def output_message(self, value: AppExchangeGetOutput):
        self._output_message = value

    @property
    def app_finished(self)-> bool:
        return self._app_finished
    @app_finished.setter
    def app_finished(self, value: bool):
        self._app_finished = value  
 