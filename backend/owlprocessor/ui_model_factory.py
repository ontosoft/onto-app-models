import logging
from pickle import dump
from rdflib import Graph, RDF, Literal, BNode, URIRef, Namespace
from owlprocessor.forms import Form
from owlprocessor.form_elements import OBOPElement, FormProperty, ActionPointer
from owlprocessor.uimodel import Action, UIInternalModel
from rdflib.namespace import  SH, OWL

OBOP = Namespace("http://purl.org/net/obop/")

import uuid
# from InterfaceOntologyTypes import *

class UIModelFactory:
    def __init__(self):
        self.outputDoc = None
        self.outputStore = None
        self.rdfGraph = None
        self.internalModel = None
        self.currentForm = None

    def rdf_graf_to_uimodel(self, rdfGraph):
        self.rdfGraph = rdfGraph
        self.internalModel = UIInternalModel()
        self.readAllForms()
        self.readActions()
        #self.setUpFirstForm()
        self.createOutputStore()
        return self.internalModel

  
    def readAllForms(self):
        self.internalModel.forms = []
        for block in self.rdfGraph.subjects(RDF.type, OBOP.Block):
            logging.info("Block ----")
            logging.info(f"Block: {block}")
            dump(block, open("./uimodels/block.txt", "wb"))
            # Read form position because it represents the order of the form 
            #  in the UI. Iti is also a functional property of the form and can be used to sort the forms.
            # value of the position
            positions = self.rdfGraph.value(block, OBOP.hasPositionNumber)
            form = Form(block,positions)
            self.internalModel.forms.append(form)
            self.readFormElements(form)


    def readFormElements(self, form):
        """
        This method reads a part of the model which corresponds to a given form.
        That part of the model should produce an "implant" of rdf triples  
        with corresponding data properties. That implant is furtner inserted in the output knowledge graph.
        It is implemented using SHACL shapes, DASH and other SHACL extensions.

        The method reads additional form element which are not only represented with SHACL shapes in the
        mode graph but with OBOP elements such as button, label and similar elements, These elements are
        so far related to the form using the obop:belongsTo property. Its different from the SHACL shapes.
        """
        shapes = self.rdfGraph.subjects(OBOP.modelBelongsTo, form.node)
        for s in shapes:
            if (s, RDF.type, SH.NodeShape) in self.rdfGraph:
                shacl_node_shape = s # TODO check if there is only one shape for a form
                # Reading shapes that will be necessary to generate a set of triples 
                # (subgraph of the output graph) when the corresponding form is submitted in the UI
                # The set of triples can be created using the add() method
                form.target_classes.add(self.rdfGraph.objects(shacl_node_shape, SH.targetClass)) 
                for shacl_property_instance in self.rdfGraph.objects(shacl_node_shape, SH.property):
                    if isinstance(shacl_property_instance, BNode):
                        self.readShaclProperty(shacl_property_instance, form)

        # Reading other OBOP elements that are not represented with SHACL shapes 
        other_obop_elements = self.rdfGraph.subjects(OBOP.belongsTo, form.node)
        for element in other_obop_elements:
            self.readOtherOBOPElement(element, form)

        """ 
            This method reads a part of the model which corresponds to a given shacl property.
        """
    def readShaclProperty(self, shacl_property_instance, form):
        property_path = self.rdfGraph.value(shacl_property_instance, SH.path)
        property_name = self.rdfGraph.value(shacl_property_instance, SH.name)
        property_data_type = self.rdfGraph.value(shacl_property_instance, SH.datatype)
        # propertyValues = self.rdfGraph.objects(shacl_property_instance, SH.in)
        property_description = self.rdfGraph.value(shacl_property_instance, SH.description)
        property_min_count = self.rdfGraph.value(shacl_property_instance, SH.minCount) == 1
        form_property = FormProperty(shacl_property_instance, property_path, property_name, property_data_type, 
                                     property_description, property_min_count)
        form.add_element(form_property)


    def readOtherOBOPElement(self, element, form):
        position = self.rdfGraph.value(element, OBOP.hasPositionNumber)
        internal_element : OBOPElement= None
        if isinstance(element, type(OBOP.Button)):
            internal_element = OBOPElement(OBOP.Button, position, element)
        elif isinstance(element, OBOP.Label):
            internal_element = OBOPElement(OBOP.Label, position, element)
        elif isinstance(element, OBOP.Field):
            internal_element = OBOPElement(OBOP.Label, position, element)

        # Reading the action pointers that indicate what actions are related to the element
        action_pointers = self.rdfGraph.objects(element, OBOP.hasActionPointer) 
        for pointer in action_pointers:
           action = self.rdfGraph.value(pointer, OBOP.hasAction) 
           action_initiator = self.rdfGraph.value(pointer, OBOP.hasActionInitiator)
           internal_element.action_pointers.append(ActionPointer(action, action_initiator))
        form.add_element(internal_element)
        # Sorting in the order of the position on the HTML page
        form.elements.sort(key=lambda x: x.position)

    def readActions(self):
        for action_instance in self.rdfGraph.subjects(RDF.type, OBOP.Action):
            action = Action(action_instance)
            action.type = self.rdfGraph.value(action_instance, OBOP.actionType)
            if (self.rdfGraph.value(action_instance, OBOP.isSubmitAction)):
                action.isSubmit = True
            self.internalModel.actions.append(action)
            
                # if isHasConnection(quad[1]):
                #     for quad1 in self.rdfGraph.triples((quad[2], None, None)):
                #         if isRdfType(quad1[1]) and isConnection(quad1[2]):
                #             action.type = CONNECTION_TYPE
                #             source, destination = None, None
                #             for sQuad in self.rdfGraph.triples((quad[2], HAS_SOURCE_NODE, None)):
                #                 source = sQuad[2]
                #             for dQuad in self.rdfGraph.triples((quad[2], HAS_DESTINATION_NODE, None)):
                #                 destination = dQuad[2]
                #             action.activity = {"connection": {"

    def createOutputStore(self):
        self.outputStore = Graph()

