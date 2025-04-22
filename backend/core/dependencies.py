# app/core/dependencies.py
from fastapi import Depends
from config.settings import get_settings

def get_settings_dep(settings=Depends(get_settings)):
    return settings