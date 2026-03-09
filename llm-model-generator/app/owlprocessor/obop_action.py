from rdflib import URIRef

class OBOPAction:
    def __init__(self, node: URIRef):
        self._graph_node : URIRef = node
        self._type: str = None
        self._isSubmit = False

    def __repr__(self):
        return f"Action with iri {str(self.graph_node)} and type {self.type}"

    @property
    def graph_node (self)-> URIRef:
        return self._graph_node
    
    @graph_node.setter
    def graph_node(self, value : URIRef):
        self._graph_node = value

    @property
    def type(self)-> str:
        return self._type

    @type.setter
    def type(self, value: str):
        self._type : str = value

    @property
    def isSubmit(self):
        return self._isSubmit

    @isSubmit.setter
    def isSubmit(self, value):
        self._isSubmit = value

