from __future__ import annotations
from typing import TYPE_CHECKING
from json import JSONEncoder
import logging
from rdflib import  Namespace
from rdflib import URIRef
OBOP = Namespace("http://purl.org/net/obop/")
from rdflib.namespace import SH

logger = logging.getLogger("ontoui_app")
if TYPE_CHECKING:
    from .forms import Form
    from .app_interaction_model import ApplicationState

class FormElement:
    def __init__(self,form , graph_node, type, position:int = 0 ):
        self.graph_node = graph_node
        self.type = type
        self.position :int = position
        self.action_pointers = []
        self.form:Form = form

    def add_action_pointer(self, action_pointer):
        self.action_pointers.append(action_pointer)

    def __str__(self):
        return f"FormElement: {self.type}"

    def __repr__(self):
        return f"FormElement: {self.type}"

    def create_jsonform_schema_property(self, app_state:ApplicationState):
        new_property_name : str = None
        field_type : str = "string"
        # TODO Naming the property as a label for OBOPElements."
        # This should be considered once again. Label could be part 
        # of the basic form element not only OBOPElement

        # OBOP.Button elements are not part of the JSONschema but are
        # part of the UI schema.
        if self.type in [ OBOP.Button] :
            return ""
        if str(self.type) == str(OBOP.Field):
            field_type = "string" 
        if isinstance(self, OBOPElement) and self.label !="":
            new_property_name = str(self.label)
            app_state.current_json_form_name_mapping[str(self.graph_node)] = str(self.label)
        # then it is a SHACL property
        elif isinstance(self, SHACLFormProperty) and  \
            self.property_data_type !="": 
            # TODO The type checking should be better organized
            # not just string
            field_type = "string" 
            new_property_name = str(self.property_name)
            app_state.current_json_form_name_mapping[str(self.graph_node)] = str(self.property_name)


        return {
            new_property_name: {
                "type": field_type,
                "position": self.position,
        #        "action_pointers": self.action_pointers
            }
        }

    def create_jsonform_ui_schema_element(self, app_state:ApplicationState):
        """
            This method assigns a name to the element in the UI schema."
            It is the name of the mapped property if the element is a SHACL property
            for which ther is a related OBOP element with additional information
            If the element has a label, it is used as the name of the element.
            If the none of the above is true, the name is taken from the graph node
            as the last part of the URI.
        """
        encoded_name: str = None
        if str(self.graph_node) in app_state.current_json_form_name_mapping:        
            encoded_name = app_state.current_json_form_name_mapping[str(self.graph_node)] 
        elif self.label != "":
            encoded_name = str(self.label)
        elif isinstance(self.graph_node, URIRef):
            encoded_name = str(self.graph_node).split("/")[-1]       
        else:
            raise ValueError(f"An element with the graph node {self.graph_node} doesn not hae a label")
        if self.type == OBOP.Button:
            return {
                "type": 'button',
                "scope": '#/properties/' + encoded_name,
                "label": encoded_name,
            }
        elif self.type == OBOP.Field:
            return {
                "type": 'Control',
                "scope": '#/properties/' + encoded_name,
                "label": encoded_name,
            }
        return {
            "type": 'Control',
            "scope": '#/properties/' + encoded_name,

        }
 



class FormElementEncoder(JSONEncoder):
    def default(self, o):
        form_element = {}
        try:
            if isinstance(o, FormElement):
                form_element = {
                    "type": o.type,
                    "graph_node": o.graph_node,
                    "position": o.position,
                    "action_pointers": o.action_pointers
                }
        except Exception as e:
            logger.error(f"Error in FormElementEncoder: {e}")
        return form_element


class SHACLFormProperty(FormElement):
    def __init__(
        self,
        form,
        graph_node,
        property_path,
        property_order,
        property_name=None,
        property_data_type=None,
        property_description=None,
        property_min_count=None,
        related_element = None
    ):
        super().__init__(form, graph_node, property_path, property_order)
        self.property_name = property_name
        self.property_data_type = property_data_type
        self.property_description = property_description
        self.property_min_count = property_min_count
        self.related_element = related_element # The OBOP related element
        # which additionaly describes this schacl property

        def __str__(self):
            return f"FormProperty: {self.property_name}"

        def __repr__(self):
            return f"FormProperty: {self.property_name}"


""" 
    These elements are external to the current SHACL shapes
"""

class OBOPElement(FormElement):
    def __init__(self, parent_form, graph_node, type, position:int, label = None, action_initiator=None):
        super().__init__(parent_form, graph_node, type, position)
        self.label = label
        self._action_pointers = []

    @property
    def action_pointers(self):
        return self._action_pointers

    @action_pointers.setter
    def action_pointers(self, value):
        self._action_pointers = value

    def __str__(self):
        return f"OBOPElement: {self.type}"

    def __repr__(self):
        return f"OBOPElement: {self.type}"


""" 
    This class contains an action pointer that specifies what action to take
    when the corresponding form activiti is initiated
    
    action: Action in the rdf model 
    action_initiator: HTML element action that starts the action.
        For instance, this can be "onclick" for a button element
"""
class ActionPointer:
    def __init__(self, action, action_initiator=None):
        self.action = action
        self.action_initiator = action_initiator
