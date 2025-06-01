from rdflib import URIRef



class BBOProcess:
    def __init__(self, graph_node):
        self.graph_node :URIRef = graph_node


class BBOActivity:
    def __init__(self, graph_node, activity_type, activity_description = None):
        self.graph_node : URIRef = graph_node
        self.bbo_type : str = activity_type
        self.bbo_description = activity_description


class BBOEvent:
    def __init__(self, graph_node : URIRef,  event_description = None):
        self.graph_node : URIRef = graph_node
        self.bbo_description = event_description

class BBOFlow:
    def __init__(self, graph_node : URIRef, source_event: BBOEvent | BBOActivity , target_event: BBOEvent | BBOActivity ):
        self.graph_node : URIRef = graph_node
        self.source_event : BBOEvent | BBOActivity = source_event
        self.target_event : BBOEvent | BBOActivity = target_event