"""ShapesDocument upload, per-user dedupe and visibility.

No files are written in this test: MINIMAL_SHACL is an inline string sent
as the request's `content` field, and names like "person.shapes.ttl" are
just the display name stored in shapesdocument.name.

Runs against the local dev database, like the other tests here:

    cd backend/app && set -a && source ../../.env && set +a \
        && uv run python -m pytest tests/test_shapes.py
"""

import uuid

from fastapi.testclient import TestClient
from sqlmodel import Session

from main import app
from app import crud
from app.core.config import settings
from app.core.db import engine
from app.models import UserCreate

client = TestClient(app)

SHAPES_URL = f"{settings.API_V1_STR}/shapes"

# A tiny but real SHACL shape (one NodeShape, one property).
MINIMAL_SHACL = """
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix ex: <http://example.org/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

ex:PersonShape a sh:NodeShape ;
    sh:targetClass ex:Person ;
    sh:property [ sh:path ex:name ; sh:datatype xsd:string ] .
"""

POWER_USER_EMAIL = "power-user@example.com"
POWER_USER_PASSWORD = "powerpower123"


def auth_headers(email: str, password: str) -> dict[str, str]:
    response = client.post(
        f"{settings.API_V1_STR}/login/access-token",
        data={"username": email, "password": password},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def ensure_power_user() -> dict[str, str]:
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


def upload(headers: dict[str, str], name: str, content: str) -> dict:
    response = client.post(
        f"{SHAPES_URL}/",
        headers=headers,
        json={"name": name, "format": "shacl", "content": content},
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_upload_dedupe_and_visibility() -> None:
    superuser = auth_headers(
        settings.FIRST_SUPERUSER, settings.FIRST_SUPERUSER_PASSWORD
    )
    power_user = ensure_power_user()

    # Make the content unique per test run so reruns never collide with
    # leftovers from an aborted run.
    content = MINIMAL_SHACL + f"\n# run {uuid.uuid4()}\n"

    su_doc = power_doc = None
    try:
        su_doc = upload(superuser, "person.shapes.ttl", content)
        assert su_doc["format"] == "shacl"

        # Same user + same content -> the same document comes back.
        again = upload(superuser, "person-renamed.ttl", content)
        assert again["id"] == su_doc["id"]

        # Different user + same content -> an own, separate document.
        power_doc = upload(power_user, "person.shapes.ttl", content)
        assert power_doc["id"] != su_doc["id"]

        # The power user lists only their own document ...
        listed = client.get(f"{SHAPES_URL}/", headers=power_user).json()
        listed_ids = {d["id"] for d in listed["data"]}
        assert power_doc["id"] in listed_ids
        assert su_doc["id"] not in listed_ids

        # ... and cannot read the superuser's PRIVATE copy directly.
        response = client.get(f"{SHAPES_URL}/{su_doc['id']}", headers=power_user)
        assert response.status_code == 403

        # Once the superuser publishes it, the power user sees and reads it,
        # but may neither delete it nor change its visibility.
        response = client.put(
            f"{SHAPES_URL}/{su_doc['id']}",
            headers=superuser,
            json={"is_public": True},
        )
        assert response.status_code == 200, response.text
        assert response.json()["is_public"] is True
        listed_ids = {
            d["id"]
            for d in client.get(f"{SHAPES_URL}/", headers=power_user).json()["data"]
        }
        assert su_doc["id"] in listed_ids
        assert (
            client.get(f"{SHAPES_URL}/{su_doc['id']}", headers=power_user).status_code
            == 200
        )
        assert (
            client.delete(
                f"{SHAPES_URL}/{su_doc['id']}", headers=power_user
            ).status_code
            == 403
        )
        response = client.put(
            f"{SHAPES_URL}/{su_doc['id']}",
            headers=power_user,
            json={"is_public": False},
        )
        assert response.status_code == 403

        # No candidates exist yet for a fresh document.
        candidates = client.get(
            f"{SHAPES_URL}/{power_doc['id']}/appmodels", headers=power_user
        ).json()
        assert candidates["count"] == 0

        # Broken Turtle is rejected on upload.
        response = client.post(
            f"{SHAPES_URL}/",
            headers=power_user,
            json={"name": "broken.ttl", "format": "shacl", "content": "@prefix x"},
        )
        assert response.status_code == 400
    finally:
        for doc, headers in ((su_doc, superuser), (power_doc, power_user)):
            if doc is not None:
                client.delete(f"{SHAPES_URL}/{doc['id']}", headers=headers)


def test_generate_appmodel_from_shapes() -> None:
    power_user = ensure_power_user()
    content = MINIMAL_SHACL + f"\n# run {uuid.uuid4()}\n"
    doc = upload(power_user, "person.shapes.ttl", content)

    model = None
    try:
        response = client.post(
            f"{SHAPES_URL}/{doc['id']}/generate", headers=power_user
        )
        assert response.status_code == 200, response.text
        model = response.json()

        # Provenance is recorded in the row ...
        assert model["shapes_id"] == doc["id"]
        assert model["generation_method"] == "rule-based"
        assert model["is_public"] is False
        # ... and inside the graph itself (survives a Turtle export).
        assert "wasDerivedFrom" in model["knowledge_graph_rdf"]
        assert f"urn:uuid:{doc['id']}" in model["knowledge_graph_rdf"]

        # The candidate shows up under its shapes document.
        candidates = client.get(
            f"{SHAPES_URL}/{doc['id']}/appmodels", headers=power_user
        ).json()
        assert candidates["count"] == 1
        assert candidates["data"][0]["id"] == model["id"]

        # The generated model actually runs in the engine: the real load+start
        # path (static model factory -> ProcessEngine), i.e. validator level
        # V4 - the generator's output is engine-runnable, not just valid RDF.
        response = client.post(
            f"{settings.API_V1_STR}/appmodels/run/{model['id']}",
            headers={**power_user, "X-Onto-Session": f"test-{uuid.uuid4()}"},
        )
        assert response.status_code == 200, response.text
    finally:
        if model is not None:
            client.delete(
                f"{settings.API_V1_STR}/appmodels/{model['id']}",
                headers=power_user,
            )
        client.delete(f"{SHAPES_URL}/{doc['id']}", headers=power_user)
