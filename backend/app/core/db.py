import hashlib
import json
import logging
import uuid
from pathlib import Path

from rdflib import Graph
from sqlmodel import Session, create_engine, select

from app import crud
from app.core.config import settings
from app.models import AppModel, ShapesDocument, User, UserCreate

logger = logging.getLogger(__name__)

engine = create_engine(str(settings.SQLALCHEMY_DATABASE_URI))


# make sure all SQLModel models are imported (app.models) before initializing DB
# otherwise, SQLModel might fail to initialize relationships properly
# for more details: https://github.com/fastapi/full-stack-fastapi-template/issues/28


# Repo-level example models (backend/app_models), shipped in the image.
EXAMPLE_MODELS_DIR = Path(__file__).resolve().parents[2] / "app_models"

# Repo example models, seeded as public in every environment so all users
# can see and run them. Each entry: (title, description, filename).
# (enter-string-form_shacl_shape.ttl is a validation sidecar, not a model.)
EXAMPLE_APPMODELS: list[tuple[str, str, str]] = [
    (
        "Enter String Form",
        "Single input field with submit/cancel buttons.",
        "enter-string-form.ttl",
    ),
    (
        "Complete Restaurant",
        "Larger restaurant data-entry model.",
        "restaurant-preprocessed.ttl",
    ),
    (
        "Restaurant (SHACL)",
        "Restaurant model driven by SHACL shapes.",
        "restaurant-shacl.ttl",
    ),
    (
        "Restaurant (SHACL, explicit bnodes)",
        "SHACL restaurant variant with explicitly named blank nodes.",
        "restaurant-shacl_explicite-bnodes.ttl",
    ),
    (
        "Restaurant (nested bnodes)",
        "Restaurant variant with blank nodes defined through nesting.",
        "restaurant_model_ttl_with_bnodes_defined_with_nesting.ttl",
    ),
]


# Example shapes shipped with the rule-based generator; seeded into the
# Shapes page so "Generate" can be tried right away. (name, filename).
EXAMPLE_SHAPES_DIR = Path(__file__).resolve().parents[1] / "model_generator" / "examples"
EXAMPLE_SHAPES: list[tuple[str, str]] = [
    ("string_form.shapes.ttl", "string_form.shapes.ttl"),
    ("restaurant.shapes.ttl", "restaurant.shapes.ttl"),
]


def seed_example_shapes(session: Session, owner_id: uuid.UUID) -> None:
    """Idempotently seed the generator's example shapes documents.

    Uses the same per-owner content-hash dedupe as the upload route, so
    restarts never create duplicates.
    """
    created = 0
    for name, filename in EXAMPLE_SHAPES:
        path = EXAMPLE_SHAPES_DIR / filename
        if not path.is_file():
            logger.warning("Example shapes file not found, skipping: %s", path)
            continue
        content = path.read_text(encoding="utf-8")
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        existing = session.exec(
            select(ShapesDocument)
            .where(ShapesDocument.owner_id == owner_id)
            .where(ShapesDocument.content_hash == content_hash)
        ).first()
        if existing:
            # Rows seeded before the is_public flag stay private otherwise.
            if not existing.is_public:
                existing.is_public = True
                session.add(existing)
                created += 1
            continue
        session.add(
            ShapesDocument(
                name=name,
                format="shacl",
                content=content,
                content_hash=content_hash,
                owner_id=owner_id,
                is_public=True,
            )
        )
        created += 1

    if created:
        session.commit()
        logger.info("Seeded %d example shapes document(s).", created)


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
    """Idempotently seed the repo's example AppModels as public.

    Honors the dual-write invariant: both knowledge_graph_rdf and
    knowledge_graph_json are populated. Existing rows (matched by title) are
    left untouched, so restarts don't create duplicates.
    """
    created = 0
    updated = 0
    for title, description, filename in EXAMPLE_APPMODELS:
        existing = session.exec(
            select(AppModel).where(AppModel.title == title)
        ).first()
        if existing:
            # Rows seeded before the is_public flag existed stay private
            # otherwise; examples are meant to be visible to everyone.
            if not existing.is_public:
                existing.is_public = True
                session.add(existing)
                updated += 1
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
                is_public=True,
            )
        )
        created += 1

    if created or updated:
        session.commit()
        logger.info(
            "Seeded %d example app model(s), marked %d public.", created, updated
        )


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

    # The repo examples are reference models for every environment; they are
    # seeded as public so non-superusers see them too. Idempotent by title.
    seed_example_appmodels(session, owner_id=user.id)
    # The generator's example shapes are seeded as public as well, so every
    # user can try "Generate" right away.
    seed_example_shapes(session, owner_id=user.id)
