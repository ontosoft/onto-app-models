import hashlib
import json
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from rdflib import RDF, Graph, Namespace, URIRef
from sqlmodel import func, or_, select

from app.api.deps import SessionDep, CurrentUser
from app.model_generator.builder import generate_model_graph
from app.model_generator.templates import OBOP
from app.models import (
    AppModel,
    AppModelPublic,
    AppModelsPublic,
    Message,
    ShapesDocument,
    ShapesDocumentCreate,
    ShapesDocumentPublic,
    ShapesDocumentUpdate,
    ShapesDocumentsPublic,
)

PROV = Namespace("http://www.w3.org/ns/prov#")

router = APIRouter(prefix="/shapes", tags=["shapes"])


@router.post("/", response_model=ShapesDocumentPublic)
def create_shapes_document(
    *, session: SessionDep, current_user: CurrentUser, shapes_in: ShapesDocumentCreate
) -> Any:
    """
    Upload a shapes document (SHACL Turtle for now).

    Dedupe is per user: if the SAME user uploads identical content (by
    sha256) again, their existing document is returned instead, so their FAM
    candidates keep grouping under one document. Different users may each
    keep their own copy of the same shapes - that is fine and intended.
    """
    # Reject content rdflib cannot parse - a broken document would fail
    # every later generation run anyway.
    try:
        Graph().parse(data=shapes_in.content, format="turtle")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid SHACL/Turtle: {str(e)}")

    content_hash = hashlib.sha256(shapes_in.content.encode("utf-8")).hexdigest()
    existing = session.exec(
        select(ShapesDocument)
        .where(ShapesDocument.owner_id == current_user.id)
        .where(ShapesDocument.content_hash == content_hash)
    ).first()
    if existing:
        return existing

    shapes = ShapesDocument.model_validate(
        shapes_in,
        update={"owner_id": current_user.id, "content_hash": content_hash},
    )
    session.add(shapes)
    session.commit()
    session.refresh(shapes)
    return shapes


@router.get("/", response_model=ShapesDocumentsPublic)
def read_shapes_documents(
    session: SessionDep, current_user: CurrentUser, skip: int = 0, limit: int = 100
) -> Any:
    """
    Retrieve shapes documents (own ones; superusers see all).
    """
    if current_user.is_superuser:
        count = session.exec(
            select(func.count()).select_from(ShapesDocument)
        ).one()
        statement = select(ShapesDocument).offset(skip).limit(limit)
    else:
        # Regular users see their own documents plus public ones.
        visible = or_(
            ShapesDocument.owner_id == current_user.id,
            ShapesDocument.is_public == True,  # noqa: E712 - SQL expression
        )
        count = session.exec(
            select(func.count()).select_from(ShapesDocument).where(visible)
        ).one()
        statement = (
            select(ShapesDocument).where(visible).offset(skip).limit(limit)
        )
    shapes = session.exec(statement).all()
    return ShapesDocumentsPublic(data=shapes, count=count)


def _get_visible_shapes_document(
    session: SessionDep, current_user: CurrentUser, id: uuid.UUID
) -> ShapesDocument:
    """Read access: the owner, superusers, and everyone for public shapes."""
    shapes = session.get(ShapesDocument, id)
    if not shapes:
        raise HTTPException(status_code=404, detail="Shapes document not found")
    if (
        not current_user.is_superuser
        and shapes.owner_id != current_user.id
        and not shapes.is_public
    ):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return shapes


def _get_owned_shapes_document(
    session: SessionDep, current_user: CurrentUser, id: uuid.UUID
) -> ShapesDocument:
    """Write access: the owner and superusers only - public grants reading."""
    shapes = session.get(ShapesDocument, id)
    if not shapes:
        raise HTTPException(status_code=404, detail="Shapes document not found")
    if not current_user.is_superuser and shapes.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return shapes


@router.get("/{id}", response_model=ShapesDocumentPublic)
def read_shapes_document(
    *, session: SessionDep, current_user: CurrentUser, id: uuid.UUID
) -> Any:
    """
    Get a shapes document by ID.
    """
    return _get_visible_shapes_document(session, current_user, id)


@router.get("/{id}/appmodels", response_model=AppModelsPublic)
def read_shapes_document_appmodels(
    *, session: SessionDep, current_user: CurrentUser, id: uuid.UUID
) -> Any:
    """
    List the FAM candidates generated from this shapes document.

    Follows the AppModel visibility rules: own and public candidates;
    superusers see all of them.
    """
    _get_visible_shapes_document(session, current_user, id)
    conditions = [AppModel.shapes_id == id]
    if not current_user.is_superuser:
        conditions.append(
            or_(
                AppModel.owner_id == current_user.id,
                AppModel.is_public == True,  # noqa: E712 - SQL expression
            )
        )
    count = session.exec(
        select(func.count()).select_from(AppModel).where(*conditions)
    ).one()
    candidates = session.exec(select(AppModel).where(*conditions)).all()
    return AppModelsPublic(data=candidates, count=count)


@router.post("/{id}/generate", response_model=AppModelPublic)
def generate_appmodel_from_shapes_document(
    *, session: SessionDep, current_user: CurrentUser, id: uuid.UUID
) -> Any:
    """
    Generate a FAM candidate from this shapes document (rule-based converter).

    The new AppModel belongs to the caller, records its provenance
    (shapes_id + generation_method) and carries a prov:wasDerivedFrom triple
    in the graph itself, so the origin survives a Turtle export.
    """
    shapes = _get_visible_shapes_document(session, current_user, id)
    if shapes.format != "shacl":
        raise HTTPException(
            status_code=422,
            detail=f"No converter registered for format '{shapes.format}'",
        )

    try:
        graph = generate_model_graph(shapes.content)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    # In-graph provenance; urn:uuid:<shapes_id> resolves to the DB row.
    model_node = next(graph.subjects(RDF.type, OBOP.Model), None)
    if model_node is not None:
        graph.add(
            (model_node, PROV.wasDerivedFrom, URIRef(f"urn:uuid:{shapes.id}"))
        )

    # Number the candidate within this document's existing ones.
    existing = session.exec(
        select(func.count()).select_from(AppModel).where(AppModel.shapes_id == id)
    ).one()
    app_model = AppModel(
        title=f"{shapes.name} (rule-based v{existing + 1})",
        description=f"Generated from shapes document '{shapes.name}'.",
        knowledge_graph_rdf=graph.serialize(format="turtle"),
        knowledge_graph_json=json.loads(graph.serialize(format="json-ld")),
        owner_id=current_user.id,
        shapes_id=shapes.id,
        generation_method="rule-based",
    )
    session.add(app_model)
    session.commit()
    session.refresh(app_model)
    return app_model


@router.delete("/{id}", response_model=Message)
def delete_shapes_document(
    *, session: SessionDep, current_user: CurrentUser, id: uuid.UUID
) -> Any:
    """
    Delete a shapes document. Generated models survive (their shapes_id
    becomes NULL via the FK's ON DELETE SET NULL).
    """
    shapes = _get_owned_shapes_document(session, current_user, id)
    session.delete(shapes)
    session.commit()
    return Message(message="Shapes document deleted successfully.")


@router.put("/{id}", response_model=ShapesDocumentPublic)
def update_shapes_document(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    id: uuid.UUID,
    shapes_in: ShapesDocumentUpdate,
) -> Any:
    """
    Update a shapes document - only its visibility, and only by superusers.
    The content stays immutable because candidates were generated from it.
    """
    shapes = _get_owned_shapes_document(session, current_user, id)
    data = shapes_in.model_dump(exclude_unset=True)
    if data.get("is_public") is None:
        data.pop("is_public", None)
    elif not current_user.is_superuser:
        raise HTTPException(
            status_code=403, detail="Only superusers can change shapes visibility"
        )
    shapes.sqlmodel_update(data)
    session.add(shapes)
    session.commit()
    session.refresh(shapes)
    return shapes
