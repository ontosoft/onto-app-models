import os
import json
import logging
from rdflib import Graph, RDF, Namespace
from rdflib.plugins.sparql import prepareQuery
from owlready2 import World, sync_reasoner_pellet
from owlready2 import sync_reasoner_hermit
from app.core.config import settings
from app.owlprocessor.static_model_cache import (
    reasoned_world_cache,
    serialize_world,
    load_world,
)

ontoui_logger = logging.getLogger("ontoui_app")

if "JAVA_HOME" not in os.environ:
    os.environ["JAVA_HOME"] = settings.CURRENT_JAVA_HOME
    ontoui_logger.debug(f"JAVA_HOME not set. Setting it to {settings.CURRENT_JAVA_HOME}")

OBOP = Namespace("http://purl.org/net/obop/")


def read_model_files_from_directory(models_directory=None):
    """
    Reads the current list of inner model files (*.ttl files) in the models
    directory into json format.

    Defaults to settings.MODEL_DIRECTORY — the same directory the load and
    upload endpoints use — instead of a cwd-relative path, so the list and the
    load/upload surfaces can never disagree about where the models live.
    """
    models_info = []
    directory_path = str(models_directory or settings.MODEL_DIRECTORY)
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


def create_pellet_reasoning_graph(graph_world: World, cache_key: str) -> World:
    """Apply Pellet reasoning to a clone of the input world and return the result.

    ``cache_key`` is a stable hash of the original model RDF. The reasoned world is
    cached by it, so a repeat load of the same model skips the (10-25s) reasoner: a
    fresh World is reloaded from the cached serialization instead (inferences
    survive save->reload). Each caller gets its own World, so concurrent sessions
    never share one owlready store.
    """
    try:
        full_key = reasoned_world_cache.key("pellet", cache_key)

        def _build() -> bytes:
            # Miss: clone the input into a fresh world, reason into it, serialize.
            cloned_world = load_world(serialize_world(graph_world))
            with cloned_world:
                sync_reasoner_pellet(
                    cloned_world,
                    infer_property_values=True,
                    infer_data_property_values=True,
                )
            return serialize_world(cloned_world)

        data, cached = reasoned_world_cache.get_or_build(full_key, _build)
        ontoui_logger.info(
            "Pellet reasoning: cache %s (key %s)", "HIT" if cached else "MISS", cache_key[:12]
        )
        return load_world(data)
    except Exception as e:
        ontoui_logger.error(f"Error during clonning or Pellet reasoning: {e}")
        raise


def create_hermit_reasoning_graph(graph_world: World, cache_key: str) -> World:
    """Apply HermiT reasoning to a clone of the input world and return the result.

    Same caching strategy as create_pellet_reasoning_graph: the reasoned world is
    cached by the stable ``cache_key`` and reloaded per caller, so repeat loads skip
    the reasoner.
    """
    try:
        full_key = reasoned_world_cache.key("hermit", cache_key)

        def _build() -> bytes:
            cloned_world = load_world(serialize_world(graph_world))
            with cloned_world:
                sync_reasoner_hermit(cloned_world, infer_property_values=True)
            return serialize_world(cloned_world)

        data, cached = reasoned_world_cache.get_or_build(full_key, _build)
        ontoui_logger.info(
            "HermiT reasoning: cache %s (key %s)", "HIT" if cached else "MISS", cache_key[:12]
        )
        return load_world(data)
    except Exception as e:
        ontoui_logger.error(f"Error during clonning or Hermit reasoning: {e}")
        raise
