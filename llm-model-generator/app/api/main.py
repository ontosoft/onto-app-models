from fastapi import APIRouter

from app.api.routes import stream, login, private, users, utils, onto_app_router
from app.core.config import settings

api_router = APIRouter()
api_router.include_router(login.router)
api_router.include_router(users.router)
api_router.include_router(utils.router)
api_router.include_router(stream.router)
api_router.include_router(onto_app_router.router)

if settings.ENVIRONMENT == "local":
    api_router.include_router(private.router)

