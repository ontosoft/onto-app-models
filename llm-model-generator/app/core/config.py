import secrets
from typing import Any, Annotated, Literal
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing_extensions import Self
from pathlib import Path
from typing import ClassVar
import warnings
import os

from pydantic import (
    AnyUrl, 
    BeforeValidator,
    HttpUrl,
    PostgresDsn,
    computed_field,
    EmailStr,
    model_validator
)

def parse_cors(v: Any) -> list[str] | str:
    if isinstance(v, str) and not v.startswith("["):
        return [i.strip() for i in v.split(",") if i.strip()]
    elif isinstance(v, list | str):
        return v
    raise ValueError(v)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # Use top level .env file (one level above ./llm-model-generator/)
        env_file="../.env",
        env_ignore_empty=True,
        extra="ignore",
        env_file_encoding="utf-8"
    )
    APP_NAME: str = "LLM Model Generator"
    PROJECT_NAME: str
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = secrets.token_urlsafe(32)
    # 60 minutes * 24 hours * 8 days = 8 days
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8
    FRONTEND_HOST: str = "http://localhost:5173"
    ENVIRONMENT: Literal["local", "staging", "production"] = "local"

    BACKEND_CORS_ORIGINS: Annotated[
        list[AnyUrl] | str, BeforeValidator(parse_cors)
    ] = []

    @computed_field  # type: ignore[prop-decorator]
    @property
    def all_cors_origins(self) -> list[str]:
        return [str(origin).rstrip("/") for origin in self.BACKEND_CORS_ORIGINS] + [
            self.FRONTEND_HOST
        ]
    SENTRY_DSN: HttpUrl | None = None
    POSTGRES_SERVER: str
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str = ""
    POSTGRES_DB: str = ""

    @computed_field  # type: ignore[prop-decorator]k
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> PostgresDsn:
        return PostgresDsn.build(
            scheme="postgresql+psycopg",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_SERVER,
            port=self.POSTGRES_PORT,
            path=self.POSTGRES_DB,
        )
    SMTP_TLS: bool = True
    SMTP_SSL: bool = False
    SMTP_PORT: int = 587
    SMTP_HOST: str | None = None
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    EMAILS_FROM_EMAIL: EmailStr | None = None
    EMAILS_FROM_NAME: str | None = None

    @model_validator(mode="after")
    def _set_default_emails_from(self) -> Self:
        if not self.EMAILS_FROM_NAME:
            self.EMAILS_FROM_NAME = self.PROJECT_NAME
        return self

    EMAIL_RESET_TOKEN_EXPIRE_HOURS: int = 48

    @computed_field  # type: ignore[prop-decorator]
    @property
    def emails_enabled(self) -> bool:
        return bool(self.SMTP_HOST and self.EMAILS_FROM_EMAIL)

    EMAIL_TEST_USER: EmailStr = "test@example.com"
    FIRST_SUPERUSER: EmailStr
    FIRST_SUPERUSER_PASSWORD: str

    def _check_default_secret(self, var_name: str, value: str | None) -> None:
        if value == "changethis":
            message = (
                f'The value of {var_name} is "changethis", '
                "for security, please change it, at least for deployments."
            )
            if self.ENVIRONMENT == "local":
                warnings.warn(message, stacklevel=1)
            else:
                raise ValueError(message)

    @model_validator(mode="after")
    def _enforce_non_default_secrets(self) -> Self:
        self._check_default_secret("SECRET_KEY", self.SECRET_KEY)
        self._check_default_secret("POSTGRES_PASSWORD", self.POSTGRES_PASSWORD)
        self._check_default_secret(
            "FIRST_SUPERUSER_PASSWORD", self.FIRST_SUPERUSER_PASSWORD
        )

        return self



    NEO4J_URI: str
    NEO4J_USERNAME: str
    NEO4J_PASSWORD: str

    OPENAI_API_KEY: str

    # --- Engine transport (Stage 2b) ---
    # "local": run engines in this process (default; local dev / tests / single
    # container). "redis": forward per-session engine ops to an engine_worker
    # container over Redis (crash isolation + horizontal scaling).
    ENGINE_TRANSPORT: Literal["local", "redis"] = "local"
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    # Seconds the API waits for a worker's RPC reply before giving up. A cold
    # model load runs the Java reasoner (Pellet+HermiT), which can take ~60-90s in
    # a CPU-throttled container; keep this comfortably above that. Repeat loads hit
    # the reasoned-world cache and are fast. Override via env for slower/faster hosts.
    ENGINE_RPC_TIMEOUT: int = 180
    # Threads per worker -> how many sessions one worker serves concurrently.
    ENGINE_WORKER_CONCURRENCY: int = 4

    @computed_field  # type: ignore[prop-decorator]
    @property
    def REDIS_URL(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    debug: bool = True
    BASE_DIR :Path= Path(__file__).resolve().parent.parent

    TEMPORARY_MODELS_DIRECTORY : ClassVar[Path] = BASE_DIR /"temporary_models"
    # app_models sits at the package root (llm-model-generator/app_models), one
    # level ABOVE app/ — unlike ontologies/ and temporary_models/, which live
    # under app/. BASE_DIR/"app_models" pointed at the non-existent
    # app/app_models, breaking load_inner_uimodel_from_server (FileNotFoundError
    # on the _shacl_shape companion) and sending uploads where the list endpoint
    # never looks.
    MODEL_DIRECTORY : ClassVar[Path] = BASE_DIR.parent/"app_models"
    ONTOLOGIES_DIRECTORY: ClassVar[Path] = BASE_DIR/"ontologies"
    CURRENT_JAVA_HOME: ClassVar[str] = os.getenv("JAVA_HOME", "/Library/Java/JavaVirtualMachines/adoptopenjdk-13.jdk/Contents/Home/")



settings = Settings()