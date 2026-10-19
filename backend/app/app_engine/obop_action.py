from rdflib import URIRef


class Connection:
    """A to-be-created object-property link between two form instances.

    Read from an ``obop:Connection`` individual: ``connectionHasSource`` /
    ``connectionHasTarget`` point at the NodeShapes of the two forms, and each
    ``obop:hasConnector`` names one object property via its ``shacl:path``. At
    runtime the engine resolves each shape to the instance its form created and
    emits ``(source_instance, object_property, target_instance)`` per property.
    """

    def __init__(
        self,
        graph_node: URIRef,
        source_shape: URIRef,
        target_shape: URIRef,
        object_properties: list[URIRef],
    ):
        self.graph_node = graph_node  # the obop:Connection individual's IRI
        self.source_shape = source_shape
        self.target_shape = target_shape
        self.object_properties = object_properties

    def __repr__(self):
        return (
            f"Connection({self.graph_node}: source={self.source_shape}, "
            f"target={self.target_shape}, "
            f"properties={[str(p) for p in self.object_properties]})"
        )


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


class MakeConnectionAction(OBOPAction):
    """An ``obop:MakeConnectionAction`` — links instances entered in different
    forms via object properties. Carries the ``obop:Connection``(s) to establish
    when its script task executes (see ProcessEngine.execute_make_connection_action).
    """

    def __init__(self, node: URIRef):
        super().__init__(node)
        self._type = "make_connection"
        self.connections: list["Connection"] = []

