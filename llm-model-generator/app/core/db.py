import json
import logging
import uuid
from pathlib import Path

from rdflib import Graph
from sqlmodel import Session, create_engine, select

from app import crud
from app.core.config import settings
from app.models import AppModel, User, UserCreate

logger = logging.getLogger(__name__)

engine = create_engine(str(settings.SQLALCHEMY_DATABASE_URI))


# make sure all SQLModel models are imported (app.models) before initializing DB
# otherwise, SQLModel might fail to initialize relationships properly
# for more details: https://github.com/fastapi/full-stack-fastapi-template/issues/28


# Repo-level example models (llm-model-generator/app_models), shipped in the image.
EXAMPLE_MODELS_DIR = Path(__file__).resolve().parents[2] / "app_models"

# Demo models seeded only in local/dev. Each entry: (title, description, filename).
EXAMPLE_APPMODELS: list[tuple[str, str, str]] = [
    (
        "Enter String Form",
        "Single input field with submit/cancel buttons.",
        "enter-string-form.ttl",
    ),
    (
        "Submit / Cancel Buttons",
        "Minimal form demonstrating submit and cancel actions.",
        "submit-cancel-buttons.ttl",
    ),
    (
        "Complete Restaurant",
        "Larger restaurant data-entry model.",
        "complete_restaurant.ttl",
    ),
]


def _rdf_to_jsonld(rdf_str: str) -> object:
    """Parse Turtle and serialize to a JSON-LD python object.

    Mirrors the API's convert_rdf_to_jsonld, but without the FastAPI
    HTTPException coupling (this runs at startup, not in a request) and
    without importing the route module (which would create an import cycle:
    db -> appmodels -> deps -> db).
    """
    g = Graph()
    g.parse(data=rdf_str, format="turtle")
    return json.loads(g.serialize(format="json-ld"))


def seed_example_appmodels(session: Session, owner_id: uuid.UUID) -> None:
    """Idempotently seed a few known-good example AppModels (local/dev only).

    Honors the dual-write invariant: both knowledge_graph_rdf and
    knowledge_graph_json are populated. Existing rows (matched by title) are
    left untouched, so restarts don't create duplicates.
    """
    created = 0
    for title, description, filename in EXAMPLE_APPMODELS:
        existing = session.exec(
            select(AppModel).where(AppModel.title == title)
        ).first()
        if existing:
            continue

        path = EXAMPLE_MODELS_DIR / filename
        if not path.is_file():
            logger.warning("Example model file not found, skipping: %s", path)
            continue

        rdf_str = path.read_text(encoding="utf-8")
        try:
            jsonld = _rdf_to_jsonld(rdf_str)
        except Exception:  # noqa: BLE001 - bad example must not break startup
            logger.exception("Failed to convert example model %s; skipping", filename)
            continue

        session.add(
            AppModel(
                title=title,
                description=description,
                knowledge_graph_rdf=rdf_str,
                knowledge_graph_json=jsonld,
                owner_id=owner_id,
            )
        )
        created += 1

    if created:
        session.commit()
        logger.info("Seeded %d example app model(s).", created)


def init_db(session: Session) -> None:
    # Tables should be created with Alembic migrations
    # But if you don't want to use migrations, create
    # the tables un-commenting the next lines
    # from sqlmodel import SQLModel

    # This works because the models are already imported and registered from app.models
    #SQLModel.metadata.create_all(engine)

    user = session.exec(
        select(User).where(User.email == settings.FIRST_SUPERUSER)
    ).first()
    if not user:
        user_in = UserCreate(
            email=settings.FIRST_SUPERUSER,
            password=settings.FIRST_SUPERUSER_PASSWORD,
            is_superuser=True,
        )
        user = crud.create_user(session=session, user_create=user_in)

    # Demo data only in local/dev; never in staging/production.
    if settings.ENVIRONMENT == "local":
        seed_example_appmodels(session, owner_id=user.id)
