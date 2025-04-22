import logging
import os
import sys
import uuid
from pathlib import Path
from rdflib import Graph, RDF, Literal, BNode, URIRef, Namespace
from .forms import Form, Layout, HorizontalLayout, VerticalLayout
from .form_elements import OBOPElement, SHACLFormProperty, ActionPointer
from .app_model import Action
from rdflib.namespace import SH, OWL
from owlready2 import World
from config.settings import get_settings, Settings
import jsonpickle
from .app_model import AppInternalStaticModel
from utilities.model_directory_functions import create_pellet_reasoning_graph 

OBOP = Namespace("http://purl.org/net/obop/")
logger = logging.getLogger('ontoui_app')

settings:Settings = get_settings()

class AppStaticModelFactory:
        

    @staticmethod
    def rdf_graf_to_uimodel(rdf_model_file: str = None, rdf_text_ttl: str = None ) -> AppInternalStaticModel:
        internal_app_static_model = AppInternalStaticModel()
        internal_app_static_model.rdf_graph_rdflib = \
            AppStaticModelFactory.read_graph_rdflib(rdf_model_file, rdf_text_ttl)
        internal_app_static_model.rdf_world_owlready = \
            AppStaticModelFactory.read_graph_owlready(internal_app_static_model.rdf_graph_rdflib)
        internal_app_static_model.rdf_pellet_reasoning_world = \
            create_pellet_reasoning_graph(
                internal_app_static_model.rdf_world_owlready)           
        AppStaticModelFactory.readAllLayouts(internal_app_static_model)
        AppStaticModelFactory.readAllForms(internal_app_static_model)
        AppStaticModelFactory.readActions(internal_app_static_model)
        # self.setUpFirstForm()
        AppStaticModelFactory.combine_shacl_properties_and_obop_elements(internal_app_static_model)
        AppStaticModelFactory.assignOwnerFormsToLayouts(internal_app_static_model)
        AppStaticModelFactory.assignElementsToLayouts(internal_app_static_model)
        return internal_app_static_model

    @staticmethod
    def read_graph_rdflib( rdf_file_name:str = None, rdf_text_ttl:str = None) -> Graph:
        """
        Reads an RDF file and parses it into the graph objects.
        The project uses both rdflib and owlready2 to read the RDF file. 
        The rdflib library is used to parse the RDF file and create a graph.
        The owlready2 library is used to enable reasoning over the RDF graph. 

                Args:
            rdf_file_name (str): The path to the RDF file.
            rdf_text (str): The RDF in the string form. 
        """
        if (rdf_file_name is None) == (rdf_text_ttl is None):
            raise ValueError("Exactly one of 'rdf_model_file' or 'rdf_text' must be provided.")
        if rdf_file_name is not None:
            # Reading the RDF graph from the file
            logger.debug(f"Reading and parsing the RDF file {rdf_file_name}")
            rdf_graph_rdflib = Graph()
            rdf_graph_rdflib.parse(rdf_file_name, format="ttl")
            return rdf_graph_rdflib
        else:
            # Reading the RDF graph from the string
            logger.debug("Reading and parsing the RDF string in ttl format.")
            # Reading the RDF graph in the string form using rdflib library
            rdf_graph_rdflib = Graph()
            rdf_graph_rdflib.parse(data = rdf_text_ttl, format="ttl")  
            return rdf_graph_rdflib

    @staticmethod
    def read_graph_owlready(rdf_graph_rdflib: Graph) -> World:
        """
        Reads an RDF file and parses it using owlready library.
        The owlready2 library is used in order to enable reasoning over the RDF graph
        using reasoners such as Pellet reasoner. 

        Args:
            rdf_graph_rdflib (path): The RDF file in as rdflib graph object.
        """
        # The following part is a workaround for the owlready2 library limitation.
        # Because the owlready2 library does not support parsing RDF 
        # files in the string form, we need to serialize rdflib RDF graph to 
        # a temporary file and then read it using owlready2.
        temporary_location = Path(settings.TEMPORARY_MODELS_DIRECTORY)
        temporary_location.mkdir(parents=True, exist_ok=True)
        temporary_model_file = uuid.uuid4().hex + ".xml"
        filePath = temporary_location/temporary_model_file
        rdf_graph_rdflib.serialize(destination=filePath, format="xml")
      
        graph_world :World = World()
        model_graph_owlready = graph_world.get_ontology(str(filePath)).load()

        model_graph_with_obop = graph_world. \
            get_ontology(str(Path(settings.ONTOLOGIES_DIRECTORY).joinpath('obop.owl'))).load()
        # After reading the RDF file using owlready2, we need to remove the temporary file.
        os.remove(filePath)

        return graph_world


    def readAllLayouts(internal_app_static_model: AppInternalStaticModel):
        """
        This method reads all layouts from the RDF graph into the internal static application model
        """
        # Read horizontal layouts
        for layout_individual in internal_app_static_model.rdf_graph_rdflib.subjects(RDF.type, OBOP.HorizontalLayout):
            logger.info(f"HorizontalLayout: {str(layout_individual)}")
            layout = HorizontalLayout(internal_app_static_model, layout_individual)
            # Read layout position because it represents the order 
            # of nesting in the UI. It is also a functional property of the layout and is used to sort the layouts.
            positions = internal_app_static_model.rdf_graph_rdflib.value(layout_individual, OBOP.hasPositionNumber)
            layout.position = positions
            internal_app_static_model.add_layout(layout)
        # Read vertical layouts
        for layout_individual in internal_app_static_model.rdf_graph_rdflib.subjects(RDF.type, OBOP.VerticalLayout):
            logging.info(f"VerticalLayout: {str(layout_individual)}")
            layout = VerticalLayout(internal_app_static_model, layout_individual)
            # Read layout position because it represents the order
            # of nesting in the UI. It is also a functional property of the layout and is used to sort the layouts.
            positions = internal_app_static_model.rdf_graph_rdflib.value(layout_individual, OBOP.hasPositionNumber)
            layout.position = positions
            internal_app_static_model.add_layout(layout)

    def readAllForms(internal_app_static_model: AppInternalStaticModel):
        internal_app_static_model.forms = []
        for block in internal_app_static_model.rdf_graph_rdflib.subjects(RDF.type, OBOP.Block):
            logging.info(f"Block: {str(block)}")
            # with open("./app_models/blocks.txt", "a") as f:
            #     f.write(str(block) + "\n")
            # Read form position because it represents the order of the form
            #  in the UI. Iti is also a functional property of the form and can be used to sort the forms.
            # value of the position
            positions = internal_app_static_model.rdf_graph_rdflib.value(block, OBOP.hasPositionNumber)
            form = Form(internal_app_static_model, block, positions)
            internal_app_static_model.forms.append(form)
            AppStaticModelFactory.readFormElements(form, internal_app_static_model.rdf_graph_rdflib)


    def readFormElements(form: Form, rdf_graph_rdflib: Graph):
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
        shapes = rdf_graph_rdflib.subjects(OBOP.modelBelongsTo, form.node)
        for s in shapes:
            if (s, RDF.type, SH.NodeShape) in rdf_graph_rdflib:
                shacl_node_shape = s  # TODO check if there is only one shape for a form
                # Reading shapes that will be necessary to generate a set of triples
                # (subgraph of the output graph) when the corresponding form is submitted in the UI
                # The set of triples can be created using the add() method
                form.target_classes = list(
                    map(
                        lambda item: str(item),
                        rdf_graph_rdflib.objects(shacl_node_shape, SH.targetClass),
                    )
                )
                logger.debug(
                    f"Form target classes: {jsonpickle.encode(form.target_classes)}"
                )
                for shacl_property_instance in rdf_graph_rdflib.objects(
                    shacl_node_shape, SH.property
                ):
                    # Reading SHACL properties that are represented with SHACL shapes
                    # Those SHACL properties that don't have any further
                    # properties are not considered as form elements
                    if (shacl_property_instance, None, None) in rdf_graph_rdflib:
                        AppStaticModelFactory.readShaclProperty(shacl_property_instance, form)

        # Reading other OBOP elements that are not represented with SHACL shapes
        other_obop_elements = rdf_graph_rdflib.subjects(OBOP.belongsTo, form.node)
        for element in other_obop_elements:
            AppStaticModelFactory.readOtherOBOPElement(element, form )


    def readShaclProperty(shacl_property_instance, form: Form):
        """ 
            This method reads a part of the model which corresponds to a given SHACL property.
        """
        rdf_graph_rdflib = form.internal_app_static_model.rdf_graph_rdflib
        logger.debug(f"Reading SHACL property: {shacl_property_instance}") 
        property_path = rdf_graph_rdflib.value(shacl_property_instance, SH.path)
        property_name = rdf_graph_rdflib.value(shacl_property_instance, SH.name)
        property_order = rdf_graph_rdflib.value(shacl_property_instance, SH.order)
        property_data_type = rdf_graph_rdflib.value(shacl_property_instance, SH.datatype)
        # propertyValues = self.rdfGraph.objects(shacl_property_instance, SH.in)
        property_description = rdf_graph_rdflib.value(
            shacl_property_instance, SH.description
        )
        property_min_count = rdf_graph_rdflib.value(shacl_property_instance, SH.minCount) 
        
        # Reading the related element that specifies the property
        # using OPOP ontology
        related_element = str(rdf_graph_rdflib.value(shacl_property_instance, OBOP.specifiedBy))
        logger.debug(f"Related element: {related_element}")

        form_property : SHACLFormProperty = SHACLFormProperty(
            form,
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

    def readOtherOBOPElement(element, form : Form):
        logger.debug(f"Reading OBOP element: {element}")
        rdf_graph_rdflib = form.inner_app_static_model.rdf_graph_rdflib
        position = rdf_graph_rdflib.value(element, OBOP.hasPositionNumber)
        internal_element: OBOPElement = None
        if element in rdf_graph_rdflib.subjects(
                    RDF.type, OBOP.Button):
            internal_element = OBOPElement(form, element, OBOP.Button, position)
        elif element in rdf_graph_rdflib.subjects(
                    RDF.type, OBOP.Label):
            internal_element = OBOPElement(form, element, OBOP.Label, position)
        elif element in rdf_graph_rdflib.subjects(
                    RDF.type, OBOP.Field):
            if element in rdf_graph_rdflib.subjects(
                    OBOP.hasLabel, None):
                label = rdf_graph_rdflib.value(element, OBOP.hasLabel)
                internal_element = OBOPElement(form, element, OBOP.Field, position, label)
            else:
                internal_element = OBOPElement(form, element, OBOP.Field, position)
        elif element in rdf_graph_rdflib.subjects(
                    RDF.type, OBOP.Loop):
            internal_element = OBOPElement(form, element, OBOP.Loop, position)

        # Reading the action pointers that indicate what actions are related to the element
        action_pointers = rdf_graph_rdflib.objects(element, OBOP.hasActionPointer)
        for pointer in action_pointers:
            action = rdf_graph_rdflib.value(pointer, OBOP.hasAction)
            action_initiator = rdf_graph_rdflib.value(pointer, OBOP.hasActionInitiator)
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

    def readActions(internal_app_static_model: AppInternalStaticModel):
        for action_instance in internal_app_static_model.rdf_graph_rdflib.subjects(RDF.type, OBOP.Action):
            action = Action(action_instance)
            action.type = internal_app_static_model.rdf_graph_rdflib.value(action_instance, OBOP.actionType)
            if internal_app_static_model.rdf_graph_rdflib.value(action_instance, OBOP.isSubmitAction):
                action.isSubmit = True
            internal_app_static_model.actions.append(action)

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



    def combine_shacl_properties_and_obop_elements(internal_app_static_model: AppInternalStaticModel):
        """
        This method combines a SHACL property and OBOP element, for
        example an OBOP.field, into a single propery because they
        both describe the same thing in a single form.
        The position and other properties of obop element are  assigned
        to the SHACL property and the obop element is removed from 
        the list of form elements.
        This is applied on all forms in the internal model.
        """
        for form in internal_app_static_model.forms:
            for shacl_property in form.elements:
                if isinstance(shacl_property, SHACLFormProperty) and shacl_property.related_element is not None:
                    for obop_element in form.elements:
                        if isinstance(obop_element, OBOPElement):
                            if str(obop_element.model_node) == shacl_property.related_element:
                                shacl_property.position = obop_element.position
                                shacl_property.action_pointers += obop_element.action_pointers
                                ### TODO Other properties of the OBOP element should be assigned to the SHACL property
                                form.elements.remove(obop_element)
                                break

    def assignOwnerFormsToLayouts(internal_app_static_model: AppInternalStaticModel):
        """
            This method assigns an owner form to a layout if that layout is the main layout of the form.  
            The form is the owner of the layout if it appears as a value of the object property 
            obop:belongsTo  of the layout in the model graph.
        """
        try:
            forms_and_layouts_sparql_query1 = """
            PREFIX obop: <http://purl.org/net/obop/>
            SELECT DISTINCT ?layout ?block
            WHERE {
                ?layout obop:belongsTo ?block .
                ?block a obop:Block .
                ?layout a ?c1 . 
                ?c1 rdfs:subClassOf* obop:Layout .
            }"""

            layout_block_pairs = internal_app_static_model.rdf_pellet_reasoning_world. \
                sparql_query(forms_and_layouts_sparql_query1)
            #logger.debug(f"Query Results: {list(layout_block_pairs)}")

            # Denote the form owners to those layouts that are main layouts of the form
            for row in layout_block_pairs:
                (graph_layout, graph_block) = row
                logger.debug(f"Row is: {internal_app_static_model.rdf_pellet_reasoning_world.base_iri(str(graph_layout))} - {str(graph_block)} ")
                layout = next((layout for layout in internal_app_static_model.layouts \
                              if layout.node == graph_layout),None)
                form = next((f for f in internal_app_static_model.forms \
                             if f.node == graph_block),None)
                if layout is not None and form is not None:
                    layout.owner_form = form

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                
            logger.error(f"Error in assigning owner form to layout: {e}{exc_type, fname, exc_tb.tb_lineno}")


    def assignLayoutToFormElements(internal_app_static_model : AppInternalStaticModel):
        """
            This method assigns parent layouts to form elements
        """
        try:
            for form in internal_app_static_model.forms:
                for form_element in form.elements:
                    parent_layouts = internal_app_static_model.rdf_graph_rdflib.objects(form_element.node, OBOP.belongsToVisual)
                    if parent_layouts.__len__() > 1:
                        raise Exception("More than one parent layout found. Parent layout  " +
                        "is functional predicate and should be unique.")
                    else:
                        parent_layout = internal_app_static_model.layouts.find(
                            lambda x: x.node == parent_layouts[0]
                        )
                        # Assigning the layout to the form element
                        parent_layout.elements.append(form_element)

            # Sorting in the order of the position on the HTML page
            for layout in internal_app_static_model.layouts:
                layout.elements.sort(key=lambda x: x.position)

        except Exception as e:
            logger.error(f"Error in assigning layout to form elements: {e}")    
            logger.error(f"Some form elements: {form.elements} probably do \
                         not have the layout attribute set.")

    def assignElementsToLayouts(internal_app_static_model: AppInternalStaticModel):
        """
            This method assigns form elements to layouts
        """
        for form in internal_app_static_model.forms:
            for element in form.elements:
                for visual_container in internal_app_static_model.rdf_graph_rdflib.objects(element.model_node,OBOP.belongsToVisual):
                    # TODO: check if this comparison includes the reasoning (for example
                    #  if the visual container is a subclass of the layout)
                    if internal_app_static_model.rdf_graph_rdflib.value(visual_container, RDF.type) == OBOP.Layout:
                        layout = internal_app_static_model.layouts.find(
                            lambda x: x.node == visual_container
                        ) 
                        # Assigning the layout to the form element
                        layout.elements.append(element)
                    # Assigning the form to the layout
        # Sorting in the order of the position on the HTML page
        try:
            for layout in internal_app_static_model.layouts:
                layout.elements.sort(key=lambda x: x.position)
        except Exception as e:
            logger.error(f"Error in sorting the form elements: {e}")    
            logger.error(f"Some form elements: {layout.elements} probably do \
             not have the position attribute set.")

