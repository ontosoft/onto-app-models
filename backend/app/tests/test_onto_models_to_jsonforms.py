"""Translation-layer tests: hand-written FAM models -> JSONForms schemas.

These tests cover what the generator round-trip tests cannot: FAM features
written by hand that the SHACL generator does not emit — here a nested
HorizontalLayout holding a Submit/Cancel button pair inside the main
VerticalLayout. They call ``Form.create_functional_json_form_schemas``
directly on the loaded static model, which keeps them independent of the
process engine.

Why this works without a business process: loading only parses the RDF into
the static model (forms, layouts, buttons — *how the forms look*), and the
BBO process is needed first by ``run_application()``, where the ProcessEngine
walks it to decide *when* each form is shown. The running engine calls this
same translation method when a token reaches a UserTask, so the tests
exercise the identical code path, minus the scheduling.

Modernized 2026-11-10: the original module drove the pre-BBO engine
(``app.model_graph = ...``, ``message_type="form"``) and asserted a response
contract that no longer exists; its trivial single-/two-field cases are
covered by the generator tests today.
"""

from pathlib import Path

from app_engine.app_engine import AppEngine

FIXTURES = Path(__file__).parent / "test_models"
BASE = "http://example.org/logicinterface/testing/"


class _StubState:
    """Stands in for ApplicationState: the translation layer only writes the
    two mapping dicts (field IRI -> schema property name, picker options);
    everything else on the real state belongs to the running process."""

    def __init__(self) -> None:
        self.current_json_form_name_mapping: dict = {}
        self.current_json_form_picker_mapping: dict = {}


def _translate(fixture_name: str) -> tuple[dict, _StubState]:
    """Load a hand-written FAM fixture and translate its single form."""
    rdf = (FIXTURES / fixture_name).read_text(encoding="utf-8")
    engine = AppEngine()
    engine.load_inner_app_model(rdf_string=rdf, model_name=fixture_name)
    forms = engine.internal_app_static_model.forms
    assert len(forms) == 1
    state = _StubState()
    return forms[0].create_functional_json_form_schemas(state), state


def test_field_translation_and_name_mapping():
    """A Field becomes a schema property named after its label, and the
    element IRI -> property name mapping is recorded (the engine needs it
    to store submitted values under the right data property)."""
    json_form, state = _translate("test_submit_cancel_buttons.ttl")

    assert json_form["graph_node"] == f"{BASE}block_1"
    assert json_form["schema"] == {
        "type": "object",
        "properties": {"Field 1": {"type": "string", "position": 0}},
    }
    assert json_form["data"] == {}
    assert state.current_json_form_name_mapping == {f"{BASE}field_1": "Field 1"}


def test_nested_layout_with_submit_and_cancel_buttons():
    """The sublayout nests in document order below the Control, and the
    buttons carry their action pointers with the classified action type
    (obop:SubmitBlockAction -> submit, obop:CancelBlockAction -> cancel)."""
    json_form, _ = _translate("test_submit_cancel_buttons.ttl")

    assert json_form["uischema"] == {
        "type": "VerticalLayout",
        "elements": [
            {
                "type": "Control",
                "scope": "#/properties/Field 1",
                "label": "Field 1",
            },
            {
                "type": "HorizontalLayout",
                "elements": [
                    {
                        "type": "button",
                        "scope": "#/properties/Submit",
                        "label": "Submit",
                        "actions": [
                            {
                                "graph_node": f"{BASE}action_1",
                                "type": "submit",
                                "initiators": [],
                            }
                        ],
                    },
                    {
                        "type": "button",
                        "scope": "#/properties/Cancel",
                        "label": "Cancel",
                        "actions": [
                            {
                                "graph_node": f"{BASE}action_2",
                                "type": "cancel",
                                "initiators": [],
                            }
                        ],
                    },
                ],
            },
        ],
    }
