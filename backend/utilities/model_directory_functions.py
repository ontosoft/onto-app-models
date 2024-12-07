import os
import json
import logging
from rdflib import Graph, RDF, Namespace
from rdflib.plugins.sparql import  prepareQuery

ontoui_logger = logging.getLogger("ontoui_app")

OBOP = Namespace("http://purl.org/net/obop/")

def read_model_files_from_directory(models_directory: str = 'app_models'):
    """
    Reads the current list of inner model files (*.ttl files) in the folder 'app_models' into
    json format. 
    """
    models_info = []  
    directory_path = os.getcwd() + '/' + models_directory  
    ontoui_logger.debug('Directory: %s', directory_path) 
    for filename in os.listdir(directory_path):
        if filename.endswith('.ttl'):
            filepath = os.path.join(directory_path, filename)
            # Check if the file is a file and not a directory
            if os.path.isfile(filepath):
                ontoui_logger.debug('File: %s', filename)
                graph = Graph().parse(filepath, format="ttl")
                graph.bind("obop", OBOP)  # Bind the namespace prefix for use in the SPARQL query
                q = prepareQuery( """
                    SELECT ?model ?description WHERE {
                        ?model a obop:Model.
                        ?model obop:modelDescription ?description.
                    }   
                """  , initNs={'obop': OBOP})

                query_result = graph.query(q) #
                if len(query_result) == 0: 
                    ontoui_logger.debug('The file is not a valid UI model file. It has to contain exactly one obop:Model instance.')
                elif len(query_result) > 1:
                    ontoui_logger.debug(f'The UI model file {filename} has more obop:Model instances.' )
                    for row in query_result:
                        ontoui_logger.debug(row)
                else:
                    query_result_list =list(query_result)
                    model, description = query_result_list[0]
                    ontoui_logger.debug('Model: %s', model)
                    ontoui_logger.debug('Description: %s', description) 
                    models_info.append({
                            "filename": filename,
                            "model": str(model),
                            "description": str(description),
                            "filepath": filepath
                        })
    models_info_json = json.dumps(models_info)
    ontoui_logger.debug('Model description: %s', models_info_json)
    return models_info_json