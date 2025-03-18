from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .app_interaction_model import AppInteractionModel

class AppInternalStaticModel:
    """_summary_
    Internal representation of the model graph which is originally 
    a knowledge graph. The AppInternalModel gives a object as a 
    model representation.
    """
    def __init__(self):
        self.model_graph = None
        self.startingFormBlock = None
        self.form_blocks = []
        self.actions = []
   

    @property
    def firstForm(self):
        return self.startingFormBlock

    @firstForm.setter
    def firstForm(self, forms):
        self.startingFormBlock = forms

    @property
    def forms(self):
        return self.form_blocks

    @forms.setter
    def forms(self, forms):
        self.form_blocks = forms


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