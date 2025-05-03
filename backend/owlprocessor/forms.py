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

FunctionalJSONForm : TypeAlias = dict[str, dict, dict ]

class Form:

    def __init__(self,
                 inner_app_static_model, 
                 graph_node, 
                 position=0):
        self._graph_node : URIRef = graph_node
        self._target_classes = list()
        self._elements = []
        self.model = None
        self._position: int = position
        self._main_layout: Layout = None
        self.shapes = []
        self.inner_app_static_model : AppInternalStaticModel = inner_app_static_model

    @property
    def graph_node(self):
        return self._graph_node

    @graph_node.setter
    def graph_node(self, value):
        self._graph_node = value

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

    @property
    def main_layout(self)-> Layout:
        return self._main_layout
    @main_layout.setter
    def main_layout(self, value: Layout):
        self._main_layout = value

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

    def create_functional_json_form_schemas(self, app_state : ApplicationState) -> FunctionalJSONForm:
        """_summary_

        Args:
            app_state (ApplicationState): _description_

        Returns:
            JSONForm: JSONForm schema for the form consist of main three JSON objects 
            for the JSONForms, namely,  schema, uischema and data. 
            Additionally, it includes elements like actions, iris of the form, ...
            which are not part of the JSONForms schema, but are required for the form to be functional during the interaction with it in the frontend application generator


        Preparing the JSONForms schema starts with the main layout element 
        in the form. There must be only one main layout element in the form.

        uischema is created through the main layout element and their corresponding
        layout elements recursively, 

        schema dictionary is created, on the other hand, through this form and for each element in the form.

        """

        if self._main_layout is None:
            logger.error("The form does not have a main layout element.")
            raise ValueError("The form does not have a main layout element.")
           
        jform : FunctionalJSONForm = {
            "graph_node": str(self._graph_node),
            "schema": {
                "type": "object",
                "properties": {
                }
            },
            "uischema": self._main_layout.create_jsonform_ui_schema        
                (app_state),
            "data": {},
            }
        
        logger.debug(f"Elements are: {self._elements}") 
        if self._elements.__len__() != 0:
            for element in self.elements:
                jform["schema"]["properties"].update(
                    element.create_jsonform_schema_property(app_state))
        return jform

class Layout:
    def __init__(self, 
                 inner_app_static_model, graph_node, position:int=0):
        self._graph_node : URIRef = graph_node
        self._type : str = None
        self._position : int = position
        self._owner_form : Form = None
        self._inner_app_static_model : AppInternalStaticModel = inner_app_static_model
        
    @property
    def graph_node(self):
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
    def __init__(self, inner_app_static_model, graph_node, position:int=0, type="VerticalLayout"):
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

    def create_jsonform_ui_schema(self, app_state:ApplicationState)-> dict:
        """
        Creates a JSONForms uischema for the VerticalLayout.
        """
        jsonform_uischema = {
            "type": "VerticalLayout",
            "elements": []
        }
        for element in self._elements:
            if isinstance(element, FormElement):
                jsonform_uischema["elements"].append(
                    element.create_jsonform_ui_schema_element(app_state))
            elif isinstance(element, Layout):
                # If the element is a layout, we need to recursively call the create_jsonform_ui_schema method 
                jsonform_uischema["elements"].append(
                    element.create_jsonform_ui_schema(app_state))

        return jsonform_uischema

class HorizontalLayout(Layout):
    def __init__(self, inner_app_static_model, graph_node, position:int=0, type="HorizontalLayout"):
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
            if (isinstance(element, FormElement)):
                jsonform_uischema["elements"].append(
                    element.create_jsonform_ui_schema_element(app_state))
            elif isinstance(element, Layout):
                # If the element is a layout, we need to recursively call the
                #  create_jsonform_ui_schema method
                jsonform_uischema["elements"].append(element.create_jsonform_ui_schema(app_state))
        return jsonform_uischema



        

