from pathlib import Path
from pydantic_settings import BaseSettings
import os
from functools import lru_cache



class Settings(BaseSettings):
    APP_NAME: str = "Onto-UI Application Generator"
    DEBUG: bool = "false"
    # Define the base directory as the project root
    BASE_DIR : Path= Path(__file__).resolve().parent.parent

    TEMPORARY_MODELS_DIRECTORY: Path = BASE_DIR /"temporary_models"
    ENV: str 
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

class DevelopmentSettings(BaseSettings):
    APP_NAME: str = "Onto-UI Application Generator"
    DEBUG: bool = True
    BASE_DIR :Path= Path(__file__).resolve().parent.parent
    TEMPORARY_MODELS_DIRECTORY : Path = BASE_DIR /"temporary_models"
    MODEL_DIRECTORY : Path = BASE_DIR/"app_models"
    ONTOLOGIES_DIRECTORY: Path = BASE_DIR/"ontologies"

class TestingSettings(BaseSettings):
    APP_NAME: str = "Onto-UI Application Generator - Testing"
    DEBUG: bool = True 
    BASE_DIR : Path = Path(__file__).resolve().parent.parent
    TEMPORARY_MODELS_DIRECTORY: Path = BASE_DIR /"temporary_models"
    MODEL_DIRECTORY: Path = BASE_DIR/"tests/test_models"
    ONTOLOGIES_DIRECTORY: Path = BASE_DIR/"ontologies"



#@lru_cache()
def get_settings()-> Settings:
    env = os.getenv("ENV","development")
    if env == "testing":
        return TestingSettings()
    else:
        return DevelopmentSettings()

