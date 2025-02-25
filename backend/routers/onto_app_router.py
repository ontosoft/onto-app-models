from fastapi import APIRouter, UploadFile, File, Request
from pathlib import Path
from owlprocessor.app import App
from utilities.model_directory_functions import read_model_files_from_directory
import logging
import json
import jsonpickle

logger = logging.getLogger('ontoui_app')
router = APIRouter()
app:App =  None 

i = 0

@router.post("/upload_rdf_file", response_description="Upload new model file")
async def upload_model_file(file: UploadFile = File(...)):
    """
    Uploads a new model file and reads it into the inner application model.   
    """
    filecontent = await file.read()
    try:
        local_model = App()
        local_model.readGraph(filecontent)
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
    i += 1 
    global app
    logger.debug(f"This is the {i} th time the function is run.")
    if app is not None and app.isInnerAppModelLoaded and app.localAppInteractionModelInstance is not None:
        logger.info(f"Process generator exists { app.localAppInteractionModelInstance}")
        return {"message": "The applicaton was already run before.",
                "model": app.localAppInteractionModelInstance}
        #jsonpickle.encode(
    elif app is not None and app.isInnerAppModelLoaded and app.localAppInteractionModelInstance is None:
        # The inner model reporesentation corresponding to the RDF graph
        # was already loaded. However, the application is still not running because
        # (localAppInteractionModelInstance is not created)
        app.runApplication()
        return {"message_type": "information",
                "message_content": "The application is running."}
    elif app is None:
        return {"message_type": "information",
                 "message_content" : "No model loaded. Load an application model first."}

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
async def read_current_app_data_from_model():
    """
    Reading the data from the the interactive model (e.g. UI page) and 
    returns it in the json format to the frontend. This method is called after 
    processing the data sent from the frontend and both methods are used to 
    make data exchange between the frontend and the backend.
    """
    return app.readNewModelLayout()
 
    
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
    if app is not None and app.isInnerAppModelLoaded:
        logger.debug(f"The app model \"{app.modelName} \" was already loaded.") 
        return {"message": f"The model {app.modelName} is loaded . The applicaton was already run before. Do you want to load a new model?"}
    else:
        logger.debug(f"The app model \"{filename} \" is about to be loaded.") 
        modelsLocation = Path("./app_models")
        modelsLocation.mkdir(parents=True, exist_ok=True)
        filePath = modelsLocation.joinpath(filename)
        app = App()
        app.readGraph(filePath)
        app.loadInnerAppModel()
        return {"message": f"The model is loaded {app.modelName}. "}
     
