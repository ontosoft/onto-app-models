from __future__ import annotations
from rdflib import URIRef
from typing import List


class BBOFlowElementsContainer:
    def __init__(self, graph_node: URIRef):
        self._graph_node : URIRef = graph_node
        self._flow_elements : List[BBOFlowElement] = []

    @property
    def graph_node(self) -> URIRef:
        return self._graph_node 
    @graph_node.setter
    def graph_node(self, value: URIRef):
        self._graph_node = value
    
    @property
    def flow_elements(self) -> List[BBOFlowElement]:
        return self._flow_elements

    @flow_elements.setter
    def flow_elements(self, value: List[BBOFlowElement]):
        self._flow_elements = value

    def add_flow_element(self, flow_element: BBOFlowElement):
        self._flow_elements.append(flow_element)

    def __repr__(self):
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

    def __repr__(self):
        return f"BBOFlowElement: {str(self.graph_node)} in the container {str(self.flow_element_container.graph_node)}"

class BBOFlowNode(BBOFlowElement):
    def __init__(self, graph_node: URIRef, 
                 flow_elements_conatainer: BBOFlowElementsContainer):
        super().__init__(graph_node, flow_elements_conatainer)

    def __repr__(self):
        parent_str = super().__repr__()
        return f"BBOFlowNode: {parent_str}"

class BBOActivity(BBOFlowNode):
    def __init__(self, graph_node,  
                flow_elements_conatainer: BBOFlowElementsContainer
                ):
        super().__init__(graph_node, flow_elements_conatainer)

    def __repr__(self):
        parent_rep = super().__repr__()
        return f"BBOActivity: {parent_rep}"

class BBOTask(BBOActivity):
    def __init__(self, graph_node: URIRef, container: BBOFlowElementsContainer,
                 description: str = None):
        super().__init__(graph_node, container)

    def __repr__(self):
        parent_rep = super().__repr__()
        return f"BBOTask: {parent_rep}"

class BBOScriptTask(BBOTask):
    def __init__(self, graph_node: URIRef, container: BBOFlowElementsContainer,
                 description: str = None):
        super().__init__(graph_node, container)
        self.description = description

    def __repr__(self):
        parent_rep = super().__repr__()
        return f"BBOScriptTask: {parent_rep}, Description: {self.description}"

class BBOUserTask(BBOTask):
    def __init__(self, graph_node: URIRef, container: BBOFlowElementsContainer,
                 description: str = None):
        super().__init__(graph_node, container)
        self.description = description

    def __repr__(self):
        parent_rep = super().__repr__()
        return f"BBOUserTask: {parent_rep}, Description: {self.description}"

class BBOSubProcess(BBOFlowElementsContainer, BBOActivity):
    def __init__(self, graph_node: URIRef, container: BBOFlowElementsContainer):
        BBOFlowElementsContainer.__init__(graph_node )
        BBOActivity.__init__(graph_node, container)
        self.loop_characteristic : BBOSubProcessLoopCharacteristic = None

    def __str__(self):
        return f"BBOSubProcess: {self.graph_node}"



class BBOEvent(BBOFlowNode):
    def __init__(self, graph_node: URIRef, 
                flow_elements_container: BBOFlowElementsContainer,
                event_description = None):
        super().__init__(graph_node, flow_elements_container)

    def __repr__(self):
        parent_rep = super().__repr__()
        return f"BBOEvent: {parent_rep}"

 
class BBOCatchEvent(BBOEvent):
    def __init__(self, graph_node: URIRef,  
                 flow_elements_container : BBOFlowElementsContainer):
        super().__init__(graph_node, flow_elements_container)

    def __repr__(self):
        parent_rep = super().__repr__()
        return f"BBOCatchEvent: {parent_rep}"


class BBOStartEvent(BBOCatchEvent):
    def __init__(self, graph_node: URIRef, 
                 flow_elements_container : BBOFlowElementsContainer):
        super().__init__(graph_node, flow_elements_container)
    
    def __repr__(self):
        parent_rep = super().__repr__()
        return f"BBOStartEvent: {parent_rep}"

class BBOProcessStartEvent(BBOStartEvent):
    def __init__(self, graph_node: URIRef, process: BBOProcess, event_description: str = None):
        super().__init__(graph_node, process)
        self.description = event_description

    def __repr__(self):
        parent_rep = super().__repr__()
        return f"BBOProcessStartEvent: {parent_rep}, Description: {self.description}"

class BBOThrowEvent(BBOEvent):
    def __init__(self, graph_node: URIRef, container: BBOFlowElementsContainer):
        super().__init__(graph_node, container)

    def __repr__(self):
        parent_rep = super().__repr__()
        return f"BBOThrowEvent: {parent_rep}"

class BBOEndEvent(BBOThrowEvent):
    def __init__(self, graph_node: URIRef, container: BBOFlowElementsContainer,
                  event_description = None):
        super().__init__(graph_node, container)
        self.description = event_description

    def __repr__(self):
        parent_rep = super().__repr__()
        return f"BBOEndEvent: {parent_rep}, Description: {self.description}"

class BBOEvent(BBOFlowNode):
    def __init__(self, graph_node : URIRef,  container: BBOFlowElementsContainer):
        super().__init__(graph_node, container)
    
    def __repr__(self):
        parent_rep = super().__repr__()
        return f"BBOEvent: {parent_rep}"

class BBOGateway(BBOFlowNode):
    def __init__(self, graph_node: URIRef, 
                 flow_elements_container: BBOFlowElementsContainer):
        super().__init__(graph_node, flow_elements_container)
    
    def __repr__(self):
        parent_rep = super().__repr__()
        return f"BBOGateway: {parent_rep}" 

class BBOExclusiveGateway(BBOGateway):
    def __init__(self, graph_node: URIRef, 
                 flow_elements_container: BBOFlowElementsContainer,
                 description: str = None):
        super().__init__(graph_node, flow_elements_container)
        self.description: str = None

    def __str__(self):
        parent_rep = super().__repr__()
        return f"BBOExclusiveGateway: {parent_rep}, Description: {self.description}"

class BBOSequenceFlow(BBOFlowElement):
    """ 
        Represents a sequence flow in a BBO process model. 
    """
    def __init__(self, graph_node: URIRef, 
                 container: BBOFlowElementsContainer, 
                 source_ref: BBOFlowElement,
                 target_ref: BBOFlowElement):
        super().__init__(graph_node, container )
        self.source_ref: BBOFlowElement = source_ref
        self.target_ref: BBOFlowElement = target_ref

    def __repr__(self):
        parent_rep = super().__repr__() 
        return f"BBOSequenceFlow: {parent_rep}, Source: {self.source_ref.graph_node}, Target: {self.target_ref.graph_node}"


class BBONormalSequenceFlow(BBOSequenceFlow):
    def __init__(self, graph_node: URIRef, 
                 container: BBOFlowElementsContainer,
                 source_ref: BBOFlowElement ,
                 target_ref: BBOFlowElement ,
                 description: str = None):
        super().__init__(graph_node, container, source_ref, target_ref)
        self.description = description

    def __repr__(self):
        parent_rep = super().__repr__() 
        return f"BBONormalSequenceFlow: {parent_rep}, Description: {self.description}"


class BBOConditionalSequenceFlow(BBOSequenceFlow):
    def __init__(self, graph_node: URIRef, 
                 container: BBOFlowElementsContainer,
                 source_ref: BBOFlowElement ,
                 target_ref: BBOFlowElement ,
                 description: str = None):
        super().__init__(graph_node, container, source_ref, target_ref)
        self.description: None = description

    def __repr__(self):
        parent_rep = super().__repr__() 
        desc = self.description if self.description is not None else ""
        return f"BBOConditionalSequenceFlow: {parent_rep}, Description: {desc}"
