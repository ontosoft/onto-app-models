class AppInternalModel:
    def __init__(self):
        self.modelGraph = None
        self.startingFormBlock = None
        self.formBlocks = []
        self.actions = []

    @property
    def firstForm(self):
        return self.startingFormBlock

    @firstForm.setter
    def firstForm(self, forms):
        self.startingFormBlock = forms

    @property
    def forms(self):
        return self.formBlocks

    @forms.setter
    def forms(self, forms):
        self.formBlocks = forms


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