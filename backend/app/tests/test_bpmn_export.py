"""FAM -> BPMN 2.0 export (app/bpmn_export.py).

The export has two halves, and the tests cover both:

1. The SEMANTIC half - every BBO flow node/flow of the FAM must reappear as
   its BPMN element (subprocesses nested, conditions carried along), because
   a BPMN file that silently drops workflow steps would misrepresent the FAM.
2. The DIAGRAM half (BPMNDiagram/DI) - BPMN tools display nothing without
   explicit coordinates, so every element needs a shape or an edge, and the
   auto-layout must produce a drawable picture: children inside their
   subprocess bounds, no negative coordinates, waypoints on every edge.

The endpoint test runs against the real dev database like the other API
tests (docker compose db, top-level .env exported).
"""

import re
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path

from rdflib import Graph

from app.bpmn_export import fam_to_bpmn
from model_generator import builder

_NS = {
    "b": "http://www.omg.org/spec/BPMN/20100524/MODEL",
    "bpmndi": "http://www.omg.org/spec/BPMN/20100524/DI",
    "dc": "http://www.omg.org/spec/DD/20100524/DC",
    "di": "http://www.omg.org/spec/DD/20100524/DI",
}
_FLOW_NODE_TAGS = {
    "startEvent",
    "endEvent",
    "userTask",
    "scriptTask",
    "task",
    "exclusiveGateway",
    "subProcess",
}

_EXAMPLES = Path(__file__).parents[1] / "model_generator" / "examples"
_HAND_BUILT = Path(__file__).parents[2] / "app_models" / "restaurant-preprocessed.ttl"


def _export(graph: Graph) -> ET.Element:
    xml = fam_to_bpmn(graph, name="test")
    return ET.fromstring(xml)


def _flow_nodes(root: ET.Element) -> list[ET.Element]:
    return [e for e in root.iter() if e.tag.split("}")[1] in _FLOW_NODE_TAGS]


def _bounds(root: ET.Element) -> dict[str, tuple[float, float, float, float]]:
    """bpmnElement id -> (x, y, width, height) of its BPMNShape."""
    result = {}
    for shape in root.findall(".//bpmndi:BPMNShape", _NS):
        b = shape.find("dc:Bounds", _NS)
        result[shape.get("bpmnElement")] = tuple(
            float(b.get(k)) for k in ("x", "y", "width", "height")
        )
    return result


def _assert_complete_diagram(root: ET.Element) -> None:
    """Every semantic element must be drawable: one shape per flow node,
    one edge with at least two waypoints per sequence flow."""
    shapes = _bounds(root)
    for node in _flow_nodes(root):
        assert node.get("id") in shapes, f"no BPMNShape for {node.get('id')}"
    edges = {
        e.get("bpmnElement"): e.findall("di:waypoint", _NS)
        for e in root.findall(".//bpmndi:BPMNEdge", _NS)
    }
    for flow in root.findall(".//b:sequenceFlow", _NS):
        waypoints = edges.get(flow.get("id"))
        assert waypoints is not None, f"no BPMNEdge for {flow.get('id')}"
        assert len(waypoints) >= 2
    # a drawable picture starts inside the canvas
    for x, y, _w, _h in shapes.values():
        assert x >= 0 and y >= 0


def _assert_children_inside_subprocesses(root: ET.Element) -> None:
    """DI coordinates are absolute, so an expanded subprocess must spatially
    contain the shapes of its children - otherwise viewers draw the children
    outside their box."""
    shapes = _bounds(root)
    for sub in root.findall(".//b:subProcess", _NS):
        sx, sy, sw, sh = shapes[sub.get("id")]
        for child in sub:
            if child.tag.split("}")[1] not in _FLOW_NODE_TAGS:
                continue
            cx, cy, cw, ch = shapes[child.get("id")]
            assert sx <= cx and sy <= cy and cx + cw <= sx + sw and cy + ch <= sy + sh, (
                f"{child.get('id')} sticks out of {sub.get('id')}"
            )


def test_generated_model_exports_complete_bpmn() -> None:
    shapes_ttl = (_EXAMPLES / "string_form.shapes.ttl").read_text()
    graph = builder.generate_model_graph(shapes_ttl)
    root = _export(graph)

    # the workflow structure survives the translation
    process = root.find("b:process", _NS)
    assert process is not None and process.get("isExecutable") == "false"
    subs = root.findall(".//b:subProcess", _NS)
    assert len(subs) == 1  # one entity -> one insert subprocess
    # the subprocess children are NESTED in the XML (BPMN semantics),
    # among them the user task and the validation gateway of R9
    nested = {e.tag.split("}")[1] for e in subs[0]}
    assert {"startEvent", "userTask", "scriptTask", "exclusiveGateway"} <= nested

    # the conditional flows carry their routesOn trigger as the condition
    conditions = [
        c.text for c in root.findall(".//b:conditionExpression", _NS)
    ]
    assert any("submit_action" in c for c in conditions)
    assert any("FormValidationConforms" in c for c in conditions)

    _assert_complete_diagram(root)
    _assert_children_inside_subprocesses(root)


def test_hand_built_model_exports_complete_bpmn() -> None:
    """The exporter is not generator-specific: the hand-written restaurant
    model (4 subprocesses, 7 gateways, loops between subprocesses) must
    export just as completely."""
    graph = Graph().parse(_HAND_BUILT, format="turtle")
    root = _export(graph)
    assert len(root.findall(".//b:subProcess", _NS)) == 4
    assert len(_flow_nodes(root)) == 58  # every BBO flow node of the file
    _assert_complete_diagram(root)
    _assert_children_inside_subprocesses(root)


def test_model_without_process_is_rejected() -> None:
    graph = Graph()
    graph.parse(
        data="@prefix ex: <http://example.org/> . ex:a ex:b ex:c .",
        format="turtle",
    )
    try:
        fam_to_bpmn(graph)
        raise AssertionError("expected ValueError for a FAM without a process")
    except ValueError:
        pass


def test_bpmn_endpoint_serves_the_file() -> None:
    """GET /appmodels/{id}/bpmn returns the displayable file for a model the
    caller may read, and 404 for an unknown id."""
    from fastapi.testclient import TestClient

    from app.core.config import settings
    from main import app

    client = TestClient(app)
    response = client.post(
        f"{settings.API_V1_STR}/login/access-token",
        data={
            "username": settings.FIRST_SUPERUSER,
            "password": settings.FIRST_SUPERUSER_PASSWORD,
        },
    )
    assert response.status_code == 200, response.text
    headers = {"Authorization": f"Bearer {response.json()['access_token']}"}

    shapes_ttl = (_EXAMPLES / "string_form.shapes.ttl").read_text()
    generated = builder.generate_appmodel_from_shacl(shapes_ttl)
    created = client.post(
        f"{settings.API_V1_STR}/appmodels/",
        headers=headers,
        json={
            "title": f"bpmn-export-test-{uuid.uuid4().hex[:8]}",
            "knowledge_graph_rdf": generated.rdf,
        },
    )
    assert created.status_code == 200, created.text
    model_id = created.json()["id"]
    try:
        response = client.get(
            f"{settings.API_V1_STR}/appmodels/{model_id}/bpmn", headers=headers
        )
        assert response.status_code == 200, response.text
        assert response.headers["content-type"].startswith("application/xml")
        assert re.search(
            r'filename=".*\.bpmn"', response.headers["content-disposition"]
        )
        _assert_complete_diagram(ET.fromstring(response.text))

        missing = client.get(
            f"{settings.API_V1_STR}/appmodels/{uuid.uuid4()}/bpmn",
            headers=headers,
        )
        assert missing.status_code == 404
    finally:
        client.delete(
            f"{settings.API_V1_STR}/appmodels/{model_id}", headers=headers
        )
