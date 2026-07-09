import uuid
import json
from typing import Any
from rdflib import Graph

from fastapi import APIRouter, HTTPException, Header
from sqlmodel import func, select

from app.core.session_service import engine_sessions, DEFAULT_SESSION
from app.api.deps import SessionDep, CurrentUser
from app.models import AppModel, AppModelCreate, AppModelPublic, AppModelsPublic, AppModelUpdate, Message

router = APIRouter(prefix="/appmodels", tags=["appmodels"])

def convert_rdf_to_jsonld(rdf_str: str, rdf_format: str = "turtle") -> Any:
    g = Graph()
    try:
        # 1. Validation & Parsing
        g.parse(data=rdf_str, format=rdf_format)
        # 2. Conversion: Serialize to JSON-LD string then load as python object
        jsonld_str = g.serialize(format="json-ld")
        return json.loads(jsonld_str)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid RDF data: {str(e)}")

@router.get("/", response_model=AppModelsPublic)
def read_app_models(
    session: SessionDep, current_user: CurrentUser, skip: int = 0, limit: int = 100
) -> Any:
    """
    Retrieve app models.
    """
    if current_user.is_superuser:
        count_statement = select(func.count()).select_from(AppModel)
        count = session.exec(count_statement).one()
        statement = select(AppModel).offset(skip).limit(limit)
        app_models = session.exec(statement).all()
    else:
        count_statement = (
            select(func.count())
            .select_from(AppModel)
            .where(AppModel.owner_id == current_user.id)
        )
        count = session.exec(count_statement).one()
        statement = (
            select(AppModel)
            .where(AppModel.owner_id == current_user.id)
            .offset(skip)
            .limit(limit)
        )
        app_models = session.exec(statement).all()
    return AppModelsPublic(data=app_models, count=count)

@router.get("/{id}", response_model=AppModelPublic)
def read_app_model(
    *, session: SessionDep, current_user: CurrentUser, id: uuid.UUID
) -> Any:
    """
    Get app model by ID.
    """
    app_model = session.get(AppModel, id)
    if not app_model:
        raise HTTPException(status_code=404, detail="App model not found")
    if not current_user.is_superuser and app_model.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return app_model

@router.post("/", response_model=AppModelPublic)
def create_app_model(
    *, session: SessionDep, current_user: CurrentUser, app_model_in: AppModelCreate
) -> Any:
    """
    Create new app model.
    """

    # Process RDF content
    app_model_data = app_model_in.model_dump()
    
    knowledge_graph_json_data = convert_rdf_to_jsonld(app_model_in.knowledge_graph_rdf)
    
    # Add converted JSON-LD to the data for the new model
    app_model_data["knowledge_graph_json"] = knowledge_graph_json_data
    app_model = AppModel.model_validate(app_model_data, update={"owner_id": current_user.id})
    
    session.add(app_model)
    session.commit()
    session.refresh(app_model)
    return app_model
    
@router.put("/{id}", response_model=AppModelPublic)
def update_app_model(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    id: uuid.UUID,
    app_model_in: AppModelUpdate,
) -> Any:   
    """
    Update an app model.
    """
    app_model = session.get(AppModel, id)
    if not app_model:
        raise HTTPException(status_code=404, detail="App model not found")
    if not current_user.is_superuser and app_model.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    # Update the JSON-LD  field based on the new RDF input
    app_model_data = app_model_in.model_dump()
    app_model.knowledge_graph_json = convert_rdf_to_jsonld(app_model_in.knowledge_graph_rdf)
        
    app_model.sqlmodel_update(app_model_data)
    session.add(app_model)
    session.commit()
    session.refresh(app_model)
    return app_model


@router.delete("/{id}", response_model=Message)
def delete_app_model(   
    *, session: SessionDep, current_user: CurrentUser, id: uuid.UUID
) -> Any:
    """
    Delete an app model.
    """
    app_model = session.get(AppModel, id)
    if not app_model:
        raise HTTPException(status_code=404, detail="App model not found")
    if not current_user.is_superuser and app_model.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    session.delete(app_model)
    session.commit()
    return Message(message="App model deleted successfully.")

@router.post("/run/{id}", response_model=Message)
def run_app_model(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    id: uuid.UUID,
    onto_session: str = Header(default=DEFAULT_SESSION, alias="X-Onto-Session"),
) -> Any:
    """
    Run an app model in the caller's engine session (X-Onto-Session header).
    """
    app_model = session.get(AppModel, id)
    if not app_model:
        raise HTTPException(status_code=404, detail="App model not found")
    if not current_user.is_superuser and app_model.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    try:
        # Load + run this model in its own session engine. A fresh session id
        # gets a clean engine; a reused one is reset() first (see run_model).
        engine_sessions.run_model(
            onto_session, rdf_string=app_model.knowledge_graph_rdf
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to run application: {str(e)}")

    return Message(message=f"App model '{app_model.title}' run successfully.")