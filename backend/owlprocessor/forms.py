from __future__ import annotations
from rdflib import URIRef 
from typing import TYPE_CHECKING
import logging
from .form_elements import FormElement
from typing import TypeAlias

if TYPE_CHECKING:
    from .app_model import AppInternalStaticModel
    from .app_interaction_model import ApplicationState

logger = logging.getLogger("ontoui_app")

JSONForm : TypeAlias = dict[str, dict, dict ]

class Form:

    def __init__(self,
                 inner_app_static_model, 
                 node, 
                 position=0):
        self._node : URIRef = node
        self._target_classes = list()
        self._elements = []
        self.model = None
        self._position: int = position
        self.shapes = []
        self.inner_app_static_model : AppInternalStaticModel = inner_app_static_model

    @property
    def node(self):
        return self._node

    @node.setter
    def node(self, value):
        self._node = value

    @property
    def target_classes(self):
        return self._target_classes

    @target_classes.setter
    def target_classes(self, value):
        self._target_classes = value

    @property
    def position(self):
        return self.position

    @position.setter
    def position(self, value):
        self._position = value

    @position.setter
    def position(self, value):
        self._position = value

    @property
    def elements(self):
        return self._elements

    @elements.setter
    def elements(self, value):
        self._elements = value

    def add_element(self, element):
        self._elements.append(element)

    def add_target_class(self, target_class):
        self._target_classes.add(target_class)

    @property
    def inner_app_static_model(self):
        return self._inner_app_static_model
    @inner_app_static_model.setter
    def inner_app_static_model(self, value):
        self._inner_app_static_model = value

    def create_json_form_schemas(self, app_state : ApplicationState) -> JSONForm:
        jform : JSONForm = {
            "node": str(self._node),
            "schema": {
                "type": "object",
                "properties": {
                }
            },
            "uischema": {
                "type": 'VerticalLayout',
                "elements": [
                    
                ]
            }
        }
        
        logger.debug(f"Elements are: {self._elements}") 
        if self._elements.__len__() != 0:
            for element in self.elements:
                jform["schema"]["properties"].update(
                    element.create_jsonform_schema_property(app_state))
                jform["uischema"]["elements"].append(
                    element.create_jsonform_ui_schema_element(app_state))
        return jform

class Layout:
    def __init__(self, 
                 inner_app_static_model, graph_node, position=0):
        self._graph_node : URIRef = graph_node
        self._type : str = None
        self._position : int = position
        self._owner_form : Form = None
        self._inner_app_static_model : AppInternalStaticModel = inner_app_static_model
        
    @property
    def node(self):
        return self._graph_node
    @node.setter
    def node(self, value):
        self._graph_node = value
    @property
    def type(self):
        return self._type
    @type.setter
    def type(self, value):
        self._type = value
    @property
    def position(self):
        return self._position
    @position.setter
    def position(self, value):
        self._position = value
    @property
    def owner_form(self):
        return self._owner_form
    @owner_form.setter
    def owner_form(self, value: Form):
        self._owner_form = value


class VerticalLayout(Layout):
    def __init__(self, inner_app_static_model, graph_node, position=0, type="VerticalLayout"):
        """"
        VerticalLayout is a subclass of Layout that represents a layout that caan correspond to the JSONForms uischema VerticalLayout.
        In the list of elements, it can contain other visual elements such as layouts or form elements.

        """
        super().__init__(inner_app_static_model, graph_node, position)
        self._type = "VerticalLayout"
        self._elements : list[Layout | FormElement] = []

    @property
    def elements(self):
        return self._elements
    @elements.setter
    def elements(self, value):
        self._elements = value
    def add_element(self, element):
        self._elements.append(element)

    def create_jsonform_ui_schema(self, app_state:ApplicationState):
        """
        Creates a JSONForms uischema for the VerticalLayout.
        """
        jsonform_uischema = {
            "type": "VerticalLayout",
            "elements": []
        }
        for element in self._elements:
            jsonform_uischema["elements"].append(element.create_jsonform_ui_schema_element(app_state))
        return jsonform_uischema

class HorizontalLayout(Layout):
    def __init__(self, inner_app_static_model, graph_node, position=0, type="HorizontalLayout"):
        """
        HorizontalLayout is a subclass of Layout that represents a layout that corresponds to the JSONForms uischema HorizontalLayout.
        In the list of elements, it can contain other visual elements such as layouts or form elements.
        """
        super().__init__(inner_app_static_model, graph_node, position)
        self._type = "HorizontalLayout"
        self._elements : list[Layout | FormElement] = []
    @property
    def elements(self):
        return self._elements
    @elements.setter
    def elements(self, value):
        self._elements = value
    def add_element(self, element):
        self._elements.append(element)
    def create_jsonform_ui_schema(self, app_state:ApplicationState):
        """
        Creates a JSONForms uischema for the HorizontalLayout.
        """
        jsonform_uischema = {
            "type": "HorizontalLayout",
            "elements": []
        }
        for element in self._elements:
            jsonform_uischema["elements"].append(element.create_jsonform_ui_schema_element(app_state))
        return jsonform_uischema



        

