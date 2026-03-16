import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from sqlmodel import func, select

from app.api.deps import SessionDep, CurrentUser
from app.models import AppModel, AppModelCreate, AppModelPublic, AppModelsPublic, AppModelUpdate, Message

router = APIRouter(prefix="/appmodels", tags=["appmodels"])

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
    app_model = AppModel.model_validate(app_model_in, update={"owner_id": current_user.id})
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
    app_model_data = app_model_in.model_dump(exclude_unset=True)
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

