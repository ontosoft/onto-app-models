class FormElement:
    def __init__(self, type, position = 0):
        self.type = type
        self.position :int = position
        self.action_pointers = []

    def add_action_pointer(self, action_pointer):
        self.action_pointers.append(action_pointer)

    def __str__(self):
        return f"FormElement: {self.type}"

    def __repr__(self):
        return f"FormElement: {self.type}"


class FormProperty(FormElement):
    def __init__(
        self,
        type,
        position,
        shape_instance=None,
        path=None,
        value=None,
        property_path=None,
        property_name=None,
        property_data_type=None,
        property_description=None,
        property_min_count=None,
    ):
        super().__init__(type, position)
        self.shape_instance = shape_instance
        self.name = path
        self.value = value
        self.property_path = property_path
        self.property_name = property_name
        self.property_data_type = property_data_type
        self.property_description = property_description
        self.property_min_count = property_min_count

        def __str__(self):
            return f"FormProperty: {self.property_name}"

        def __repr__(self):
            return f"FormProperty: {self.property_name}"


""" 
    These elements are external to the current SHACL shapes
"""

class OBOPElement(FormElement):
    def __init__(self, type, position, node, action_initiator=None):
        super().__init__(type, position)
        self.node = node
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
