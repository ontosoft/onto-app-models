
from pydantic_settings import BaseSettings
import os
from functools import lru_cache

class Settings(BaseSettings):
    APP_NAME: str = "Onto-UI Application Generator"
    DEBUG: bool = "false"
    TEMPORARY_MODELS_DIRECTORY: str = "./temporary_models"
    ENV: str 
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

class DevelopmentSettings(BaseSettings):
    APP_NAME: str = "Onto-UI Application Generator"
    DEBUG: bool = True
    TEMPORARY_MODELS_DIRECTORY: str = "./temporary_models"
    MODEL_DIRECTORY: str = "./app_models"
    ONTOLOGIES_DIRECTORY: str = "./ontologies"

class TestingSettings(BaseSettings):
    APP_NAME: str = "Onto-UI Application Generator - Testing"
    DEBUG: bool = True 
    TEMPORARY_MODELS_DIRECTORY: str = "./temporary_models" 
    MODEL_DIRECTORY: str = "./tests/test_models"
    ONTOLOGIES_DIRECTORY: str = "./ontologies"

#@lru_cache()
def get_settings()-> Settings:
    env = os.getenv("ENV","development")
    if env == "testing":
        return TestingSettings()
    else:
        return DevelopmentSettings()

