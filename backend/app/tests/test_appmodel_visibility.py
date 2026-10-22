"""Visibility rules for AppModels.

A model with is_public=True is listable, readable and runnable by every
authenticated user. Everything else stays restricted: editing, deleting and
changing the visibility flag are allowed only for the owner or a superuser.

Like the other tests in this directory, this file runs against the local dev
database (docker compose db) and must be started from backend/app with the
top-level .env exported, e.g.:

    cd backend/app && set -a && source ../../.env && set +a \
        && uv run python -m pytest tests/test_appmodel_visibility.py
"""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from main import app
from app import crud
from app.core.config import settings
from app.core.db import engine
from app.models import UserCreate

# TestClient calls the FastAPI app in-process: no server needs to run, but
# the routes still use the real database via their normal dependencies.
client = TestClient(app)

# settings.API_V1_STR is "/api/v1" (app/core/config.py) - the prefix under
# which main.py mounts all routers. Built from the setting so the test
# follows along if the prefix ever changes.
APPMODELS_URL = f"{settings.API_V1_STR}/appmodels"

# Smallest possible valid Turtle graph: one triple. Enough for the create
# and update routes, whose only RDF requirement is that rdflib can parse it
# (they convert it to JSON-LD for the dual-write invariant).
MINIMAL_RDF = "@prefix ex: <http://example.org/> . ex:a ex:b ex:c ."

# The "power user": a regular, non-superuser account. Created on first test
# run and reused afterwards (the password only matters for logging in here).
POWER_USER_EMAIL = "power-user@example.com"
POWER_USER_PASSWORD = "powerpower123"


def auth_headers(email: str, password: str) -> dict[str, str]:
    """Log in via the real OAuth2 endpoint and return the Bearer header.

    /login/access-token expects form fields named username/password (OAuth2
    convention), not JSON.
    """
    response = client.post(
        f"{settings.API_V1_STR}/login/access-token",
        data={"username": email, "password": password},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def ensure_power_user() -> dict[str, str]:
    """Create the regular test user directly in the DB (idempotent), log in.

    Created via crud instead of the API because user creation over the API
    would itself require superuser credentials - not what this test is about.
    """
    with Session(engine) as session:
        user = crud.get_user_by_email(session=session, email=POWER_USER_EMAIL)
        if not user:
            crud.create_user(
                session=session,
                user_create=UserCreate(
                    email=POWER_USER_EMAIL, password=POWER_USER_PASSWORD
                ),
            )
    return auth_headers(POWER_USER_EMAIL, POWER_USER_PASSWORD)


def create_model(headers: dict[str, str], title: str) -> dict:
    """POST a minimal AppModel as the given user and return the response body."""
    response = client.post(
        f"{APPMODELS_URL}/",
        headers=headers,
        json={"title": title, "knowledge_graph_rdf": MINIMAL_RDF},
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_public_model_visible_to_power_user() -> None:
    # The superuser from .env (FIRST_SUPERUSER) owns the fixtures; the power
    # user is the one whose point of view we are testing.
    superuser = auth_headers(
        settings.FIRST_SUPERUSER, settings.FIRST_SUPERUSER_PASSWORD
    )
    power_user = ensure_power_user()

    # Two superuser-owned models with random titles (so reruns never collide
    # with leftovers): one stays private, one gets published.
    private = create_model(superuser, f"private-{uuid.uuid4()}")
    public = create_model(superuser, f"public-{uuid.uuid4()}")
    try:
        # Create must not accept a visibility flag: new models start private.
        assert private["is_public"] is False

        # Publish one model. Only the superuser may flip is_public; the
        # update route requires knowledge_graph_rdf in every PUT body.
        response = client.put(
            f"{APPMODELS_URL}/{public['id']}",
            headers=superuser,
            json={"knowledge_graph_rdf": MINIMAL_RDF, "is_public": True},
        )
        assert response.status_code == 200, response.text
        assert response.json()["is_public"] is True

        # Listing as power user: the public model appears, the private one
        # must not leak (it belongs to the superuser).
        listed = client.get(f"{APPMODELS_URL}/", headers=power_user).json()
        listed_ids = {model["id"] for model in listed["data"]}
        assert public["id"] in listed_ids
        assert private["id"] not in listed_ids

        # Direct reads by id follow the same rule: public 200, foreign
        # private 403.
        response = client.get(
            f"{APPMODELS_URL}/{public['id']}", headers=power_user
        )
        assert response.status_code == 200
        response = client.get(
            f"{APPMODELS_URL}/{private['id']}", headers=power_user
        )
        assert response.status_code == 403

        # "Public" grants read/run only: the power user may neither edit the
        # foreign model nor change its visibility.
        response = client.put(
            f"{APPMODELS_URL}/{public['id']}",
            headers=power_user,
            json={"knowledge_graph_rdf": MINIMAL_RDF, "is_public": False},
        )
        assert response.status_code == 403

        # Regression guard for exclude_unset: an ordinary update that does
        # not mention is_public must keep the flag as it is - with a plain
        # model_dump() the unset field would arrive as None and crash or
        # reset the column.
        response = client.put(
            f"{APPMODELS_URL}/{public['id']}",
            headers=superuser,
            json={"knowledge_graph_rdf": MINIMAL_RDF, "title": public["title"]},
        )
        assert response.status_code == 200
        assert response.json()["is_public"] is True
    finally:
        # Clean up so repeated runs don't accumulate fixture rows.
        for model in (private, public):
            client.delete(
                f"{APPMODELS_URL}/{model['id']}", headers=superuser
            )


def test_power_user_can_run_public_example() -> None:
    """End-to-end: a power user starts a seeded public example model.

    Uses the 'Enter String Form' example that db.py seeds as public in
    local/dev. run/{id} loads the model's RDF into an engine session, so this
    also exercises the engine with a real ontology-backed model.
    """
    power_user = ensure_power_user()
    listed = client.get(f"{APPMODELS_URL}/", headers=power_user).json()
    example = next(
        (m for m in listed["data"] if m["title"] == "Enter String Form"), None
    )
    if example is None:
        pytest.skip("Example models are not seeded in this database")
    assert example["is_public"] is True

    # A fresh X-Onto-Session id gives the run its own isolated engine.
    response = client.post(
        f"{APPMODELS_URL}/run/{example['id']}",
        headers={**power_user, "X-Onto-Session": f"test-{uuid.uuid4()}"},
    )
    assert response.status_code == 200, response.text
