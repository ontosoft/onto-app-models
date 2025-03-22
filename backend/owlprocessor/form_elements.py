from __future__ import annotations
from typing import TYPE_CHECKING
from json import JSONEncoder
import logging
from rdflib import  Namespace
OBOP = Namespace("http://purl.org/net/obop/")

logger = logging.getLogger("ontoui_app")
if TYPE_CHECKING:
    from .forms import Form
    from .app_interaction_model import ApplicationState

class FormElement:
    def __init__(self,form , model_node, type, position = 0 ):
        self.model_node = model_node
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
        new_property_name : str
        field_type : str = "string"
        # TODO Naming the property as a label for OBOPElements."
        # This should be considered once again. Label could be part 
        # of the basic form element not only OBOPElement
        if str(self.type) == str(OBOP.Field):
            field_type = "string"
        if isinstance(self, OBOPElement) and self.label !="":
            new_property_name = str(self.label)
            app_state.current_json_form_name_mapping[str(self.model_node)] = str(self.label)

        return {
            new_property_name: {
                "type": field_type,
                "position": int(self.position),
        #        "action_pointers": self.action_pointers
            }
        }

    def create_jsonform_ui_schema_element(self, app_state:ApplicationState):
        encoded_name: str = None
        if str(self.model_node) in app_state.current_json_form_name_mapping:        
            encoded_name = app_state.current_json_form_name_mapping[str(self.model_node)] 
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
                    "model_node": o.model_node,
                    "position": o.position,
                    "action_pointers": o.action_pointers
                }
        except Exception as e:
            logger.error(f"Error in FormElementEncoder: {e}")
        return form_element


class FormProperty(FormElement):
    def __init__(
        self,
        form,
        model_node,
        property_path,
        property_order,
        property_name=None,
        property_data_type=None,
        property_description=None,
        property_min_count=None,
        related_element = None
    ):
        super().__init__(form, model_node, property_path, property_order)
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
    def __init__(self, parent_form, model_node, type, position, label = None, action_initiator=None):
        super().__init__(parent_form, model_node, type, position)
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
