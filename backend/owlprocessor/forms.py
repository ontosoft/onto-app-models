from __future__ import annotations
from typing import TYPE_CHECKING
from json import JSONEncoder
import json
import logging
from .form_elements import FormElementEncoder
from typing import TypeAlias

if TYPE_CHECKING:
    from .app_model import AppInternalStaticModel
    from .app_interaction_model import ApplicationState

logger = logging.getLogger("ontoui_app")

JSONForm : TypeAlias = dict[str, dict, dict ]

class Form:

    def __init__(self,inner_app_static_model, node, position=0):
        self._node = node
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
        """_summary_
                  "target_classes": {
                    "type": "array",
                    "title": "Target classes",
                        "items": {
                            "type": "string"
                        },
                        "default": self._target_classes
                    },
        Returns:
            _type_: _description_
        """
        logger.debug(f"Elements are: {self._elements}") 
        if self._elements.__len__() != 0:
            for element in self.elements:
                jform["schema"]["properties"].update(
                    element.create_jsonform_schema_property(app_state))
                jform["uischema"]["elements"].append(
                    element.create_jsonform_ui_schema_element(app_state))
        return jform

class FormEncoder(JSONEncoder):
    def default(self, o):
        form = {}
        try:
            if isinstance(o, Form):
                encoded_elements = []
                if o.elements.__len__() != 0:
                    for element in o.elements:
                        encoded_elements.append(
                            json.dumps(element, cls=FormElementEncoder)
                        )
                else:
                    encoded_elements = []

                encoded_target_classes: str = ""
                if o.target_classes.__len__() != 0:
                    encoded_target_classes = json.dumps(
                        o.target_classes)
                else:
                    encoded_target_classes = ""
                form = {

                    "node": o.node,
                    "target_classes": encoded_target_classes,
                    "elements": encoded_elements,
                }

                logger.debug(f"Target classes are: {o.target_classes}")
                for target_class in o.target_classes:
                    pass
                    # form.update({"target_classes" : json.dump(o.target_classes,default=lambda k: k.__dict__)})

        except Exception as e:
            logger.debug(e)
        else:
            return form

