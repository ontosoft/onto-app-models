from __future__ import annotations
from rdflib import Graph
from owlready2 import World, Ontology
from .bbo_elements import BBOProcess, BBOActivity, BBOEvent, BBOSubProcess,BBOFlowElementsContainer, BBOFlowNode

class AppInternalStaticModel:
    """_summary_
    Internal representation of the model graph which is created from the
    knowledge graph. An AppInternalStaticModel instaance is an object as 
    a static representation of the application.
    """
    def __init__(self):
        self._model_file_name : str = None
        self.is_loaded : bool = False
        self._rdf_graph_rdflib : Graph = None
        self._rdf_world_owlready: World = None
        self._rdf_ontology_owlready: Ontology = None
        self._rdf_pellet_reasoning_world: World = None
        self._bbo_flow_elements_containers : list[BBOFlowElementsContainer] = []
        self._bbo_flows : list[BBOFlowNode] = []
        self._main_bbo_process : BBOProcess = None
        self._bbo_subprocesses : list[BBOSubProcess] = []
        self._bbo_activities :list[BBOActivity] = []
        self._bbo_events : list[BBOEvent] = []
        self._layouts = []
        self._form_blocks = []
        self._actions : list[Action]= []
        self._model_file_name : str = None
        self._is_loaded: bool = False
   
    @property
    def model_graph(self):
        return self._model_graph
    @model_graph.setter
    def model_graph(self, value):
        self._model_graph = value
    @property
    def rdf_graph_rdflib(self)-> Graph:
        return self._rdf_graph_rdflib
    @rdf_graph_rdflib.setter
    def rdf_graph_rdflib(self, value):
        self._rdf_graph_rdflib = value
    @property
    def rdf_world_owlready(self)-> World:
        return self._rdf_world_owlready
    @rdf_world_owlready.setter
    def rdf_world_owlready(self, value):
        self._rdf_world_owlready = value

    @property
    def rdf_ontology_owlready(self)-> Ontology:
        return self._rdf_ontology_owlready
    @rdf_ontology_owlready.setter
    def rdf_ontology_owlready(self, value):
        self._rdf_ontology_owlready = value
    
    @property
    def rdf_pellet_reasoning_world(self)-> World:
        return self._rdf_pellet_reasoning_world
    @rdf_pellet_reasoning_world.setter
    def rdf_pellet_reasoning_world(self, value):
        self._rdf_pellet_reasoning_world = value

    @property
    def main_bbo_process(self):
        return self._main_bbo_process
    @main_bbo_process.setter
    def main_bbo_process(self, value):
        self._main_bbo_process = value

    @property
    def bbo_subprocesses(self)-> list[BBOSubProcess]:
        return self._bbo_subprocesses
    @bbo_subprocesses.setter
    def bbo_subprocesses(self, value: list[BBOSubProcess]):
        self._bbo_subprocesses = value

    @property
    def bbo_activities(self):
        return self._bbo_activities
    @bbo_activities.setter
    def bbo_activities(self, value):
        self._bbo_activities = value

    @property
    def bbo_events(self):
        return self._bbo_events
    @bbo_events.setter
    def bbo_events(self, value):
        self._bbo_events = value
    @property
    def bbo_flows(self):
        return self._bbo_flows
    @bbo_flows.setter
    def bbo_flows(self, value):
        self._bbo_flows = value
    @property
    def model_file_name(self):
        return self._model_file_name
    @model_file_name.setter
    def model_file_name(self, value):
        self._model_file_name = value
    @property
    def is_loaded(self):
        return self._is_loaded
    @is_loaded.setter
    def is_loaded(self, value):
        self._is_loaded = value
    @property
    def forms(self):
        return self._form_blocks

    @forms.setter
    def forms(self, forms):
        self._form_blocks = forms

    @property
    def layouts(self):
        return self._layouts
    @layouts.setter
    def layouts(self, layouts):
        self._layouts = layouts
    def add_layout(self, layout):
        """
        Add a layout to the list of layouts in the model.
        """
        self._layouts.append(layout)

    @property
    def actions(self):
        return self._actions
    @actions.setter
    def actions(self, actions):
        self._actions = actions
    def add_action(self, action):
        """
        Add an action to the list of actions in the model.
        """
        self._actions.append(action)
    


class Action:
    def __init__(self, node):
        self._graph_node = node
        self._type = None
        self._isSubmit = False

    def __str__(self):
        return f"Action: {self.node}"

    @property
    def graph_node (self):
        return self._graph_node
    
    @graph_node.setter
    def graph_node(self, value):
        self._graph_node = value

    @property
    def type(self):
        return self._type

    @type.setter
    def type(self, value):
        self._type = value

    @property
    def isSubmit(self):
        return self._isSubmit

    @isSubmit.setter
    def isSubmit(self, value):
        self._isSubmit = value

    def execute(self, form_data):
        """
        Execute the action with the given form data.
        """
        if self.isSubmit:
            # Process the form data
            print(f"Executing action {self.graph_node} with form data: {form_data}")
        else:
            # Handle other action types
            print(f"Executing action {self.graph_node} without form data.")