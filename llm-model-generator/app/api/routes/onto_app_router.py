from fastapi import APIRouter, UploadFile, File, Request, Header
from fastapi import Query
from fastapi.concurrency import run_in_threadpool
from app.core.config import settings
from pathlib import Path
from app.owlprocessor.app_engine import AppEngine
from app.owlprocessor.app_model_factory import AppStaticModelFactory
from app.utilities.model_directory_functions import read_model_files_from_directory
from app.contracts.engine import AppExchangeGetOutput
from app.core.session_service import engine_sessions, DEFAULT_SESSION
import logging

logger = logging.getLogger('ontoui_app')
router = APIRouter(prefix="/generator", tags=["onto_model_generator"])

# The runtime engine is no longer a module-level global (that made the backend
# single-tenant). Each request carries an X-Onto-Session header and resolves its
# own AppEngine through engine_sessions. See app/core/session_service.py.

@router.post("/upload_rdf_file", response_description="Upload new model file", )
async def upload_model_file(file: UploadFile = File(...)):
    """
    Uploads a new model file and reads it into the inner application model.   
    """
    filecontent = await file.read()
    try:
        local_model = AppEngine()
        local_model = AppStaticModelFactory.rdf_graf_to_uimodel(filecontent)
        if local_model is None:
            return {"The file is not a valid UI model": "The file is not a valid UI model"}
    except Exception as e:
        return {"The file is not a valid UI model": str(e)}

    modelsLocation : Path = settings.MODEL_DIRECTORY
    modelsLocation.mkdir(parents=True, exist_ok=True)
    filePath = modelsLocation/ file.filename
    with open(filePath, "w", encoding='utf-8') as f:
        f.write(filecontent)
    return {"filename": file.filename}

@router.get("/run_application", response_description="Run the application")
async def run_application(
    session: str = Header(default=DEFAULT_SESSION, alias="X-Onto-Session"),
):
    """
    Runs the application by creating a ProcessEngine for this session.
    If the session's model is already running, reports that instead.
    """
    status = await run_in_threadpool(engine_sessions.status, session)
    if status["running"]:
        logger.info("The application was already run before for this session.")
        return {"message": "The applicaton was already run before."}
    elif status["loaded"]:
        # The static model corresponding to the RDF graph is loaded for this
        # session but not yet running. Start it.
        logger.info(f"Running the application with the model {status['model_name']}")
        await run_in_threadpool(engine_sessions.run, session)
        return {"message_type": "information",
                "layout_type": "",
                "message_content": "The application is running."}
    else:
        return {"message_type": "information",
                 "message_content" : "No model loaded. Load an application model first."}



@router.get("/stop_application", response_description="Shut down the running application")
async def stop_application(
    session: str = Header(default=DEFAULT_SESSION, alias="X-Onto-Session"),
):
    """
    This function stops the application for this session if it is running.
    """
    logger.info("Stopping the application for this session")
    await run_in_threadpool(engine_sessions.stop, session)
    return {"message_type": "information",
             "message_content" : "No model is loaded. The application was shut down."}


@router.post("/app_exchange_post", response_description="Process the data sent from the frontend")
async def process_data_sent_from_frontend(
    request: Request,
    session: str = Header(default=DEFAULT_SESSION, alias="X-Onto-Session"),
):
    """
    Receiving the current data form the frontend (e.g. UI page). This method is called
    before reading the data from the interactive model and then is used the method
    app_exchange_get are used to complete data exchange between the frontend and the backend.
    """
    # The data sent from the frontend is in the json format
    frontend_state = await request.json()

    return await run_in_threadpool(engine_sessions.post, session, frontend_state)

@router.get("/app_exchange_get", response_description="Get current UI page")
async def read_current_app_data_from_model(
    session: str = Header(default=DEFAULT_SESSION, alias="X-Onto-Session"),
) -> AppExchangeGetOutput:
    """
    Reading the data from the the interactive model (e.g. UI page) and
    returns it in the json format to the frontend. This route is called after
    processing the data sent from the frontend and both methods are used to
    make data exchange between the frontend and the backend.
    """
    return await run_in_threadpool(engine_sessions.get, session)
 
    
@router.get("/read_inner_server_models", response_description="Get current list of inner UI models on the server") 
async def read_the_list_of_app_models():
    """
    Reads the current list of inner model files in the folder 'app_models' into
    json format. 
    """
    logger.debug('Reading the list of inner UI models from the server')
    return read_model_files_from_directory() 

@router.get("/load_inner_uimodel_from_server",  response_description="Load the chosen app model on the server")
async def load_inner_server_model(
    filename: str,
    force_load: bool | None = Query(default=None, description="Force reload the model"),
    session: str = Header(default=DEFAULT_SESSION, alias="X-Onto-Session"),
):
    """
    Load the chosen inner UI model from the server into this session's engine.

    Args:
        filename (str): The name of the UI model file to be loaded.
        This file is stored in the 'app_models' folder as RDF file
    """
    status = await run_in_threadpool(engine_sessions.status, session)
    if force_load is not None and force_load:
        logger.debug(f"The app model \"{filename} \" is about to be loaded by force.")
        await run_in_threadpool(engine_sessions.load, session, file_name=filename)
        loaded = await run_in_threadpool(engine_sessions.status, session)
        return {"message": f"The model is loaded {loaded['model_name']} by force."}
    elif status["loaded"]:
        logger.debug(f"The app model \"{status['model_name']} \" was already loaded.")
        return {"message": f"The model {status['model_name']} is loaded . The applicaton was already run before. Do you want to load a new model?"}
    else:
        # If the model is not loaded, load it even if it is not forced
        try:
            logger.debug(f"The app model \"{filename} \" is about to be loaded.")
            await run_in_threadpool(engine_sessions.load, session, file_name=filename)
            loaded = await run_in_threadpool(engine_sessions.status, session)
            return {"message": f"The model is loaded {loaded['model_name']}. "}
        except Exception as e:
            logger.error(f"Error loading the model {filename}: {e}")
            return {"message": f"Error loading the model {filename}: {e}"}