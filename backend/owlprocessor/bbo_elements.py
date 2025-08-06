from __future__ import annotations
from rdflib import URIRef
from typing import List


class BBOFlowElementsContainer:
    def __init__(self, graph_node: URIRef):
        self.graph_node : URIRef = graph_node
        self.flow_elements : List[BBOFlowElement] = []

    def add_flow_element(self, flow_element: BBOFlowElement):
        self.flow_elements.append(flow_element)

    def __str__(self):
        return f"BBOFlowElementsContainer: {self.graph_node}"
    

class BBOProcess(BBOFlowElementsContainer):
    def __init__(self, graph_node):
        super().__init__(graph_node)
    def __str__(self):
        return f"BBOProcess: {self.graph_node}"

class BBOSubProcessLoopCharacteristic:
    def __init__(self, graph_node: URIRef):
        self.graph_node : URIRef = graph_node
        self.is_compensation_loop : bool = False

    def __str__(self):
        return f"BBOSubProcessLoopCharacteristic: {self.graph_node}, Type: {self.loop_type}, Compensation: {self.is_compensation_loop}"

class BBOFlowElement:
    def __init__(self, graph_node: URIRef, flow_element_container: BBOFlowElementsContainer):
        self.graph_node : URIRef = graph_node
        self.flow_element_container : BBOFlowElementsContainer = flow_element_container

    def __str__(self):
        return f"BBOFlowElement: {self.graph_node}"
    
    def __repr__(self):
        return f"BBOFlowElement: {self.graph_node}"

class BBOFlowNode(BBOFlowElement):
    def __init__(self, graph_node: URIRef, 
                 flow_elements_conatiner: BBOFlowElementsContainer, node_type: str):
        super().__init__(graph_node, flow_elements_conatiner)
        self.node_type : str = node_type

    def __str__(self):
        return f"BBOFlowNode: {self.graph_node}, Type: {self.node_type}"



class BBOActivity(BBOFlowNode):
    def __init__(self, graph_node, activity_type, activity_description = None):
        super().__init__(graph_node, "activity")


class BBOSubProcess(BBOFlowElementsContainer, BBOActivity):
    def __init__(self, graph_node: URIRef, container: BBOFlowElementsContainer):
        BBOFlowElementsContainer.__init__(graph_node )
        BBOActivity.__init__(self, graph_node, container)
        self.loop_characteristic : BBOSubProcessLoopCharacteristic = None

    def __str__(self):
        return f"BBOSubProcess: {self.graph_node}"



class BBOEvent(BBOFlowNode):
    def __init__(self, graph_node: URIRef, 
                flow_elements_container: BBOFlowElementsContainer,
                event_description = None):
        super().__init__(graph_node, flow_elements_container)
        self.event_description = event_description

    def __str__(self):
        return f"BBOEvent: {self.graph_node}, Type: {self.event_type}, Description: {self.event_description}"

 
class BBOCatchEvent(BBOEvent):
    def __init__(self, graph_node: URIRef,  
                 flow_elements_container : BBOFlowElementsContainer, event_description = None):
        super().__init__(graph_node, flow_elements_container, event_description)


class BBOStartEvent(BBOCatchEvent):
    def __init__(self, graph_node: URIRef, 
                 flow_elements_container : BBOFlowElementsContainer, event_description = None):
        super().__init__(graph_node, flow_elements_container, "start", event_description)

class BBOProcessStartEvent(BBOStartEvent):
    def __init__(self, graph_node: URIRef, process: BBOProcess, event_description = None):
        super().__init__(graph_node, event_description)
        super().has_container = process

    def __str__(self):
        return f"BBOProcessStartEvent: {self.graph_node}, Process: {self.process}"

class BBOThrowEvent(BBOEvent):
    def __init__(self, graph_node: URIRef, event_description = None):
        super().__init__(graph_node, "throw", event_description)

class BBOEndEvent(BBOThrowEvent):
    def __init__(self, graph_node: URIRef, event_description = None):
        super().__init__(graph_node, "end", event_description)


class BBOEvent:
    def __init__(self, graph_node : URIRef,  event_description = None):
        self.graph_node : URIRef = graph_node
        self.bbo_description = event_description


class BBOGateway(BBOFlowNode):
    def __init__(self, graph_node: URIRef):
        super().__init__(graph_node,)

class BBOExclusiveGateway(BBOGateway):
    def __init__(self, graph_node: URIRef):
        super().__init__(graph_node, "exclusive")
        self.has_default_element = None

    def __str__(self):
        return f"BBOGateway: {self.graph_node}, Type: {self.gateway_type}, Description: {self.gateway_description}"

class BBOSequenceFlow(BBOFlowElement):
    """ 
        Represents a sequence flow in a BBO process model. 

    """
    def __init__(self, graph_node : URIRef, source_event: BBOEvent | BBOActivity , target_event: BBOEvent | BBOActivity ):
        self.graph_node : URIRef = graph_node
        self.source_event : BBOEvent | BBOActivity = source_event
        self.target_event : BBOEvent | BBOActivity = target_event


class BBONormalSequenceFlow(BBOSequenceFlow):
    def __init__(self, graph_node: URIRef, source_event: BBOEvent | BBOActivity, target_event: BBOEvent | BBOActivity):
        super().__init__(graph_node, source_event, target_event)

