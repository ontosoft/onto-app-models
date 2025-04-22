from __future__ import annotations
from rdflib import Graph
from owlready2 import World

class AppInternalStaticModel:
    """_summary_
    Internal representation of the model graph which is created from the
    knowledge graph. An AppInternalStaticModel instaance is an object as 
    a static representation of the application.
    """
    def __init__(self):
        self.model_graph = None
        self._startingFormBlock = None
        self._rdf_graph_rdflib : Graph = None
        self._rdf_world_owlready: World = None
        self._rdf_pellet_reasoning_world: World = None
        self._layouts = []
        self._form_blocks = []
        self._actions : list[Action]= []
   
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
    def rdf_pellet_reasoning_world(self)-> World:
        return self._rdf_pellet_reasoning_world
    @rdf_pellet_reasoning_world.setter
    def rdf_pellet_reasoning_world(self, value):
        self._rdf_pellet_reasoning_world = value

    @property
    def firstForm(self):
        return self._startingFormBlock

    @firstForm.setter
    def firstForm(self, forms):
        self._startingFormBlock = forms

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
        self._node = node
        self._type = None
        self._isSubmit = False

    def __str__(self):
        return f"Action: {self.node}"

    @property
    def node (self):
        return self._node
    
    @node.setter
    def node(self, value):
        self._node = value

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