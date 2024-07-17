from fastapi import APIRouter, UploadFile, File
from pathlib import Path
from app_modelling.ontomodel import ApplicationModel
from utilities.model_directory_functions import read_model_files_from_directory
import logging

logger = logging.getLogger('ontoui_app')
router = APIRouter()
model:ApplicationModel =  None 


@router.post("/upload_rdf_file", response_description="Upload new model file")
async def upload_model_file(file: UploadFile = File(...)):
    """
    Uploads a new model file and reads it into the inner application model.   
    """
    filecontent = await file.read()
    try:
        local_model = ApplicationModel()
        local_model.readGraph(filecontent)
        local_model.loadUIModel()
    except Exception as e:
        return {"The file is not a valid UI model": str(e)}

    modelsLocation = Path("./uimodels")
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
    if model.processGenerator is not None:
        print(f"Process generator exists { model.processGenerator}")
        return {"message": "The applicaton was already run before."}
    else:
        model.runApplication()
        return model.readNewModelLayout()

@router.get("/get_current_ui_page", response_description="Get current UI page") 
async def read_current_ui_page_from_model():
    """
    Reads the current UI page from the model and returns it in the
    json format. 
    """
    return model.readNewModelLayout()
    
@router.get("/read_inner_server_models", response_description="Get current list of inner UI models on the server") 
async def read_the_list_of_ui_models():
    """
    Reads the current list of inner model files in the folder 'uimodels' into
    json format. 
    """
    return read_model_files_from_directory() 

@router.get("/load_inner_uimodel_from_server",  response_description="Load the chosen inner UI model from the server")
async def load_inner_server_model(filename: str):
    """
    Load the chosen inner UI model from the server.

    Args:
        filename (str): The name of the UI model file to be loaded.
        This file should be in the 'uimodels' folder.
    """
    global model
    if model is not None and model.modelLoaded:
        logger.debug(f"The model is loaded {model.modelName} was already loaded.") 
        return {"message": f"The model is loaded {model.modelName}. The applicaton was already run before. Do you want to load a new model?"}
    else:
        modelsLocation = Path("./uimodels")
        modelsLocation.mkdir(parents=True, exist_ok=True)
        filePath = modelsLocation/ filename
        model = ApplicationModel()
        model.readGraph(filePath)
        model.loadUIModel()
        return {"message": f"The model is loaded {model.modelName}. "}
     
