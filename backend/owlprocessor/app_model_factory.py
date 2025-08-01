import logging
import os
import sys
import uuid
from pathlib import Path
from rdflib import Graph, RDF, Namespace, URIRef
from .forms import Form, HorizontalLayout, VerticalLayout
from .form_elements import OBOPElement, SHACLFormProperty, ActionPointer
from .bbo_elements import BBOActivity, BBOEvent, BBOFlow
from rdflib import RDFS
from .app_model import Action
from rdflib.namespace import SH, OWL
from owlready2 import World, Ontology
from config.settings import get_settings, Settings
import jsonpickle
from .app_model import AppInternalStaticModel
from utilities.model_directory_functions import create_pellet_reasoning_graph 

OBOP = Namespace("http://purl.org/net/obop/")
BBO = Namespace("https://www.irit.fr/recherches/MELODI/ontologies/BBO#")
logger = logging.getLogger('ontoui_app')

settings:Settings = get_settings()

class AppStaticModelFactory:
        

    @staticmethod
    def rdf_graf_to_uimodel(rdf_model_file: Path = None, rdf_text_ttl: str = None ) -> AppInternalStaticModel:
        internal_app_static_model = AppInternalStaticModel()
        internal_app_static_model.rdf_graph_rdflib = \
            AppStaticModelFactory.read_graph_rdflib(rdf_model_file, rdf_text_ttl)
        internal_app_static_model.rdf_world_owlready, internal_app_static_model.rdf_ontology_owlready = \
            AppStaticModelFactory.read_graph_owlready(internal_app_static_model.rdf_graph_rdflib)
        internal_app_static_model.rdf_pellet_reasoning_world = \
            create_pellet_reasoning_graph(
                internal_app_static_model.rdf_world_owlready)           
        AppStaticModelFactory.readBBOElements(internal_app_static_model)
        AppStaticModelFactory.readAllLayouts(internal_app_static_model)
        AppStaticModelFactory.readAllForms(internal_app_static_model)
        AppStaticModelFactory.readActions(internal_app_static_model)
        AppStaticModelFactory.combine_shacl_properties_and_obop_elements(internal_app_static_model)
        AppStaticModelFactory.assignOwnerFormsToLayouts(internal_app_static_model)
        AppStaticModelFactory.assignElementsAndLayoutsToLayouts(internal_app_static_model)
        AppStaticModelFactory.assignAdditionalParameters(internal_app_static_model, rdf_model_file, rdf_text_ttl)
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
    def read_graph_owlready(rdf_graph_rdflib: Graph) -> tuple[World, Ontology]:
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
        temporary_location : Path = settings.TEMPORARY_MODELS_DIRECTORY
        temporary_location.mkdir(parents=True, exist_ok=True)
        temporary_model_file = uuid.uuid4().hex + ".xml"
        filePath = temporary_location/temporary_model_file
        rdf_graph_rdflib.serialize(destination=filePath, format="xml")
      
        graph_world :World = World()
        model_graph_owlready : Ontology = graph_world.get_ontology(str(filePath)).load()
        logger.debug(f"Loading the obop ontology")
        model_graph_with_obop : Ontology = graph_world. \
            get_ontology(str(settings.ONTOLOGIES_DIRECTORY/"obop.owl")).load()
        logger.debug(f"Loading the BPMN Based Ontology (BBO) ontology")
        # The BBO ontology is used to represent the BBO processes and activities
        # Two changes were done on the original bbo.owl file to avoid the following problem
        # DataProperty http://BPMNbasedOntology#processType belongs to more than one entity types: [owl.ObjectProperty, owl.DatatypeProperty]; I'm trying to fix it...
        # The first change was to remove the owl:ObjectProperty from the bbo.owl file
        # The second change was to remove the owl:DatatypeProperty from the bbo.owl ware 
        # removin the line :
        # <owl:imports rdf:resource="http://purl.obolibrary.org/obo/uo/releases/2018-05-20/uo.owl"/>
        # this is because the BBO ontology import was not possible to be resolved
        model_graph_with_bbo : Ontology = graph_world. \
            get_ontology(str(settings.ONTOLOGIES_DIRECTORY/"bbo.owl")).load()

        # After reading the RDF file using owlready2, we need to remove the temporary file.
        os.remove(filePath)

        return graph_world, model_graph_with_bbo

    @staticmethod
    def readBBOElements(internal_app_static_model: AppInternalStaticModel):
        """
        This method reads all BBO elements from the RDF graph into the internal static application model
        """
        # Read BBO processes - for the sake of simplicity, it can be assumed that 
        # there exits only one BBO process in the model 
        rdflib_kg: Graph = internal_app_static_model.rdf_graph_rdflib
        main_bbo_process_uri:URIRef = None
        if (len(list(rdflib_kg.subjects(RDF.type, BBO.Process))) != 1):
            logger.error("No main BBO process found in the knowledge graph. ")
        else:
            main_bbo_process_uri = next(rdflib_kg.subjects(RDF.type, BBO.Process), None)
        logger.info(f"BBO Process: {str(main_bbo_process_uri)}")

        # Get all activities and their labels
        for bbo_activity_uri in rdflib_kg.subjects(RDF.type, BBO.Activity):
            logger.info(f"BBO Activity: {str(bbo_activity_uri)}")
            label = rdflib_kg.value(bbo_activity_uri, RDFS.label)
            activity = BBOActivity(bbo_activity_uri, BBO.Activity)
            internal_app_static_model._bbo_activities.append(activity)

        # Get all events 
        all_bbo_events_query = """
            PREFIX obop: <http://purl.org/net/obop/>
            PREFIX bbo: <https://www.irit.fr/recherches/MELODI/ontologies/BBO#>
            SELECT DISTINCT ?bbo_event_iri
            WHERE {{
                ?bbo_event_iri a ?c1.
                ?c1 rdfs:subClassOf*  bbo:Event .
            }}"""

        events = internal_app_static_model.rdf_pellet_reasoning_world. \
                    sparql(all_bbo_events_query)
        
        # Include the events in the internal application model 
        for row in events:
            (bbo_event_iri,) = row
            logger.info(f"BBO Event: {bbo_event_iri.iri}")
            bbo_event = BBOEvent(bbo_event_iri, rdflib_kg.value(bbo_event_iri, RDFS.label))
            internal_app_static_model.bbo_events.append(bbo_event)


        for bbo_sequence_flow_iri in rdflib_kg.subjects(RDF.type, BBO.SequenceFlow):
            logger.info(f"BBO Sequence Flow: {str(bbo_sequence_flow_iri)}")
            source = rdflib_kg.value(bbo_sequence_flow_iri, BBO.has_sourceRef)
            target = rdflib_kg.value(bbo_sequence_flow_iri, BBO.has_targetRef)
            source_event : BBOEvent = next((event for event in internal_app_static_model.bbo_events 
                    if event.graph_node == source), None)
            target_event : BBOEvent = next((event for event in internal_app_static_model.bbo_events 
                    if event.graph_node == target), None)
            if source is None:
                logger.error(f"BBO Sequence flow {bbo_sequence_flow_iri} does not have source reference.")
                continue
            if target is None:
                logger.error(f"BBO Sequence flow {bbo_sequence_flow_iri} does not have target reference.")
                continue
            internal_app_static_model._bbo_flows.append(
                BBOFlow(bbo_sequence_flow_iri, source_event, target_event))

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
            graph_position = internal_app_static_model.rdf_graph_rdflib.value(layout_individual, OBOP.hasPositionNumber)
            if graph_position is None:
                logger.error(f"Layout {layout_individual} does not have a position number.")
            position = graph_position.toPython()
            layout.position = position
            internal_app_static_model.add_layout(layout)
        # Read vertical layouts
        for layout_individual in internal_app_static_model.rdf_graph_rdflib.subjects(RDF.type, OBOP.VerticalLayout):
            logging.info(f"VerticalLayout: {str(layout_individual)}")
            layout = VerticalLayout(internal_app_static_model, layout_individual)
            # Read layout position because it represents the order
            # of nesting in the UI. It is also a functional property of the layout and is used to sort the layouts.
            graph_position = internal_app_static_model.rdf_graph_rdflib.value(layout_individual, OBOP.hasPositionNumber)
            if graph_position is None:
                logger.error(f"Layout {layout_individual} does not have a position number.")
            position = graph_position.toPython()
            layout.position = position
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
            position = internal_app_static_model.rdf_graph_rdflib.value(block, OBOP.hasPositionNumber)
            if position is None:
                logger.error(f"Form {block} does not have a position number.")
            
            form = Form(internal_app_static_model, block, position.toPython())
            form.target_classes =  \
                internal_app_static_model.rdf_graph_rdflib.objects( block, OBOP.targetClass)
            
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
        shapes = rdf_graph_rdflib.subjects(OBOP.modelBelongsTo, form.graph_node)
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
        other_obop_elements = rdf_graph_rdflib.subjects(OBOP.belongsTo, form.graph_node)
        for element in other_obop_elements:
            AppStaticModelFactory.readOtherOBOPElement(element, form )


    def readShaclProperty(shacl_property_instance, form: Form):
        """ 
            This method reads a part of the model which corresponds to a given SHACL property.
        """
        rdf_graph_rdflib = form.inner_app_static_model.rdf_graph_rdflib
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
        graph_position = rdf_graph_rdflib.value(element, OBOP.hasPositionNumber)
        position:int = -1
        label = None
        if element in rdf_graph_rdflib.subjects(
            OBOP.hasLabel, None):
            label = rdf_graph_rdflib.value(element, OBOP.hasLabel)
        if graph_position is None:
            logger.error(f"OBOP element {element} does not have a position number.")
        position = graph_position.toPython()
        internal_element: OBOPElement = None
        if element in rdf_graph_rdflib.subjects(
                    RDF.type, OBOP.Button):
            internal_element = OBOPElement(form, element, OBOP.Button, position, label)
        elif element in rdf_graph_rdflib.subjects(
                    RDF.type, OBOP.Label):
            internal_element = OBOPElement(form, element, OBOP.Label, position, label)
        elif element in rdf_graph_rdflib.subjects(
            RDF.type, OBOP.Field):
               internal_element = OBOPElement(form, element, OBOP.Field, position, label)
        elif element in rdf_graph_rdflib.subjects(
                    RDF.type, OBOP.Loop):
            internal_element = OBOPElement(form, element, OBOP.Loop, position)

        # Reading the actions that can be activated by the element 
        actions = rdf_graph_rdflib.objects(element, OBOP.activatesAction)
        for action in actions:
            action_type = "other"
            # Checking the type of the action
            if action in rdf_graph_rdflib.subjects(RDF.type, OBOP.SubmitBlockAction):
                action_type = "submit"
            action_pointer = ActionPointer(str(action), action_type)
            # Reading action initiators which represent the form events 
            # that activate the action. For examle, a button click
            # can activate the submit action. 
            # The ActionPointer  instances are (action, action_initiator)pairs 
            action_initiators = rdf_graph_rdflib.objects(action, OBOP.hasInitiator)
            for ai in action_initiators:
                action_pointer.action_initiators.append(str(ai))
                
            internal_element.action_pointers.append(
                    action_pointer)
        if internal_element is not None:
            form.add_element(internal_element)
        # Sorting on the HTML page in the order of positions 
        try:
            form.elements.sort(key=lambda x: x.position)
        except Exception as e:
                #TODO it might be better to assign some default value to the 
                # position attribute of the form elements
                logger.error(f"Error in sorting the form elements: {e}")    
                logger.error(f"Some form elements: {form.elements} probably do \
                             not have the position attribute set.")
                raise
        
    def readActions(internal_app_static_model: AppInternalStaticModel):
        """
        This method reads all actions from the RDF graph into the internal static application model
        """
        try:
            all_actions_query = """
            PREFIX obop: <http://purl.org/net/obop/>
            SELECT DISTINCT ?action ?xActionClass
            WHERE {
                ?action a ?xActionClass . 
                ?xActionClass rdfs:subClassOf* obop:Action .
            }"""
            all_actions_generator = internal_app_static_model.rdf_pellet_reasoning_world. \
                sparql(all_actions_query)
            for row in all_actions_generator:
                (graph_action, action_class) = row
                logger.debug(f"Action  {graph_action.iri}  ")
                action : Action = Action(graph_action.iri)
                if (action_class == OBOP.SubmitBlockAction):
                    action.type = "submit"
                    action.isSubmit = True

                internal_app_static_model.actions.append(action)

            # TODO: For other action types
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
        except Exception as e:
            logger.error(f"Error by reading actions: {e}")    
            logger.exception("Error by reading actions")


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
                            if str(obop_element.graph_node) == shacl_property.related_element:
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
            forms_and_layouts_sparql_query = """
            PREFIX obop: <http://purl.org/net/obop/>
            SELECT DISTINCT ?layout ?block
            WHERE {
                ?layout obop:belongsTo ?block .
                ?block a obop:Block .
                ?layout a ?c1 . 
                ?c1 rdfs:subClassOf* obop:Layout .
            }"""
            layout_block_pairs = internal_app_static_model.rdf_pellet_reasoning_world. \
                sparql(forms_and_layouts_sparql_query)
            #logger.debug(f"Query Results: {list(layout_block_pairs)}")

            # Denote the in the inner representation form owners to those layouts that are main layouts of the form
            
            for row in layout_block_pairs:
                (graph_layout, graph_block) = row
                logger.debug(f"Layout  {graph_layout.iri} belongs originally to form {graph_block.iri} ")
                layout = next((layout for layout in internal_app_static_model.layouts \
                              if str(layout.graph_node) == graph_layout.iri),None)
                form = next((f for f in internal_app_static_model.forms \
                             if str(f.graph_node) == graph_block.iri),None)
                if layout is not None and form is not None:
                    layout.owner_form = form
                    form.main_layout = layout

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                
            logger.error(f"Error in assigning owner form to layout: {e}{exc_type, fname, exc_tb.tb_lineno}")


    def assignElementsAndLayoutsToLayouts(internal_app_static_model: AppInternalStaticModel):
        """
            This method assigns form elements to layouts as lists of elements
            that are part of the layout and assigns layouts to layouts if they are
            nested in the layout.
        """
        # Assigning form elements to the layout
        for form in internal_app_static_model.forms:
            for element in form.elements:
                element_iri = str(element.graph_node)
                # Finding the visual container to which the element belongs in the model graph 
                element_and_layout_sparql_query = f"""
                    PREFIX obop: <http://purl.org/net/obop/>
                    SELECT DISTINCT ?layout 
                    WHERE {{
                        <{element_iri}> obop:belongsToVisual ?layout .
                        <{element_iri}> a ?c1 .
                        ?c1 rdfs:subClassOf*  obop:VisualElement .
                        ?layout a ?c2 . 
                        ?c2 rdfs:subClassOf* obop:Layout .
                    }}"""

                layouts = internal_app_static_model.rdf_pellet_reasoning_world. \
                    sparql(element_and_layout_sparql_query)
                # Include the layout (element) in the list of elements of the layout 
                
                for row in layouts:
                    (graph_layout,) = row
 
                    inner_parent_layout = next((layout for layout in internal_app_static_model.layouts \
                               if str(layout.graph_node) == str(graph_layout.iri)), None)
                    # Assigning the element to the layout
                    logger.debug(f"Element {element_iri} belongs to the layout :  {graph_layout.iri} ")
                    inner_parent_layout.elements.append(element)

        # Assigning nested layout to the parent layout
        for layout in internal_app_static_model.layouts:
            layout_iri = str(layout.graph_node)
            # Finding the parent layout  
            parent_layout_sparql_query = f"""
                PREFIX obop: <http://purl.org/net/obop/>
                SELECT DISTINCT ?parent_layout 
                WHERE {{
                    <{layout_iri}> obop:belongsToVisual ?parent_layout .
                    <{layout_iri}> a ?c1 .
                    ?c1 rdfs:subClassOf* obop:Layout .
                    ?parent_layout a ?c2 .
                    ?c2 rdfs:subClassOf* obop:Layout .
                }}"""

            layouts = internal_app_static_model.rdf_pellet_reasoning_world. \
                sparql(parent_layout_sparql_query)

            # Include found layout in the parent layout element list 
            for row in layouts:
                (parent_layout,) = row
                # TODO: can this nesting be improved because layouts are still left
                # in the internal_app_static_model.layouts list (not tree like structure)
                inner_parent_layout = next((layout for layout in internal_app_static_model.layouts \
                           if str(layout.graph_node) == str(parent_layout.iri)), None)

                logger.debug(f"Layout {layout_iri} belongs to the layout {parent_layout.iri} ")
                # Assigning layout to the parent layout
                inner_parent_layout.elements.append(layout)

        # Sorting in the order of the position on the HTML page
        try:
            for layout in internal_app_static_model.layouts:
                layout.elements.sort(key=lambda x: x.position)
        except Exception as e:
            logger.error(f"Error in sorting the layout elements: {e}")    
            logger.error(f"Some form elements: {layout.elements} probably do \
             not have the position attribute set.")

    def assignAdditionalParameters(internal_app_static_model: AppInternalStaticModel, rdf_model_file: Path, rdf_text_ttl: str):
        """
        This method assigns other parameters to the internal application model like model file name and indicator that the model is loaded.
        """
        if rdf_model_file is not None:
            internal_app_static_model.model_file_name = rdf_model_file.name
        elif rdf_text_ttl is not None:
            internal_app_static_model.model_file_name = "Loaded simple string" 

        # Indicate that the inner application model is loaded successfully
        internal_app_static_model.is_loaded = True


            
