from .forms import Form, FunctionalJSONForm
from rdflib import Graph, Namespace, RDF, URIRef, Literal
from .app_model import AppInternalStaticModel, Action 
from .bbo_elements import BBOFlow, BBOEvent, BBOActivity
from .communication import AppExchangeFrontEndData,  AppExchangeGetOutput
import logging
import jsonpickle
from collections.abc import Mapping
from uuid import uuid4



OBOP = Namespace("http://purl.org/net/obop/")
BASE = Namespace("http://example.org/logicinterface/testing/instance/")
logger = logging.getLogger('ontoui_app')

class AppInteractionModel:
    """
    This class represents the running application. It is reposible for
    generating the next layout in the control flow of the application. 
    """
    def __init__(self, uimodel):
        self.inner_app_static_model:AppInternalStaticModel = uimodel

        self.output_graph_store : Graph = Graph()
        self.app_state: ApplicationState = ApplicationState()

    def processReceivedClientData(self, frontend_state : AppExchangeFrontEndData):
        """
        Processes the data received from the frontend.
        """
        logger.debug(f"Message from the frontend has the type:\n {frontend_state.message_type}")
        logger.debug(f"Message from the frontend has the content:\n {frontend_state.message_content}") 
        if frontend_state.message_type == "initiate_exchange":
            # The frontend has sent the data to start the first data exchange with the application
            return True
        elif frontend_state.message_type == "action":
            self.action_processor(frontend_state.message_content)
                

        # The backend is wating to send data to the frontend in the next 
        # appExchange_get request
        self.app_state.setAppExchangeWaitingToSendData()
        return True
 
    def generate_layout(self)-> AppExchangeGetOutput:
        """
        Generates the next layout in the control flow of the application
        A layout is, for example, a description of an HTML form block that contains a 
        list of actions that can be performed on the form.
        """
        if self.app_state.current_form_index == -1:
            # Checking if we are at the start of the application execution
            self.app_state.current_form_index = 0
        # TODO: This should be changed to a more sophisticated 
        #  way of checking the end of the application execution
        data = self.output_graph_store.serialize(format="turtle")
        logger.debug(f"Output graph store has the data:\n {data}")
        if self.app_state.current_form_index >= len(self.inner_app_static_model.forms):
            output_message = AppExchangeGetOutput(
                message_type = "error",
                layout_type = "notification",
                message_content = "The application has finished.",
                output_knowledge_graph = data)
            return  output_message
        else:
            form_object : Form = self.inner_app_static_model.forms[self.app_state.current_form_index]
            json_form:FunctionalJSONForm = form_object.create_functional_json_form_schemas(self.app_state) 
            # Speicifyin that the form ia being sent to the frontend 
            # and the backend is waiting for the form data to be sent back
            active_form = ActiveForm(form_object)
            self.app_state.list_of_active_forms.append(active_form)
            logger.debug(f"New active form created for {active_form.graph_node}")

            logger.debug(f" Created form is {jsonpickle.encode(json_form, indent=2)}")
            output_message = AppExchangeGetOutput(
                message_type = "layout",
                layout_type = "form",
                message_content = json_form,
                output_knowledge_graph = data)
            self.app_state.is_waiting_for_form_data = True 
            return output_message

    def action_processor(self, action_message: dict):
        """
        Processes the action data received from the frontend.
        """
        logger.debug(f"Action data received from the frontend: {action_message}")
        # The frontend has sent the data to process the action
        action_node = action_message["action_graph_node"]
        if action_message["action_type"] == "submit":
            form_graph_node = action_message["form_graph_node"]
            form_data = action_message["form_data"]
            logger.debug(f"Form data from the frontend is:\n {form_data}")
            action : Action = next(filter(lambda x: x.graph_node == action_node, self.inner_app_static_model.actions),None)
            if action is None:
                logger.error(f"Action with graph node {action_node} not found in the application model.")
                return
            
            form:Form = next((form for form in self.inner_app_static_model.forms \
                if str(form.graph_node) == form_graph_node),None)
            if form is not None:
                # The form has been submitted, so we can move to the next form
                # It should be checked if there exists an instance in the outputGraphStore 
                # corresponding to the current form 
                #
                active_form : ActiveForm = next((af for af in self.app_state.list_of_active_forms \
                    if str(af.graph_node) == str(form_graph_node)), None) 
                if active_form is None:
                    logger.error(f"Active form with graph node {form_graph_node} not found in the application state.")
                if not active_form.has_stored_instances:
                    # If the form has no store instances, we create those instances 
                    # and change the active form state
                    named_individual_iri = BASE[str(uuid4())]
                    logger.debug(f"New instance created for target classes has uri {named_individual_iri}")
                    for target_class in form.target_classes:
                        self.output_graph_store.add((named_individual_iri, RDF.type, target_class))
                    active_form.has_stored_instances = True
                    active_form.stored_instance_graph_node = named_individual_iri
                    logger.debug(f"Active form {form_graph_node} has stored instances now.")
                else:
                    # If the form has already stored instances (named individuals), we use that existing instance
                    named_individual_iri = active_form.stored_instance_graph_node
                    logger.debug(f"Using existing instance {named_individual_iri} for the form {form_graph_node}")

                for key in form_data.keys():
                    # find the element graph node iri for the data element in the array of mappings
                    logger.debug(f"Mapping {self.app_state.current_json_form_name_mapping} is being searched ")
                    element_graph_node_uri = next(( k for k, v in self.app_state.  
                        current_json_form_name_mapping.items() if v == key), None)
                    logger.debug(f"Graph node URI of the element for the key {key} is {element_graph_node_uri}")
                    for data_property in self.inner_app_static_model.rdf_graph_rdflib.objects(
                        URIRef(element_graph_node_uri), OBOP.containsDatatype):
                        logger.debug(f"Data property found for the element {element_graph_node_uri}: {data_property}")
                        # Add the data to the output graph store
                        self.output_graph_store.add((named_individual_iri, data_property, Literal(form_data[key])))
                        logger.debug(f"Added data {form_data[key]} for element {element_graph_node_uri} to the output store.")
                # We have to decide what to do with other form elements that 
                # are not inserted in the form data
                # element = next((el for el in form.elements if str(el.graph_node) == str(element_graph_node_uri)), None) 
 
        elif action_message.action_type == "cancel":

            pass

    def processExecutionNextStep(self):
        """
        Processes the next step in the application execution according to the control flow.
        """
        if self.app_state.current_control_flow_pointer.type == "StartEvent":
            logger.debug("The application is at the start event. Generating the first layout.")
            # The application is at the start event and can be found the process flow that 
            # starts with the start event 
            next_flow: BBOFlow = next(
                (flow for flow in self.inner_app_static_model.bbo_flows
                 if flow.start_event.graph_node == self.app_state.current_control_flow_pointer.graph_node),
                None
            )
            target_reference : BBOEvent | BBOActivity = next_flow.target_event 

            return self.generate_layout()

        if self.app_state.is_waiting_for_form_data:
            # The application is waiting for the form data to be sent back from the frontend
            # We can generate the next layout in the control flow of the application
            self.app_state.is_waiting_for_form_data = False
            return self.generate_layout()
        else:
            logger.debug("The application is not waiting for form data.")
            return None

class ApplicationState:
    def __init__(self):
        self._current_form_index = -1 # The index of the current form
        self._is_waiting_for_form_data = False
        self._running_initiated = False
        self._app_exchange_waiting_to_send_data = False
        self._current_json_form_name_mapping : JSONFormNameMapping = {}
        self.__list_of_active_forms: list[ActiveForm]= []  # List of forms sent to the frontend for editing
        #This list of forms is used to keep track of named individuaals
        # that are created during the previous form exchanges
        # If a form has a named individual here it means that properties are only being
        # changed and shouldn't be created again. 
        self._current_control_flow_pointer : dict = None  # The current control flow pointer is 
        # used to keep track of the current control flow in the application   

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

    @property
    def list_of_active_forms(self):
        return self.__list_of_active_forms

    @list_of_active_forms.setter
    def list_of_active_forms(self, value: list["ActiveForm"]):
        self.__list_of_active_forms = value

    @property
    def current_control_flow_pointer(self):
        return self._current_control_flow_pointer
    @current_control_flow_pointer.setter
    def current_control_flow_pointer(self, value: dict):
        self._current_control_flow_pointer = value  
    
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
    used to identify correct Ontology concepts such as an individual 
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

class ActiveForm:
    """
    This class represents a form that is currently active in the application.
    It is used to keep track of the forms that are being edited by the user.
    """
    def __init__(self, form: Form):
        self.has_stored_instances = False  # Indicates if the form is already has a stored instance in the output graph store
        self.stored_instance_graph_node = None  # The graph node of the stored instance in the output graph store
        self.graph_node = form.graph_node  # The graph node of the form