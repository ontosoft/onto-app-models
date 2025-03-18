import logging
from rdflib import Graph, RDF, Literal, BNode, URIRef, Namespace
from .forms import Form
from .form_elements import OBOPElement, FormProperty, ActionPointer
from .app_model import Action
from rdflib.namespace import SH, OWL
import jsonpickle
from .app_model import AppInternalStaticModel

OBOP = Namespace("http://purl.org/net/obop/")
logger = logging.getLogger("ui")



class UIModelFactory:
    def __init__(self):
        self.outputDoc = None
        self.outputStore = None
        self.rdfGraph = None
        self.internal_app_static_model : AppInternalStaticModel = None
        self.currentForm = None

    def rdf_graf_to_uimodel(self, rdfGraph) -> AppInternalStaticModel:
        self.rdfGraph = rdfGraph
        self.internal_app_static_model = AppInternalStaticModel()
        self.readAllForms()
        self.readActions()
        # self.setUpFirstForm()
        self.createOutputStore()
        self.combine_shacl_properties_and_obop_elements()
        return self.internal_app_static_model

    def readAllForms(self):
        self.internal_app_static_model.forms = []
        for block in self.rdfGraph.subjects(RDF.type, OBOP.Block):
            logging.info(f"Block: {str(block)}")
            # with open("./app_models/blocks.txt", "a") as f:
            #     f.write(str(block) + "\n")
            # Read form position because it represents the order of the form
            #  in the UI. Iti is also a functional property of the form and can be used to sort the forms.
            # value of the position
            positions = self.rdfGraph.value(block, OBOP.hasPositionNumber)
            form = Form(self.internal_app_static_model, block, positions)
            self.internal_app_static_model.forms.append(form)
            self.readFormElements(form)

    def readFormElements(self, form):
        """
        This method reads a part of the model which corresponds to a given form.
        That part of the model should produce an "implant" of rdf triples
        with corresponding data properties. That implant is further inserted in the output knowledge graph
        in the form submission during the app execution.
        It is implemented using SHACL shapes, DASH and other SHACL extensions.

        The method reads additional form element which are not only represented with SHACL shapes in the
        mode graph but with OBOP elements such as button, label and similar elements, These elements are
        so far related to the form using the obop:belongsTo property. Its different from the SHACL shapes.
        """
        shapes = self.rdfGraph.subjects(OBOP.modelBelongsTo, form.node)
        for s in shapes:
            if (s, RDF.type, SH.NodeShape) in self.rdfGraph:
                shacl_node_shape = s  # TODO check if there is only one shape for a form
                # Reading shapes that will be necessary to generate a set of triples
                # (subgraph of the output graph) when the corresponding form is submitted in the UI
                # The set of triples can be created using the add() method
                form.target_classes = list(
                    map(
                        lambda item: str(item),
                        self.rdfGraph.objects(shacl_node_shape, SH.targetClass),
                    )
                )
                logger.debug(
                    f"Form target classes: {jsonpickle.encode(form.target_classes)}"
                )
                for shacl_property_instance in self.rdfGraph.objects(
                    shacl_node_shape, SH.property
                ):
                    # Reading SHACL properties that are represented with SHACL shapes
                    # Those SHACL properties that don't have any further
                    # properties are not considered as form elements
                    if (shacl_property_instance, None, None) in self.rdfGraph:
                        self.readShaclProperty(shacl_property_instance, form)

        # Reading other OBOP elements that are not represented with SHACL shapes
        other_obop_elements = self.rdfGraph.subjects(OBOP.belongsTo, form.node)
        for element in other_obop_elements:
            self.readOtherOBOPElement(element, form)

        """ 
            This method reads a part of the model which corresponds to a given SHACL property.
        """

    def readShaclProperty(self, shacl_property_instance, form):
        logger.debug(f"Reading SHACL property: {shacl_property_instance}") 
        property_path = self.rdfGraph.value(shacl_property_instance, SH.path)
        property_name = self.rdfGraph.value(shacl_property_instance, SH.name)
        property_order = self.rdfGraph.value(shacl_property_instance, SH.order)
        property_data_type = self.rdfGraph.value(shacl_property_instance, SH.datatype)
        # propertyValues = self.rdfGraph.objects(shacl_property_instance, SH.in)
        property_description = self.rdfGraph.value(
            shacl_property_instance, SH.description
        )
        property_min_count = self.rdfGraph.value(shacl_property_instance, SH.minCount) 
        
        # Reading the related element that specifies the property
        # using OPOP ontology
        related_element = str(self.rdfGraph.value(shacl_property_instance, OBOP.specifiedBy))
        logger.debug(f"Related element: {related_element}")

        form_property = FormProperty(
            self.internal_app_static_model,
            shacl_property_instance,
            property_path,
            property_order,
            property_name, #TODO: property_name is wrongly on the place of position 
            property_data_type,
            property_description,
            property_min_count,
            related_element
        )
        form.add_element(form_property)

    def readOtherOBOPElement(self, element, form):
        logger.debug(f"Reading OBOP element: {element}")
        position = self.rdfGraph.value(element, OBOP.hasPositionNumber)
        internal_element: OBOPElement = None
        if element in self.rdfGraph.subjects(
                    RDF.type, OBOP.Button):
            internal_element = OBOPElement(form, element, OBOP.Button, position)
        elif element in self.rdfGraph.subjects(
                    RDF.type, OBOP.Label):
            internal_element = OBOPElement(form, element, OBOP.Label, position)
        elif element in self.rdfGraph.subjects(
                    RDF.type, OBOP.Field):
            if element in self.rdfGraph.subjects(
                    OBOP.hasLabel, None):
                label = self.rdfGraph.value(element, OBOP.hasLabel)
                internal_element = OBOPElement(form, element, OBOP.Field, position, label)
            else:
                internal_element = OBOPElement(form, element, OBOP.Field, position)
        elif element in self.rdfGraph.subjects(
                    RDF.type, OBOP.Loop):
            internal_element = OBOPElement(form, element, OBOP.Loop, position)

        # Reading the action pointers that indicate what actions are related to the element
        action_pointers = self.rdfGraph.objects(element, OBOP.hasActionPointer)
        for pointer in action_pointers:
            action = self.rdfGraph.value(pointer, OBOP.hasAction)
            action_initiator = self.rdfGraph.value(pointer, OBOP.hasActionInitiator)
            internal_element.action_pointers.append(
                ActionPointer(action, action_initiator)
            )
        if internal_element is not None:
            form.add_element(internal_element)
        # Sorting in the order of the position on the HTML page
        try:
            form.elements.sort(key=lambda x: x.position)
        except Exception as e:
                #TODO it might be better to assigne some default value to the 
                # position attribute of the form elements
                logger.error(f"Error in sorting the form elements: {e}")    
                logger.error(f"Some form elements: {form.elements} probably do \
                             not have the position attribute set.")

    def readActions(self):
        for action_instance in self.rdfGraph.subjects(RDF.type, OBOP.Action):
            action = Action(action_instance)
            action.type = self.rdfGraph.value(action_instance, OBOP.actionType)
            if self.rdfGraph.value(action_instance, OBOP.isSubmitAction):
                action.isSubmit = True
            self.internal_app_static_model.actions.append(action)

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

    def combine_shacl_properties_and_obop_elements(self):
        """
        This method combines a SHACL property and OBOP element, for
        example an OBOP.field, into a single propery because they
        both describe the same thing in a single form.
        The position and other properties of obop element are  assigned
        to the SHACL property and the obop element is removed from 
        the list of form elements.
        This is applied on all forms in the internal model.
        """
        for form in self.internal_app_static_model.forms:
            for shacl_property in form.elements:
                if isinstance(shacl_property, FormProperty) and shacl_property.related_element is not None:
                    for obop_element in form.elements:
                        if isinstance(obop_element, OBOPElement):
                            if str(obop_element.model_node) == shacl_property.related_element:
                                shacl_property.position = obop_element.position
                                shacl_property.action_pointers += obop_element.action_pointers
                                ### TODO Other properties of the OBOP element should be assigned to the SHACL property
                                form.elements.remove(obop_element)
                                break

