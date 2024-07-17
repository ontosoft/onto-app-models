from json import JSONEncoder
import json

class Form:
    def __init__(self, node, position = 0):
        self._node = node
        self._target_classes = set()
        self._elements = []
        self.model = None
        self._position: int = position
        self.shapes = []

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


class FormEncoder(JSONEncoder):
    def default(self, o):
        form = {}
        try :
            if isinstance(o, Form):
                form = { "node": o.node,
                    "target_classes": o.target_classes,
                    "elements": o.elements
                }
                for  element in o.elements:
                    form.update({"elements" : element.__dict__})
                for target_class in o.target_classes:
                    form.update({"target_classes" : 
                                json.dump(target_class,default=lambda o: o.__dict__)})
        except Exception as e:
            print(e)
        else:
            return form
