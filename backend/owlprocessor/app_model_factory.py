import logging
import os
import sys
import uuid
from pathlib import Path
from rdflib import Graph, RDF, Namespace, URIRef
from .forms import Form, HorizontalLayout, VerticalLayout
from .form_elements import OBOPElement, SHACLFormProperty, ActionPointer
from .bbo_elements import (BBOProcess,  BBOFlowNode, BBOSubProcess,  
    BBOFlowElementsContainer, BBOProcessStartEvent, BBOExclusiveGateway,
    BBOEndEvent, BBOScriptTask, BBOUserTask, BBONormalSequenceFlow,
    BBOConditionExpression, BBOConditionalSequenceFlow,
    BBOSubProcessStartEvent)
from rdflib import RDFS
from .app_model import OBOPAction
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
        # Read the SHACL shapes graph if it exists
        # TODO this conversion should be done automatically
        internal_app_static_model.rdf_graph_rdflib = \
            AppStaticModelFactory.read_shacl_shapes_rdflib(rdf_model_file, rdf_text_ttl)
        #The project uses both rdflib and owlready2 to read the RDF file. 
        internal_app_static_model.rdf_graph_rdflib = \
            AppStaticModelFactory.read_graph_rdflib(rdf_model_file, rdf_text_ttl)
        #The owlready2 library is used to enable reasoning over the RDF graph. 
        internal_app_static_model.rdf_world_owlready, internal_app_static_model.rdf_ontology_owlready = \
            AppStaticModelFactory.read_graph_owlready(internal_app_static_model.rdf_graph_rdflib)
        internal_app_static_model.rdf_pellet_reasoning_world = \
            create_pellet_reasoning_graph(
                internal_app_static_model.rdf_world_owlready)           
        AppStaticModelFactory.read_bbo_elements(internal_app_static_model)
        AppStaticModelFactory.readAllLayouts(internal_app_static_model)
        AppStaticModelFactory.readAllForms(internal_app_static_model)
        AppStaticModelFactory.readActions(internal_app_static_model)
        AppStaticModelFactory.connect_bbo_script_tasks_with_obop_actions(internal_app_static_model)
        AppStaticModelFactory.combine_shacl_properties_and_obop_elements(internal_app_static_model)
        AppStaticModelFactory.assignOwnerFormsToLayouts(internal_app_static_model)
        AppStaticModelFactory.assignElementsAndLayoutsToLayouts(internal_app_static_model)
        AppStaticModelFactory.assignAdditionalParameters(internal_app_static_model, rdf_model_file, rdf_text_ttl)
        return internal_app_static_model



    @staticmethod
    def read_graph_rdflib( rdf_file_name:str = None, rdf_text_ttl:str = None) -> Graph:
        """
        Reads an RDF file and parses it into the graph objects.
        The rdflib library is used to parse the RDF file and create a graph.
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
    def read_shacl_shapes_rdflib( rdf_file_name:str = None, rdf_shapes_text_ttl:str = None) -> Graph:
        """
        Reads an RDF file with shacl_shapes and parses it into the graph objects.
           rdf_file_name (str): The path to the RDF file.
            rdf_text (str): The RDF in the string form. 
        """
        rdf_shapes_file_name: Path = None
        if rdf_file_name is not None:
            if Path(rdf_file_name).suffix == ".ttl":
                base = Path(rdf_file_name).with_suffix('')  # Remove .ttl
                rdf_shapes_file_name = Path(str(base) + '_shacl_shape.ttl')
            else:
                raise ValueError("The RDF file name must have the .ttl extension.")
            # Reading the RDF graph from the file
            logger.debug(f"Reading and parsing the SHACL file {rdf_shapes_file_name}")
            rdf_graph_rdflib = Graph()
            rdf_graph_rdflib.parse(rdf_shapes_file_name, format="ttl")
            return rdf_graph_rdflib
        else:
            # Reading the RDF graph from the string
            logger.debug("Reading and parsing the RDF string in ttl format.")
            # Reading the RDF graph in the string form using rdflib library
            rdf_graph_rdflib = Graph()
            rdf_graph_rdflib.parse(data = rdf_shapes_text_ttl, format="ttl")  
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
    def read_bbo_elements(internal_app_static_model: AppInternalStaticModel):
        """
        This method reads all BBO elements from the RDF graph into the internal static application model
        """
        # Read main BBO process
        AppStaticModelFactory.read_bbo_process(internal_app_static_model)
        # Read subprocesses 
        AppStaticModelFactory.read_bbo_suprocesses(internal_app_static_model)
        # Get all tasks
        AppStaticModelFactory.read_bbo_tasks(internal_app_static_model)
        # Read gateways
        AppStaticModelFactory.read_bbo_gateways(internal_app_static_model)
        # Get all events 
        AppStaticModelFactory.read_bbo_events(internal_app_static_model)
        # Get all sequence flows
        AppStaticModelFactory.read_bbo_flow_elements(internal_app_static_model) 



    @staticmethod
    def read_bbo_process(internal_app_static_model: AppInternalStaticModel):
        """
        Reads BBO processes from the RDF graph into the internal static application model.
        The BBO process is a main process in the application model.
        """
        rdflib_kg: Graph = internal_app_static_model.rdf_graph_rdflib
        main_bbo_process_uri:URIRef = None
        if (len(list(rdflib_kg.subjects(RDF.type, BBO.Process))) != 1):
            logger.error("No main BBO process found in the knowledge graph. ")
        else:
            # If there is only one BBO process, we can assume that to be the main process
            main_bbo_process_uri = next(rdflib_kg.subjects(RDF.type, BBO.Process), None)
            internal_app_static_model.main_bbo_process = BBOProcess(main_bbo_process_uri)
            logger.info(f"BBO Process: {str(main_bbo_process_uri)}")


    @staticmethod
    def read_bbo_suprocesses(internal_app_static_model: AppInternalStaticModel):
        """ 
            Read BBO subprocesses  
        """
        rdflib_kg: Graph = internal_app_static_model.rdf_graph_rdflib
        # Read all BBO subprocesses and their super processes as containers
        for bbo_subprocess_uri in rdflib_kg.subjects(RDF.type, BBO.SubProcess):
            # First we add all subprocesses to the internal model without the container
            # to solve the problem of subprocesses that are part of other subprocesses
            subprocess : BBOSubProcess = BBOSubProcess(URIRef(bbo_subprocess_uri), None)
            internal_app_static_model.bbo_subprocesses.append(subprocess)
            # Then we read the container of the subprocess and assign it to the subprocess
            # or to the main process if the container is the main process
            logger.info(f"BBO Subprocess: {str(bbo_subprocess_uri)} - reading attempt")
            subprocess_has_container_query = f"""
            PREFIX bbo: <https://www.irit.fr/recherches/MELODI/ontologies/BBO#>
            SELECT DISTINCT ?container
            WHERE {{
                <{str(bbo_subprocess_uri)}> bbo:has_container ?container . 
                ?container a ?containerClass .
                ?containerClass rdfs:subClassOf* bbo:FlowElementsContainer .
            }}"""
            try:
                result_generator = internal_app_static_model.rdf_pellet_reasoning_world. \
                sparql(subprocess_has_container_query)
                found_container : bool= False
                for row in result_generator:
                    (container, ) = row
                    if not found_container:
                        found_container = True
                        if str(internal_app_static_model.main_bbo_process.graph_node) == container.iri:
                            # If the container is of main process, we can assume that the subprocess is a part of the main process
                            subprocess.flow_element_container = internal_app_static_model.main_bbo_process
                            internal_app_static_model.main_bbo_process.flow_elements.append(
                                subprocess)
                            logger.debug(f"BBO Subprocess: {str(bbo_subprocess_uri)} added to the main process.")
                        else:
                            # If the container is not of main process, we can assume that the subprocess is a part of other subprocess
                            # This could be a problem if the subprocess is a part of another subprocess that is not yet read
                            subprocess_container : BBOSubProcess = next((c for c in internal_app_static_model.bbo_subprocesses 
                                    if str(c.graph_node) == container.iri), None)
                            if subprocess_container is None:
                                logger.error(f"Container {container.iri} not found for the BBO subprocess {bbo_subprocess_uri}.")
                            else: 
                                # Container found in the list of subprocesses and the 
                                # suprocess is added to the container and container is 
                                #  assigned to the subprocess
                                internal_app_static_model.bbo_subprocesses.append(subprocess)
                                subprocess.flow_element_container = subprocess_container
                                logger.debug(f"BBO Subprocess: {str(bbo_subprocess_uri)} added to the subprocess {str(subprocess_container.graph_node)}.")
                    else:
                        raise ValueError(
                            f"Multiple containers found for the BBO subprocess {bbo_subprocess_uri}.")
            except Exception as e:
                logger.error(f"Error by reading subprocesses: {e}")    
                logger.exception("Error by reading subprocesses.{bbo_subprocess_uri}")

       
    @staticmethod
    def read_bbo_events(internal_app_static_model: AppInternalStaticModel):
        rdflib_kg: Graph = internal_app_static_model.rdf_graph_rdflib
        # check if there are any BBO events in the knowledge graph
        # that have no container

        events_without_containers = """
            PREFIX obop: <http://purl.org/net/obop/>
            PREFIX bbo: <https://www.irit.fr/recherches/MELODI/ontologies/BBO#>
            SELECT DISTINCT ?bbo_event
            WHERE {{
                ?bbo_event a ?c1 .
                ?c1 rdfs:subClassOf*  bbo:Event .
                FILTER NOT EXISTS { ?bbo_event bbo:has_container ?container . }
            }}"""

        try:
            events_without_containers_result = internal_app_static_model.rdf_pellet_reasoning_world. \
                sparql(events_without_containers)
            for row in events_without_containers_result:
                (bbo_event, ) = row
                logger.error(f"BBO Event without container: {bbo_event.iri}")
        except Exception as e:
            logger.error(f"Error by reading BBO events without containers: {e}")
            logger.exception("Error by reading BBO events without containers.") 

        # Read all BBO events and their containers, because the BBO events 
        # are part of the BBO processes or subprocesses in our application model.
        all_bbo_events_query = """
            PREFIX obop: <http://purl.org/net/obop/>
            PREFIX bbo: <https://www.irit.fr/recherches/MELODI/ontologies/BBO#>
            SELECT DISTINCT ?bbo_event ?c1 ?container
            WHERE {{
                ?bbo_event a ?c1 .
                ?bbo_event bbo:has_container ?container .
                ?c1 rdfs:subClassOf*  bbo:Event .
            }}"""
        try:
            events = internal_app_static_model.rdf_pellet_reasoning_world. \
                    sparql(all_bbo_events_query)
        
            # Include the events in the internal application model 
            for row in events:
                (bbo_event, c1, container) = row
                logger.info(f"BBO Event: {bbo_event.iri}, of class: {c1.iri} in container: {container.iri}")
                if c1.iri == str(BBO.ProcessStartEvent):
                    # If the event is a process start event, we need to check if it is in the main process container
                    if container.iri == str(internal_app_static_model.main_bbo_process.graph_node):
                        inner_event : BBOProcessStartEvent = BBOProcessStartEvent(
                            URIRef(bbo_event.iri),
                            internal_app_static_model.main_bbo_process , 
                            str(rdflib_kg.value(bbo_event, RDFS.comment)))
                        internal_app_static_model.main_bbo_process.add_flow_element(inner_event)  
                    else:
                        logger.error(f"BBO Process Start Event {bbo_event.iri} is not in the \
                             main process container.")
                        raise ValueError( f"BBOEvent {bbo_event.iri} is not correctly specified ." )
                elif c1.iri == str(BBO.SubProcessStartEvent):
                    internal_event_container = next((c for c in internal_app_static_model.bbo_subprocesses 
                            if str(c.graph_node) == container.iri), None)

                    if internal_event_container is not None:
                        inner_event = BBOSubProcessStartEvent(URIRef(bbo_event.iri), internal_event_container, rdflib_kg.value(bbo_event, RDFS.comment))
                        internal_event_container.add_flow_element(inner_event)
                    else:
                        logger.error(f"BBO SubProcessStartEvent {bbo_event.iri} is not in any subprocess container.")
                        raise ValueError( f"BBOSubProcessStartEvent {bbo_event.iri} is not correctly specified ." )
                elif c1.iri == str(BBO.EndEvent):
                    # If the event is an end event, we need to check if it is in the main process container or in a subprocess container
                    if container.iri == str(internal_app_static_model.main_bbo_process.graph_node):
                        inner_event : BBOEndEvent = BBOEndEvent(URIRef(bbo_event.iri), 
                                    internal_app_static_model.main_bbo_process, rdflib_kg.value(bbo_event, RDFS.comment))
                        internal_app_static_model.main_bbo_process.add_flow_element( inner_event)
                    else :
                        # If the event is in a subprocess container, we need to find the corresponding subprocess
                        internal_container = next((c for c in internal_app_static_model.bbo_subprocesses 
                            if str(c.graph_node) == container.iri), None)

                        if internal_container is not None:
                            inner_event = BBOEndEvent(URIRef(bbo_event.iri), internal_container, rdflib_kg.value(bbo_event, RDFS.comment))
                            internal_container.add_flow_element(inner_event)
                        else:
                            logger.error(f"BBO End Event {bbo_event.iri} is not in any subprocess container.")
                            raise ValueError( f"BBOEvent {bbo_event.iri} is not correctly specified ." )
                else:
                    raise ValueError( f"Unknown BBO event type: {c1.iri}." )
        except  Exception as e:
            logger.error(f"Error by reading BBO events: {e}")
            logger.exception("Error by reading BBO events.")
                                    

    @staticmethod
    def read_bbo_tasks(internal_app_static_model: AppInternalStaticModel):
        """
        Reads BBO tasks from the RDF graph into the internal static application model.
        The BBO task is a part of the BBO process or subprocesses.
        """
        rdflib_kg: Graph = internal_app_static_model.rdf_graph_rdflib
        # Read BBO Script Tasks that are part of the BBO process or subprocesses
        for bbo_task_uri in rdflib_kg.subjects(RDF.type, BBO.ScriptTask):
            logger.info(f"BBO Script Task: {str(bbo_task_uri)}")
            # Read the container of the task
            container = rdflib_kg.value(bbo_task_uri, BBO.has_container)
            if container is not None:
                # Find the container by comparing the graph node
                # with the main process and other subprocesses 
                if (container == internal_app_static_model.main_bbo_process.graph_node):
                    task = BBOScriptTask(bbo_task_uri, 
                        internal_app_static_model.main_bbo_process, 
                        str(rdflib_kg.value(bbo_task_uri, RDFS.comment)))
                    internal_app_static_model.main_bbo_process.add_flow_element(task)
                else:
                    subprocess: BBOSubProcess = next((c for c in internal_app_static_model.bbo_subprocesses
                                if c.graph_node == container), None)
                    if subprocess is not None:
                        task = BBOScriptTask(bbo_task_uri, 
                                    subprocess, 
                                    str(rdflib_kg.value(bbo_task_uri, RDFS.comment)))
                        subprocess.add_flow_element(task)
                    else:
                        logger.error(f"BBO Script Task {bbo_task_uri} does not have a valid container.")
                        continue
            else:
                logger.error(f"BBO Script Task {bbo_task_uri} does not have a container.")

        # Read BBO User Tasks that are part of the BBO process or subprocesses
        for bbo_task_uri in rdflib_kg.subjects(RDF.type, BBO.UserTask):
            logger.info(f"BBO User Task: {str(bbo_task_uri)}")
            # Read the container of the task
            container = rdflib_kg.value(bbo_task_uri, BBO.has_container)
            if container is not None:
                # Find the container by comparing the graph node
                # with the main process and other subprocesses 
                if (container == internal_app_static_model.main_bbo_process.graph_node):
                    task = BBOUserTask(bbo_task_uri, 
                        internal_app_static_model.main_bbo_process, 
                        str(rdflib_kg.value(bbo_task_uri, RDFS.comment)))
                    internal_app_static_model.main_bbo_process.add_flow_element(task)
                else:
                    subprocess: BBOSubProcess = next((c for c in internal_app_static_model.bbo_subprocesses
                                if c.graph_node == container), None)
                    if subprocess is not None:
                        task = BBOUserTask(bbo_task_uri, 
                                    subprocess, 
                                    str(rdflib_kg.value(bbo_task_uri, RDFS.comment)))
                        subprocess.add_flow_element(task)
                    else:
                        logger.error(f"BBO Task {bbo_task_uri} does not have a valid container.")
                        continue
            else:
                logger.error(f"BBO User {bbo_task_uri} does not have a container.")

    @staticmethod
    def read_bbo_gateways(internal_app_static_model: AppInternalStaticModel):
        """
        Reads BBO gateways from the RDF graph into the internal static application model.
        The BBO gateway is a part of the BBO process or subprocesses.
        """
        rdflib_kg: Graph = internal_app_static_model.rdf_graph_rdflib
        # Read BBO Exclusive Gateways that are part of the BBO process or subprocesses
        for bbo_gateway_uri in rdflib_kg.subjects(RDF.type, BBO.ExclusiveGateway):
            logger.info(f"BBO Exclusive Gateway: {str(bbo_gateway_uri)}")
            # Read the container of the gateway
            container = rdflib_kg.value(bbo_gateway_uri, BBO.has_container)
            if container is not None:
                # Find the container by comparing the graph nodes
                # with the main process and other subprocesses 
                if (container == internal_app_static_model.main_bbo_process.graph_node):
                    gateway = BBOExclusiveGateway(bbo_gateway_uri, 
                        internal_app_static_model.main_bbo_process, 
                        str(rdflib_kg.value(bbo_gateway_uri, RDFS.comment)))
                    internal_app_static_model.main_bbo_process.add_flow_element(gateway)
                else:
                    subprocess: BBOSubProcess = next((c for c in internal_app_static_model.bbo_subprocesses
                                if c.graph_node == container), None)
                    if subprocess is not None:
                        gateway = BBOExclusiveGateway(bbo_gateway_uri, 
                                    subprocess, 
                                    str(rdflib_kg.value(bbo_gateway_uri, RDFS.comment)))
                        subprocess.add_flow_element(gateway)
                    else:
                        logger.error(f"BBO Exclusive Gateway {bbo_gateway_uri} does not have a valid container.")
                        continue
            else:
                logger.error(f"BBO Exclusive Gateway {bbo_gateway_uri} does not have a container.")

    
    @staticmethod
    def read_bbo_flow_elements(internal_app_static_model: AppInternalStaticModel):
        """
        Reads BBO flow elements from the RDF graph into the internal static application model.
        The BBO flow elements are part of the BBO process or subprocesses.
        """

        # Read first BBO Normal Sequence Flows
        normal_sequence_flow_query = """ 
        PREFIX bbo: <https://www.irit.fr/recherches/MELODI/ontologies/BBO#>     
        SELECT DISTINCT ?bbo_sequence_flow ?source ?target ?container
        WHERE {
            ?bbo_sequence_flow a bbo:NormalSequenceFlow .
            ?bbo_sequence_flow bbo:has_sourceRef ?source .   
            ?bbo_sequence_flow bbo:has_targetRef ?target .
            ?bbo_sequence_flow bbo:has_container ?container .
        }"""
        try:
            results = internal_app_static_model.rdf_pellet_reasoning_world.sparql(normal_sequence_flow_query)
            for row in results:
                (bbo_sequence_flow, source, target, container) = row
                logger.info(f"BBO Normal Sequence Flow Element: {bbo_sequence_flow.iri}, Source: {source.iri}, Target: {target.iri}, Container: {container.iri}")
                # Find the source and target flow elements in the internal application model
                if container.iri == str(internal_app_static_model.main_bbo_process.graph_node):
                    # If the container is the main process, we can assume that the flow element is part of the main process
                    bbo_flow_container: BBOFlowElementsContainer = internal_app_static_model.main_bbo_process
                    source_element : BBOFlowNode = next((e for e in bbo_flow_container.flow_elements
                            if str(e.graph_node) == source.iri), None)
                    target_element :BBOFlowNode = next((e for e in bbo_flow_container.flow_elements
                            if str(e.graph_node) == target.iri), None)

                    # If the source and target elements are found, we can create a flow element
                    if source_element is not None and target_element is not None:
                        flow_element = BBONormalSequenceFlow(URIRef(bbo_sequence_flow.iri),
                            bbo_flow_container, source_element, target_element)
                        internal_app_static_model.main_bbo_process.flow_elements.append(flow_element)
                    else:
                        logger.error(f"BBO Flow Element {bbo_sequence_flow.iri} has invalid source or target.")
                else:
                    # If the container is not the main process, we need to find it in the corresponding subprocess
                    bbo_flow_container: BBOSubProcess = next((c for c in internal_app_static_model.bbo_subprocesses 
                                              if str(c.graph_node) == container.iri), None)
                    if bbo_flow_container is None:
                        logger.error(f"BBO Flow Element {bbo_sequence_flow.iri} does not have a valid container.")
                        raise ValueError(f"BBO Flow Element {bbo_sequence_flow.iri} does not have a valid container.")
                        continue
                    else: 
                        # If the container is a subprocess, we can assume that the flow element is part of the subprocess
                        source_element: BBOFlowNode = next((e for e in bbo_flow_container.flow_elements 
                            if str(e.graph_node) == source.iri), None)
                        target_element : BBOFlowNode = next((e for e in bbo_flow_container.flow_elements
                            if str(e.graph_node) == target.iri), None)
                        if source_element is not None and target_element is not None:
                            flow_element = BBONormalSequenceFlow(URIRef(bbo_sequence_flow.iri), bbo_flow_container, source_element, target_element)
                            bbo_flow_container.add_flow_element(flow_element)
                        else:
                            logger.error(f"BBO Flow Element {bbo_sequence_flow.iri} has invalid source or target.")
        except Exception as e:
            logger.error(f"Error by reading BBO flow elements: {e}")
            logger.exception("Error by reading BBO flow elements.")

        # Read BBO Conditional Sequence Flows
        conditional_sequence_flow_query = """   
        PREFIX bbo: <https://www.irit.fr/recherches/MELODI/ontologies/BBO#> 
        SELECT DISTINCT ?bbo_sequence_flow ?source ?target ?condition_expression ?container
        WHERE {
            ?bbo_sequence_flow a bbo:ConditionalSequenceFlow .
            ?bbo_sequence_flow bbo:has_sourceRef ?source .   
            ?bbo_sequence_flow bbo:has_targetRef ?target .
            ?bbo_sequence_flow bbo:has_conditionExpression ?condition_expression .
            ?bbo_sequence_flow bbo:has_container ?container .
        }"""
        try:  
            results = internal_app_static_model.rdf_pellet_reasoning_world.sparql( 
                conditional_sequence_flow_query)
            for row in results: 
                (bbo_sequence_flow, source, target, condition_expression, container) = row
                logger.info(f"Reading BBO Conditional Sequence Flow Element: {bbo_sequence_flow.iri}, Source: {source.iri}, Target: {target.iri}, Container: {container.iri}, Conditional Expression: {condition_expression.iri} ")
                # Find the condition expression
                internal_condition_expression : BBOConditionExpression = BBOConditionExpression ( URIRef(condition_expression.iri),  internal_app_static_model.rdf_graph_rdflib.value(URIRef(condition_expression.iri),OBOP.selectedAction).toPython())

                # Find the source and target flow elements in the internal application model
                if container.iri == str(internal_app_static_model.main_bbo_process.graph_node):
                    # If the container is the main process, we can assume that the flow element is part of the main process
                    bbo_flow_container: BBOFlowElementsContainer = internal_app_static_model.main_bbo_process
                    source_element : BBOFlowNode = next((e for e in bbo_flow_container.flow_elements
                            if str(e.graph_node) == source.iri), None)
                    target_element :BBOFlowNode = next((e for e in bbo_flow_container.flow_elements
                            if str(e.graph_node) == target.iri), None)

                    # If the source and target elements are found, we can create a flow element
                    if source_element is not None and target_element is not None:
                        flow_element = BBOConditionalSequenceFlow(
                            URIRef(bbo_sequence_flow.iri), 
                            bbo_flow_container, 
                            source_element, 
                            target_element,
                            internal_condition_expression, 
                            str(internal_app_static_model.rdf_graph_rdflib.value(URIRef(bbo_sequence_flow.iri), RDFS.comment)))
                        internal_app_static_model.main_bbo_process.flow_elements.append(flow_element)
                        logger.debug("Loaded BBO Conditional Sequence Flow Element") 
                        logger.debug(f"{flow_element.__repr__()} to the main process.")
                    else:
                        logger.error(f"BBO Conditional Sequence Flow Element {bbo_sequence_flow.iri} has invalid source or target.")
                else:
                    # If the container is not the main process, we need to find it in the corresponding subprocess
                    bbo_flow_container: BBOSubProcess = next((c for c in internal_app_static_model.bbo_subprocesses 
                                              if str(c.graph_node) == container.iri), None)
                    if bbo_flow_container is None:
                        logger.error(f"BBO Conditional Flow Element {bbo_sequence_flow.iri} does not have a valid container.")
                        raise ValueError(f"BBO Conditional Flow Element {bbo_sequence_flow.iri} does not have a valid container.")
                        continue
                    else: 
                        # If the container is a subprocess, we can assume that the flow element is part of the subprocess
                        source_element: BBOFlowNode = next((e for e in bbo_flow_container.flow_elements 
                            if str(e.graph_node) == source.iri), None)
                        target_element : BBOFlowNode = next((e for e in bbo_flow_container.flow_elements
                            if str(e.graph_node) == target.iri), None)
                        if source_element is not None and target_element is not None:
                            flow_element = BBOConditionalSequenceFlow(
                                URIRef(bbo_sequence_flow.iri), 
                                bbo_flow_container, 
                                source_element, 
                                target_element, 
                                internal_condition_expression,
                                str(internal_app_static_model.rdf_graph_rdflib.value(URIRef(bbo_sequence_flow.iri), RDFS.comment)))
                            bbo_flow_container.add_flow_element(flow_element)
                        else:
                            logger.error(f"BBO Conditional Sequence Flow Element {bbo_sequence_flow.iri} has invalid source or target.")    
        except Exception as e:
            logger.error(f"Error by reading BBO conditional sequence flows: {e}")
            logger.exception("Error by reading BBO conditional sequence flows.")    

    @staticmethod
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
        It is implemented using SHACL shapes, DASH and other SHACL extensions.

        The method reads additional form element which are not only represented with SHACL shapes in the
        mode graph but with OBOP elements such as button, label and similar elements, These elements are
        so far related to the form using the obop:belongsTo property. Its different from the SHACL shapes.
        """
        # Reading SHACL shapes that are related to the form is now skipped.
        #shapes = rdf_graph_rdflib.subjects(OBOP.modelBelongsTo, form.graph_node)
        # for s in shapes:
        #     if (s, RDF.type, SH.NodeShape) in rdf_graph_rdflib:
        #         shacl_node_shape = s  # TODO check if there is only one shape for a form
        #         # Reading shapes that will be necessary to generate a set of triples
        #         # (subgraph of the output graph) when the corresponding form is submitted in the UI
        #         # The set of triples can be created using the add() method
        #         form.target_classes = list(
        #             map(
        #                 lambda item: str(item),
        #                 rdf_graph_rdflib.objects(shacl_node_shape, SH.targetClass),
        #             )
        #         )
        #         logger.debug(
        #             f"Form target classes: {jsonpickle.encode(form.target_classes)}"
        #         )
        #         for shacl_property_instance in rdf_graph_rdflib.objects(
        #             shacl_node_shape, SH.property
        #         ):
        #             # Reading SHACL properties that are represented with SHACL shapes
        #             # Those SHACL properties that don't have any further
        #             # properties are not considered as form elements
        #             if (shacl_property_instance, None, None) in rdf_graph_rdflib:
        #                 AppStaticModelFactory.readShaclProperty(shacl_property_instance, form)

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
        elif element in rdf_graph_rdflib.subjects( OBOP.hasText, None):
            label = rdf_graph_rdflib.value(element, OBOP.hasText)
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
            elif action in rdf_graph_rdflib.subjects(RDF.type, OBOP.SHACLValidation):
                action_type = "shacl_validation"
            action_pointer = ActionPointer(str(action), action_type)
            # Reading action initiators which represent the form events 
            # that activate the action. For examle, a button click
            # can activate the submit action. 
            # The ActionPointer  instances are (action, action_initiator) pairs 
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
                action : OBOPAction = OBOPAction(URIRef(graph_action.iri))
                if (action_class.iri == str(OBOP.SubmitBlockAction)):
                    action.type = "submit"
                    action.isSubmit = True
                elif(action_class.iri == str(OBOP.GenerateJSONForm)):
                    action.type = "generate_json_form"
                elif(action_class.iri == str(OBOP.SHACLValidation)):
                    action.type = "shacl_validation"
                else:
                    action.type = "other"
                    logger.error(f"Unknown action type: {action_class.iri}")
                internal_app_static_model.actions.append(action)
                logger.debug(f"Loaded action: {action.__repr__()}")

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

    @staticmethod
    def connect_bbo_script_tasks_with_obop_actions (internal_app_static_model: AppInternalStaticModel):
        tasks_and_actions_query = """
            PREFIX obop: <http://purl.org/net/obop/>
            PREFIX bbo: <https://www.irit.fr/recherches/MELODI/ontologies/BBO#> 
            SELECT DISTINCT ?bbo_script_task ?action ?container
            WHERE {
            ?bbo_script_task a bbo:ScriptTask .
            ?bbo_script_task bbo:has_container ?container .
            ?container a ?container_class .
            ?container_class rdfs:subClassOf* bbo:FlowElementsContainer .
            ?bbo_script_task obop:executesAction  ?action .
            ?action a ?action_class .
            ?action_class rdfs:subClassOf* obop:Action .
            }"""
        try:  
            results = internal_app_static_model.rdf_pellet_reasoning_world.sparql( 
                tasks_and_actions_query)
            for row in results: 
                (bbo_script_task, action, container) = row
                logger.info(f"Reading BBO.ScriptTask: {bbo_script_task.iri} and OBOP action: {action.iri}, in container: {container.iri}")
                # Find the source and target flow elements in the internal application model
                if container.iri == str(internal_app_static_model.main_bbo_process.graph_node):
                    # If the container is the main process, we update  of the main process
                    bbo_flow_container: BBOFlowElementsContainer = internal_app_static_model.main_bbo_process
                    internal_bbo_script_task : BBOScriptTask = next((e for e in bbo_flow_container.flow_elements
                            if str(e.graph_node) == bbo_script_task.iri), None)
                    internal_obop_action :OBOPAction = next((e for e in 
                        internal_app_static_model.actions 
                        if str(e.graph_node) == action.iri), None)

                    # if the internal_bbo_script_task and internal_bbo_action are found, we can create the connection 

                    if internal_bbo_script_task is not None and internal_obop_action is not None:
                        internal_bbo_script_task.obop_action = internal_obop_action
                        logger.debug(f"Connected BBO Script Task {internal_bbo_script_task} with OBOP action {internal_obop_action.__repr__()}.")
                        logger.debug(f"{internal_bbo_script_task.__repr__()} connected script task.")
                    else:
                        logger.error(f"BBO Script Task {bbo_script_task.iri} or OBOP action {action.iri} not found in the internal model.")
                        logger.exception("Error by connecting BBO script tasks with OBOP actions.")
                else:
                    # If the container is not the main process, we need to find it in the corresponding subprocess
                    bbo_flow_container: BBOSubProcess = next((c for c in internal_app_static_model.bbo_subprocesses 
                                              if str(c.graph_node) == container.iri), None)
                    if bbo_flow_container is None:
                        logger.error(f"BBO Script Task {bbo_script_task.iri} does not have a valid container.")
                        raise ValueError(f"BBO Script Task {bbo_script_task.iri} does not have a valid container.")
                        continue
                    else: 
                        # If the container is a subprocess, we can assume that the flow element is part of the subprocess
                        internal_bbo_script_task: BBOFlowNode = next((e for e in bbo_flow_container.flow_elements 
                            if str(e.graph_node) == bbo_script_task.iri), None)
                        internal_obop_action : OBOPAction = next((e for e in 
                        internal_app_static_model.actions 
                            if str(e.graph_node) == action.iri), None)

                        if internal_bbo_script_task is not None and internal_obop_action is not None:
                            internal_bbo_script_task.obop_action = internal_obop_action
                            logger.debug(f"Connected BBO Script Task {internal_bbo_script_task} with OBOP action {internal_obop_action} in subprocess {bbo_flow_container}.")
                            logger.debug(f"{internal_bbo_script_task.__repr__()} connected script task.")
                        else:
                            logger.error(f"BBO Script Task {bbo_script_task.iri} or OBOP action {action.iri} not found in the internal model.")
                            logger.exception("Error by connecting BBO script tasks with OBOP actions.")
        except Exception as e:
            logger.error(f"Error by connecting BBO Script Task and OBOP actions: {e}")
            logger.exception("Error by connecting BBO Script Task and OBOP actions.")


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
                try:
                    
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
                except Exception as e:
                    logger.error(f"Error in assigning element {element_iri} to layout: {e}")    
                    logger.exception(f"Error in assigning element {element_iri} to layout.")

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


            
