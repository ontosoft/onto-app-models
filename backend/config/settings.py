from pathlib import Path
from pydantic_settings import BaseSettings
import os
from typing import ClassVar



class Settings(BaseSettings):
    app_name: str = "Onto-UI Application Generator"
    debug: bool = "false"
    # Define the base directory as the project root
    base_dir : Path= Path(__file__).resolve().parent.parent

    TEMPORARY_MODELS_DIRECTORY: Path = base_dir /"temporary_models"
    #HERMIT_PATH = BASE_DIR /"reasoners/org.semanticweb.HermiT.jar"
    CURREN_JAVA_HOME: ClassVar[Path] = os.getenv("JAVA_HOME","/Library/Java/JavaVirtualMachines/adoptopenjdk-13.jdk/Contents/Home/")
    ENV: str 
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

class DevelopmentSettings(BaseSettings):
    app_name: str = "Onto-UI Application Generator"
    debug: bool = True
    BASE_DIR :Path= Path(__file__).resolve().parent.parent

    TEMPORARY_MODELS_DIRECTORY : ClassVar[Path] = BASE_DIR /"temporary_models"
    MODEL_DIRECTORY : ClassVar[Path] = BASE_DIR/"app_models"
    ONTOLOGIES_DIRECTORY: ClassVar[Path] = BASE_DIR/"ontologies"

class TestingSettings(BaseSettings):
    APP_NAME: str = "Onto-UI Application Generator - Testing"
    DEBUG: bool = True 
    BASE_DIR : Path = Path(__file__).resolve().parent.parent

    TEMPORARY_MODELS_DIRECTORY: ClassVar[Path] = BASE_DIR /"temporary_models"
    MODEL_DIRECTORY: ClassVar[Path] = BASE_DIR/"tests/test_models"
    ONTOLOGIES_DIRECTORY: ClassVar[Path] = BASE_DIR/"ontologies"



#@lru_cache()
def get_settings()-> Settings:
    env = os.getenv("ENV","development")
    if env == "testing":
        return TestingSettings()
    else:
        return DevelopmentSettings()

