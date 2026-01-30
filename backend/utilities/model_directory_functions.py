import os
import json
import logging
import tempfile
from rdflib import Graph, RDF, Namespace
from rdflib.plugins.sparql import prepareQuery
from owlready2 import World, sync_reasoner_pellet
from owlready2 import sync_reasoner_hermit
from pathlib import Path
from config.settings import Settings, get_settings

ontoui_logger = logging.getLogger("ontoui_app")

ontoui_logger.error(os.environ)
settings: Settings = get_settings()

if "JAVA_HOME" not in os.environ:
    os.environ["JAVA_HOME"] = settings.CURREN_JAVA_HOME
    ontoui_logger.debug(f"JAVA_HOME not set. Setting it to {settings.CURREN_JAVA_HOME}")

OBOP = Namespace("http://purl.org/net/obop/")


def read_model_files_from_directory(models_directory: str = "app_models"):
    """
    Reads the current list of inner model files (*.ttl files) in the folder 'app_models' into
    json format.
    """
    models_info = []
    directory_path = os.getcwd() + "/" + models_directory
    ontoui_logger.debug("Directory: %s", directory_path)
    for filename in os.listdir(directory_path):
        if filename.endswith(".ttl"):
            filepath = os.path.join(directory_path, filename)
            # Check if the file is a file and not a directory
            if os.path.isfile(filepath):
                try:
                    ontoui_logger.debug("File: %s", filename)
                    graph = Graph().parse(filepath, format="ttl")
                    graph.bind(
                        "obop", OBOP
                    )  # Bind the namespace prefix for use in the SPARQL query
                    q = prepareQuery(
                        """
                        SELECT ?model ?description WHERE {
                            ?model a obop:Model.
                            ?model obop:modelDescription ?description.
                        }   
                    """,
                        initNs={"obop": OBOP},
                    )

                    query_result = graph.query(q)  #
                    if len(query_result) == 0:
                        ontoui_logger.debug(
                            "The file is not a valid UI model file. It has to contain exactly one obop:Model instance."
                        )
                    elif len(query_result) > 1:
                        ontoui_logger.debug(
                            f"The UI model file {filename} has more obop:Model instances."
                        )
                        for row in query_result:
                            ontoui_logger.debug(row)
                    else:
                        query_result_list = list(query_result)
                        model, description = query_result_list[0]
                        ontoui_logger.debug("Model: %s", model)
                        ontoui_logger.debug("Description: %s", description)
                        models_info.append(
                            {
                                "filename": filename,
                                "model": str(model),
                                "description": str(description),
                                "filepath": filepath,
                            }
                        )
                except Exception as e:
                    ontoui_logger.error(f"Error processing file {filename}: {e}")
                    continue  # Skip the file if there is an error
    models_info_json = models_info
    ontoui_logger.debug("Model description: %s", models_info_json)
    return models_info_json


def print_triples_in_graph(graph_world: World):
    """
    Prints all triples in the given graph_world.
    """
    for s, p, o in graph_world.as_rdflib_graph().triples((None, None, None)):
        ontoui_logger.debug(f"Subject: {s}, Predicate: {p}, Object: {o}")


def create_pellet_reasoning_graph(graph_world: World) -> World:
    """
    The function applies the pellet reasoner and returns results.
    The graph world is first cloned in order to avoid modifying the original graph.
    """

    try:
        temporary_location: Path = settings.TEMPORARY_MODELS_DIRECTORY
        graph_world.save(file=str(temporary_location / "before.owl"), format="rdfxml")
        # Clone the graph world to avoid modifying the original graph
        cloned_world = World()
        # Step 1: Save the original world to a temporary file
        with tempfile.NamedTemporaryFile(suffix=".owl") as tmp:
            graph_world.save(tmp.name)

            # Step 2: Load the saved data into the cloned world
            ontology = cloned_world.get_ontology(tmp.name).load()

        # Step 3: Apply Pellet reasoning

        cloned_world.save(
            file=str(temporary_location / "after_cloning.owl"), format="rdfxml"
        )
        with cloned_world:
            sync_reasoner_pellet(
                cloned_world,
                infer_property_values=True,
                infer_data_property_values=True,
            )
        cloned_world.save(
            file=str(temporary_location / "after_pellet_applied.owl"), format="rdfxml"
        )
        return cloned_world
    except FileNotFoundError as e:
        ontoui_logger.error(f"File not found: {e}")
        raise
    except Exception as e:
        ontoui_logger.error(f"Error during clonning or Pellet reasoning: {e}")
        raise


def create_hermit_reasoning_graph(graph_world: World) -> World:
    """
    The function applies the pellet reasoner and returns results.
    """
    try:
        temporary_location: Path = settings.TEMPORARY_MODELS_DIRECTORY
        graph_world.save(
            file=str(temporary_location / "before_hermit.owl"), format="rdfxml"
        )
        # Clone the graph world to avoid modifying the original graph
        cloned_world = World()
        # Step 1: Save the original world to a temporary file
        with tempfile.NamedTemporaryFile(suffix=".owl") as tmp:
            graph_world.save(tmp.name)

            # Step 2: Load the saved data into the cloned world
            ontology = cloned_world.get_ontology(tmp.name).load()

        # Step 3: Apply Pellet reasoning

        cloned_world.save(
            file=str(temporary_location / "after_cloning.owl"), format="rdfxml"
        )
        with cloned_world:
            sync_reasoner_hermit(
                cloned_world,
                infer_property_values=True
            )
        cloned_world.save(
            file=str(temporary_location / "after_hermit_applied.owl"), format="rdfxml"
        )
        return cloned_world
    except FileNotFoundError as e:
        ontoui_logger.error(f"File not found: {e}")
        raise
    except Exception as e:
        ontoui_logger.error(f"Error during clonning or Hermit reasoning: {e}")
        raise
