from fastapi import APIRouter, UploadFile, File, Request
from pathlib import Path
from owlprocessor.app_engine import AppEngine
from utilities.model_directory_functions import read_model_files_from_directory
from owlprocessor.communication import AppExchangeGetOutput
import logging

logger = logging.getLogger('ontoui_app')
router = APIRouter()

app:AppEngine = AppEngine()

#TODO App havy logic with dependency injection in FastAPI 
i = 0

@router.post("/upload_rdf_file", response_description="Upload new model file")
async def upload_model_file(file: UploadFile = File(...)):
    """
    Uploads a new model file and reads it into the inner application model.   
    """
    filecontent = await file.read()
    try:
        local_model = AppEngine()
        local_model.read_graph(filecontent)
        local_model.loadUIModel()
    except Exception as e:
        return {"The file is not a valid UI model": str(e)}

    modelsLocation = Path("./app_models")
    modelsLocation.mkdir(parents=True, exist_ok=True)
    filePath = modelsLocation/ file.filename
    with open(filePath, "wb") as f:
        f.write(filecontent)
    return {"filename": file.filename}

@router.get("/run_application", response_description="Run the application")
async def run_application():
    """
    Runs the application and generates the first layout.
    If the application was already run before, it returns a message 
    that the application was already run.

    """
    global i
    global app
    i += 1 

    logger.debug(f"This is the {i} th time the function is run.")
    if app is not None and app.is_inner_app_static_model_loaded and app.app_interaction_model_instance is not None:
        logger.info(f"Process generator exists { app.app_interaction_model_instance}")
        return {"message": "The applicaton was already run before.",
                "model": app.app_interaction_model_instance}
        #jsonpickle.encode(
    elif app is not None and app.is_inner_app_static_model_loaded and app.app_interaction_model_instance is None:
        # The inner model static reporesentation corresponding to the RDF graph
        # was already loaded. However, the application is still not running because
        # (AppInteractionModelInstance is not created)
        app.run_application()
        return {"message_type": "information",
                "message_content": "The application is running."}
    elif app is None:
        return {"message_type": "information",
                 "message_content" : "No model loaded. Load an application model first."}



@router.get("/stop_application", response_description="Shut down the running application")
async def stop_application():
    """
    This function stops the application if it is already running.

    """
    global app

    if app is not None: 
        logger.info(f"Stopping the application")
        del app
        app = None
        return {"message_type": "information",
                 "message_content" : "No model is loaded. The application was shut down."}


@router.post("/app_exchange_post", response_description="Process the data sent from the frontend") 
async def process_data_sent_from_frontend(request: Request):
    """
    Receiving the current data form the frontend (e.g. UI page). This method is called
    before reading the data from the interactive model and both methods are used to
    make data exchange between the frontend and the backend. 
    """
    # The data sent from the frontend is in the json format
    frontend_state = await request.json()

    return app.processReceivedClientData(frontend_state)

@router.get("/app_exchange_get", response_description="Get current UI page") 
async def read_current_app_data_from_model() -> AppExchangeGetOutput:
    """
    Reading the data from the the interactive model (e.g. UI page) and 
    returns it in the json format to the frontend. This method is called after 
    processing the data sent from the frontend and both methods are used to 
    make data exchange between the frontend and the backend.
    """
    return app.read_new_model_layout()
 
    
@router.get("/read_inner_server_models", response_description="Get current list of inner UI models on the server") 
async def read_the_list_of_app_models():
    """
    Reads the current list of inner model files in the folder 'app_models' into
    json format. 
    """
    return read_model_files_from_directory() 

@router.get("/load_inner_uimodel_from_server",  response_description="Load the chosen inner UI model from the server")
async def load_inner_server_model(filename: str):
    """
    Load the chosen inner UI model from the server.

    Args:
        filename (str): The name of the UI model file to be loaded.
        This file is stored in the 'app_models' folder as RDF file
    """
    global app
    if app is not None and app.is_inner_app_static_model_loaded:
        logger.debug(f"The app model \"{app.model_name} \" was already loaded.") 
        return {"message": f"The model {app.model_name} is loaded . The applicaton was already run before. Do you want to load a new model?"}
    else:
        logger.debug(f"The app model \"{filename} \" is about to be loaded.") 
        app = AppEngine(config="development")
        app.read_graph(filename)
        app.load_inner_app_model()
        return {"message": f"The model is loaded {app.model_name}. "}
     
