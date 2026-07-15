from __future__ import annotations
from typing import TYPE_CHECKING, List
from json import JSONEncoder
import logging
from rdflib import  Namespace
from rdflib import URIRef
OBOP = Namespace("http://purl.org/net/obop/")
from rdflib.namespace import SH

logger = logging.getLogger("ontoui_app")
if TYPE_CHECKING:
    from .forms import Form
    from .process_engine import ApplicationState

class FormElement:
    def __init__(self,form , graph_node, type, position:int = 0 ):
        self.graph_node : URIRef = graph_node
        self.type = type
        self.position :int = position
        self.action_pointers : List[ActionPointer] = []
        self.form : Form = form

    def add_action_pointer(self, action_pointer):
        self.action_pointers.append(action_pointer)

    def __str__(self):
        return f"FormElement: {self.type}"

    def __repr__(self):
        return f"FormElement: {self.type}"

    def _instance_picker_options(self, app_state: ApplicationState) -> dict:
        """Options for an instance-picker ListField: label -> instance IRI.

        Resolves the picker's obop:Connection to its OTHER endpoint (the shape
        whose block is not this form), then queries the OUTPUT knowledge graph
        for ALL instances of that endpoint's target classes — the graph is the
        source of truth, so instances count no matter how they were created.
        Labels come from the shape's first datatype property (e.g. menuName),
        falling back to the IRI tail; duplicates are suffixed.
        """
        connection = getattr(self, "picks_instance_for", None)
        output_graph = getattr(app_state, "output_graph_store", None)
        if connection is None or output_graph is None:
            return {}
        rdf = self.form.inner_app_static_model.rdf_graph_rdflib
        source = rdf.value(connection, OBOP.connectionHasSource)
        target = rdf.value(connection, OBOP.connectionHasTarget)
        other_shape = None
        for shape in (source, target):
            if shape is not None:
                block = rdf.value(shape, OBOP.modelBelongsTo)
                if block is not None and str(block) != str(self.form.graph_node):
                    other_shape = shape
                    break
        if other_shape is None:
            return {}
        # The property whose value labels an instance: the shape's first
        # (lowest sh:order) property with a sh:datatype.
        label_paths = sorted(
            (
                (rdf.value(ps, SH.order), rdf.value(ps, SH.path))
                for ps in rdf.objects(other_shape, SH.property)
                if rdf.value(ps, SH.datatype) is not None
                and rdf.value(ps, SH.path) is not None
            ),
            key=lambda t: (t[0] is None, str(t[0])),
        )
        label_path = label_paths[0][1] if label_paths else None

        # All instances of the endpoint's target classes, straight from the
        # output knowledge graph (SPARQL over the data collected so far).
        instances: list = []
        for target_class in rdf.objects(other_shape, SH.targetClass):
            for row in output_graph.query(
                "SELECT DISTINCT ?instance WHERE { ?instance a ?cls }",
                initBindings={"cls": target_class},
            ):
                if row.instance not in instances:
                    instances.append(row.instance)

        options: dict = {}
        for instance in instances:
            label = None
            if label_path is not None:
                value = output_graph.value(instance, label_path)
                if value is not None:
                    label = str(value)
            if not label:
                label = str(instance).split("/")[-1][:8]
            n = 2
            unique = label
            while unique in options:
                unique = f"{label} ({n})"
                n += 1
            options[unique] = str(instance)
        # remember which endpoint the chosen instance fills
        self._picker_shape = str(other_shape)
        return options

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
        if str(self.type) == str(OBOP.ListField) and \
                getattr(self, "picks_instance_for", None) is not None:
            # Instance picker: an enum of the existing instances of the
            # connection's other endpoint. Shown even with a single instance
            # (previews what will be linked); omitted only when there is
            # nothing to pick yet (the engine then auto-links the latest).
            options = self._instance_picker_options(app_state)
            if not options:
                return ""
            name = str(self.label) if self.label else str(self.graph_node).split("/")[-1]
            app_state.current_json_form_name_mapping[str(self.graph_node)] = name
            app_state.current_json_form_picker_mapping[name] = {
                "connection": str(self.picks_instance_for),
                "shape": self._picker_shape,  # the endpoint the choice fills
                "options": options,
            }
            return {
                name: {
                    "type": "string",
                    "enum": list(options.keys()),
                    "position": self.position,
                }
            }
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
                "actions": [
                    {
                        "graph_node": ap.graph_node,
                        "type": ap.type,
                        "initiators": [ initiator for initiator in  ap.action_initiators]
                    }
                    for ap in self.action_pointers
                ],
            }
        elif self.type == OBOP.Field:
            return {
                "type": 'Control',
                "scope": '#/properties/' + encoded_name,
                "label": encoded_name,
            }
        elif self.type == OBOP.ListField and \
                getattr(self, "picks_instance_for", None) is not None:
            # Instance picker: rendered whenever at least one instance exists
            # (a single option still previews what will be linked); with no
            # instances yet there is nothing to show and the layouts filter
            # out the None.
            if not self._instance_picker_options(app_state):
                return None
            return {
                "type": 'Control',
                "scope": '#/properties/' + encoded_name,
                "label": encoded_name,
            }
        elif self.type == OBOP.Label:
            return {
                "type": 'Label',
                "text": self.label,
            }
        return {
            "type": 'Control',
            "scope": '#/properties/' + encoded_name,

        }
 

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
        # For OBOP.ListField instance pickers: the obop:Connection whose other
        # endpoint's instances the user chooses among (obop:picksInstanceFor).
        self.picks_instance_for = None

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
    def __init__(self, graph_node: str, type: str = None, action_initiators=None):
        self.graph_node: str = graph_node
        self.type: str = type  # Type of the action, e.g., "submit", "cancel"
        self.action_initiators: List[str] = action_initiators or []
