from .forms import Form, FunctionalJSONForm
from rdflib import Graph, Namespace, RDF, URIRef, Literal
from .app_model import AppInternalStaticModel 
from .obop_action import OBOPAction
from .bbo_elements import BBOFlowElementsContainer,  \
    BBOEvent, BBOActivity, BBOProcessStartEvent, BBOFlowElement, \
    BBOSubProcessStartEvent, BBONormalSequenceFlow, BBOConditionalSequenceFlow, \
    BBOEndEvent, BBOScriptTask, BBOSubProcess, BBOUserTask
from .app_state import ApplicationState
from .forms import ActiveForm

from .communication import AppExchangeFrontEndData,  AppExchangeGetOutput
import logging
import jsonpickle
from uuid import uuid4
from pyshacl import validate



OBOP = Namespace("http://purl.org/net/obop/")
BASE = Namespace("http://example.org/logicinterface/testing/instance/")
BBO = Namespace("http://BPMNbasedOntology#")
logger = logging.getLogger('ontoui_app')

class ProcessEngine:
    """
    This class represents the running application. It is reposible for
    generating the next layout in the control flow of the application. 
    """
    def __init__(self, uimodel: AppInternalStaticModel):
        self._internal_app_static_model:AppInternalStaticModel = uimodel
        self._output_graph_store : Graph = Graph()
        self._app_state: ApplicationState = ApplicationState(self.internal_app_static_model)

    @property   
    def internal_app_static_model(self)-> AppInternalStaticModel:
        return self._internal_app_static_model 
    
    @property
    def output_graph_store(self)-> Graph:
        return self._output_graph_store
    @output_graph_store.setter
    def output_graph_store(self, value: Graph):
        self._output_graph_store = value

    @property
    def app_state(self)-> ApplicationState:
        return self._app_state
    @app_state.setter
    def app_state(self, value: ApplicationState):
        self._app_state = value

    def process_received_client_data(self, frontend_state : AppExchangeFrontEndData):
        """
        Processes the data received from the frontend.
        """
        logger.debug(f"Message from the frontend has the type:\n {frontend_state.message_type}")
        logger.debug(f"Message from the frontend has the content:\n {frontend_state.message_content}") 
        if frontend_state.message_type == "initiate_exchange":
            # The frontend has sent the data to start the first data exchange with the application
            # This activates the start event in the applicaation control flow
            # which is the BBOStartEvent in the BBOFlow
            self.move_token()
            return True
        elif frontend_state.message_type == "action":
            self.action_processor(frontend_state.message_content)
                
        # The backend is wating to send data to the frontend in the next 
        # appExchange_get request
        self.move_token()
        return True

    def move_token(self):
        """
        Moves the token in the control flow of the BPM engine and the application.
        The token is moved to the next flow element in the control flow.
        1. If the current flow element is a StartEvent, the token is moved to
           the next flow element in the control flow.
        2. If the current flow element is an EndEvent in the main process, the token is moved to
           the end of the application.
        3. If the current flow element is an EndEvent in a subprocess, the token is moved to
           the next flow element in the super process.
        4. If the current flow element is a ScriptTask, the corresponding action is executed
           and the token is moved within the called function 
           to the next flow element in the control flow 
        5. If the current flow element is a UserTask, the token is
         immediately moved to the next flow element
            
        """
        logger.debug(f"Move_token with the current flow element \
            {self.app_state.current_flow_element.graph_node}")

        if self.app_state.app_finished or self.app_state.is_waiting_for_form_data:
            return
        if self.app_state.current_flow_element is None:
            logger.error("The current flow element is None. The application is not running.")
            self.output_message = AppExchangeGetOutput(
                message_type = "error",
                layout_type = "message_box",
                message_content = {"message" : "The application is not running."}, 
                output_knowledge_graph=self.output_knowledge_graph
                )
            return 
        elif isinstance(self.app_state.current_flow_element, BBOProcessStartEvent) \
            or isinstance(self.app_state.current_flow_element, BBOSubProcessStartEvent):
            logger.debug("The current flow element is the start event.")
            # The application is at the start event and has to be found the flow that
            # starts with the start event  
            self.update_current_flow_element()
            self.move_token()
        elif isinstance(self.app_state.current_flow_element, BBOEndEvent) and \
            self.app_state.current_flow_element_container == self.internal_app_static_model.main_bbo_process:
              # The application execution is finished  
            self.output_message = AppExchangeGetOutput(
            message_type = "notification",
            layout_type = "notification",
            message_content = "The application has finished.")
            self.app_state.app_finished = True
        elif isinstance(self.app_state.current_flow_element, BBOEndEvent) \
            and self.app_state.current_flow_element_container != self.internal_app_static_model.main_bbo_process and isinstance(
                self.app_state.current_flow_element_container, BBOSubProcess):
            # If the token reached the end of the subprocess, it has to
            # move to the next flow element in the super process 
            self.app_state.current_flow_element =self.app_state.current_flow_element_container 
            self.move_token()
        elif isinstance(self.app_state.current_flow_element, BBOScriptTask):
            # If the current flow element is a script task, the correspoinging action 
            # has to be executed and the next step is generated
            self.execute_script_task(self.app_state.current_flow_element)
            self.update_current_flow_element()
            self.move_token()
        elif isinstance(self.app_state.current_flow_element, BBOUserTask):
            if self.app_state.is_waiting_to_send_data:
                logger.debug("Waiting to send data")
            elif self.app_state.is_waiting_for_form_data:
                self.move_token()

    def update_current_flow_element(self):
        next_flow: BBOFlowElement = next(
            (f for f in self.app_state.current_flow_element_container.flow_elements
             if (isinstance(f, BBONormalSequenceFlow) ) and 
                f.source_ref.graph_node == self.app_state.current_flow_element.graph_node),
            None)
        if next_flow is None:  
            logger.error(f"No next flow element has been found for the element {str(self.app_state.current_flow_element.graph_node)}")
            return False
        else:
            logger.debug(f"Next flow found for the current event is {str(next_flow.target_ref.graph_node)}")
            # The token is moved to the next flow element in the control flow
            self.app_state.current_flow_element = next_flow.target_ref
 
    def execute_script_task(self, script_task: BBOScriptTask):
        """
        Executes the script task in the control flow of the application.
        This is used to execute the action that is associated with the script task.
        """
        logger.debug(f"Executing script task {self.app_state.current_flow_element.graph_node}")
        # The script task has to be executed and the next step is generated
        if script_task.obop_action.type == "generate_json_form":
            self.execute_generate_json_form_action(script_task)

        elif script_task.obop_action.type == "submit":
            self.execute_submit_action(script_task)
     

    def execute_generate_json_form_action(self, script_task:BBOScriptTask):
        logger.debug(f"Double-check the script task {str(script_task.graph_node)} and it's actions in the knowledge graph")
        related_obop_action = f"""
            PREFIX obop: <http://purl.org/net/obop/>
            PREFIX bbo: <https://www.irit.fr/recherches/MELODI/ontologies/BBO#>
            SELECT DISTINCT ?action  ?container ?block
            WHERE {{
                <{str(script_task.graph_node)}> bbo:has_container ?container . 
                ?container a ?containerClass .
                ?containerClass rdfs:subClassOf* bbo:FlowElementsContainer .
                <{str(script_task.graph_node)}> obop:executesAction  ?action .
                ?action a obop:GenerateJSONForm .
                ?action obop:actionInBlock ?block .
            }}"""
        try:
            result_generator =  self.internal_app_static_model.rdf_pellet_reasoning_world. \
            sparql(related_obop_action)

            form_object:Form = None

            for row in result_generator:
                (action, container, block ) = row
                logger.debug(f"The OBOP action {action.iri}  for the block {block.iri} is found in the current script task which is in turn incorporated in the container {container.iri},")
                if action.iri == str(script_task.obop_action.graph_node):   
                    form_object = next((c for c in self.internal_app_static_model.forms if str(c.graph_node) == block.iri ),None)
                else:
                    logger.error("The OBOP action doesn't correspond to the BBO task")

            if form_object is not None:
                json_form:FunctionalJSONForm = form_object. \
                create_functional_json_form_schemas(self.app_state) 
                # Speicifying that the form is being sent to the frontend 
                # and the backend is waiting for the form data to be sent back
                active_form = ActiveForm(form_object)
                self.app_state.list_of_active_forms.append(active_form)
                logger.debug(f"New active form created for {active_form.graph_node}")
                # The backend is waiting to send data to the frontend
                # and the JSON Form representation is stored in the current state
                self.app_state.json_form = json_form
                logger.debug("Generated a new JSONForm")
                self.app_state.is_waiting_to_send_data = True

        except Exception as e:
            logger.error(f"Problem with the relation of OBOP actions with BBO tasks: {e}")
            logger.exception("Problem with the relation of OBOP actions with BBO tasks")


    def execute_submit_action(script_task:BBOScriptTask):
        pass

    def generate_layout(self)-> AppExchangeGetOutput:
        """
        Generates the next layout in the control flow of the application
        A layout is, for example, a description of an HTML form block that contains a 
        list of actions that can be performed on the form.
        or it can be just a message box to preview a notification
        """
        
        data = self.output_graph_store.serialize(format="turtle")
        logger.debug(f"Output graph store has the data:\n {data}")
        if isinstance(self.app_state.current_flow_element,BBOUserTask) and \
            self.app_state.is_waiting_to_send_data:
            # The backend is waiting to send data to the frontend

            # return AppExchangeGetOutput(
            #     message_type = "notification",
            #     layout_type = "message_box",
            #     message_content = {"message" : "The application is waiting to send data to the frontend."})
        
            output_message = AppExchangeGetOutput(
                message_type = "layout",
                layout_type = "form",
                message_content = self.app_state.json_form,
                output_knowledge_graph = data)
            logger.debug(f" Created response including the form is {jsonpickle.encode(output_message, indent=2)}")
            self.app_state.is_waiting_to_send_data = False
            self.app_state.is_waiting_for_form_data = True
            return output_message
        else:
            pass
            logger.debug("The application is not waiting to send data to the frontend.")

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
            action : OBOPAction = next(filter(lambda x: x.graph_node == action_node, self.internal_app_static_model.actions),None)
            if action is None:
                logger.error(f"Action with graph node {action_node} not found in the application model.")
                return
            
            form:Form = next((form for form in self.internal_app_static_model.forms \
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
                    for data_property in self.internal_app_static_model.rdf_graph_rdflib.objects(
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
    
    def validateOutputGraphStore(self):
        """
        Validates the output graph store against the application static model.
        This is used to ensure that the data in the output graph store is consistent with the application model.
        """
        result = validate(self.output_graph_store,
                    shacl_graph=self.internal_app_static_model.shacl_graph,
                    ont_graph=self.internal_app_static_model.rdf_graph_rdflib,
                    inference='rdfs',
                    abort_on_first=False,
                    allow_infos=False,
                    allow_warnings=False,
                    meta_shacl=False,
                    advanced=False,
                    js=False,
                    debug=False)
        

