"""Design-loop contract: scripted edits -> checker cascade -> confirmation.

The LLM is replaced by scripted deciders (CI needs no Ollama), so these
tests pin the loop's four properties: a sensible edit sequence ends in a
CONFIRMED model through the REAL checker cascade; agent mistakes become
corrective feedback instead of crashes; a red checker triggers a repair
round whose report reaches the next observation; and the repair budget
caps an unfixable candidate.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.model_agent import EDIT_SCHEMA, EditAction, agentic_generate

EXAMPLES = Path(__file__).parent.parent / "model_generator" / "examples"


def _restaurant_shapes() -> str:
    return (EXAMPLES / "restaurant.shapes.ttl").read_text(encoding="utf-8")


class ScriptedDecider:
    """Replay a fixed action list; repeat the last one when exhausted
    (an exhausted script keeps answering 'done', like a satisfied agent)."""

    def __init__(self, actions: list[dict[str, Any]]) -> None:
        self._actions = actions
        self._index = 0
        #: The schema handed in per step - lets tests pin the loop's
        #: dynamic/static schema contract.
        self.schemas: list[dict[str, Any] | None] = []

    def __call__(
        self,
        system_prompt: str,
        user_prompt: str,
        schema: dict[str, Any] | None = None,
    ) -> tuple[EditAction, int]:
        self.schemas.append(schema)
        data = self._actions[min(self._index, len(self._actions) - 1)]
        self._index += 1
        return EditAction.from_dict(data), 0


def _stub_green(fam_ttl: str, shapes_ttl: str) -> tuple[bool, str]:
    return True, "stub: green"


def test_scripted_design_run_is_confirmed_by_the_real_checkers() -> None:
    """Green path end to end: group Price+Description, then done - through
    the REAL cascade (Pellet consistency + both scripted engine runs)."""
    decide = ScriptedDecider(
        [
            {
                "action": "group_fields",
                "fields": ["Price", "Description"],
                "reasoning": "price and description describe the same dish",
            },
            {"action": "done", "rationale": "grouped, rest is fine"},
        ]
    )
    result = agentic_generate(_restaurant_shapes(), decide)

    assert result.confirmed, result.transcript.reason
    assert result.model is not None
    assert "dish_row_0" in result.model.rdf
    assert result.repair_rounds == 0
    assert result.transcript.verdict == "pass"
    assert len(result.transcript.steps) == 2
    # Every checker of the single 'done' attempt went green.
    assert all(entry["passed"] for entry in result.checker_reports[0])


def test_agent_mistakes_become_feedback_not_crashes() -> None:
    """An unknown field and an unknown action are answered with corrective
    outcome texts; the session survives and the run still confirms."""
    decide = ScriptedDecider(
        [
            {"action": "reorder_field", "field": "No such field", "position": 0},
            {"action": "make_coffee"},
            {"action": "reorder_field", "field": "Dish name"},  # missing position
            {"action": "done", "rationale": "giving up on edits"},
        ]
    )
    result = agentic_generate(_restaurant_shapes(), decide, checkers=(_stub_green,))

    outcomes = [step.outcome for step in result.transcript.steps]
    assert "no field named" in outcomes[0]
    assert "unknown action" in outcomes[1]
    assert "needs 'field' and 'position'" in outcomes[2]
    assert result.confirmed


def test_red_checker_feeds_repair_round() -> None:
    """A checker that rejects the first 'done' puts its report into the
    next observation; the second 'done' then confirms."""
    calls = {"n": 0}

    def red_then_green(fam_ttl: str, shapes_ttl: str) -> tuple[bool, str]:
        calls["n"] += 1
        if calls["n"] == 1:
            return False, "synthetic-red: the first candidate is rejected"
        return True, "green now"

    decide = ScriptedDecider(
        [
            {"action": "done", "rationale": "first try"},
            {"action": "done", "rationale": "second try"},
        ]
    )
    result = agentic_generate(_restaurant_shapes(), decide, checkers=(red_then_green,))

    assert result.repair_rounds == 1
    assert result.confirmed
    # The red report reached the agent as repair feedback.
    second_observation = result.transcript.steps[1].observation
    assert "REPAIR FEEDBACK" in second_observation
    assert "synthetic-red" in second_observation
    assert len(result.checker_reports) == 2


def test_repair_budget_caps_an_unfixable_candidate() -> None:
    def always_red(fam_ttl: str, shapes_ttl: str) -> tuple[bool, str]:
        return False, "synthetic-red: never good enough"

    decide = ScriptedDecider([{"action": "done", "rationale": "try"}])
    result = agentic_generate(
        _restaurant_shapes(),
        decide,
        checkers=(always_red,),
        max_repair_rounds=2,
    )

    assert not result.confirmed
    assert result.model is None
    assert result.repair_rounds == 2
    assert result.transcript.verdict == "fail"
    assert not result.transcript.aborted
    assert "repair budget" in result.transcript.reason


def test_edit_action_schema_and_describe() -> None:
    """from_dict tolerates junk; describe carries the parameters (the loop's
    repeat guard compares these strings); the schema enum names exactly the
    actions the environment dispatches."""
    empty = EditAction.from_dict({})
    assert empty.action == ""
    assert "unknown action" in empty.describe()

    coerced = EditAction.from_dict(
        {"action": "reorder_field", "field": "Price", "position": "2"}
    )
    assert coerced.position == 2
    assert 'move field "Price" to position 2' == coerced.describe()

    grouped = EditAction.from_dict(
        {"action": "group_fields", "fields": ["Price", "Description"]}
    )
    assert 'group fields "Price", "Description" into one row' == grouped.describe()

    assert set(EDIT_SCHEMA["properties"]["action"]["enum"]) == {
        "reorder_field",
        "group_fields",
        "move_entity",
        "set_loop",
        "add_relation",
        "remove_relation",
        "inspect",
        "done",
    }


def test_dynamic_schema_tracks_the_session_state() -> None:
    """The per-step schema enumerates exactly the names that currently
    exist, follows mutations, and leaves the static EDIT_SCHEMA untouched;
    the static ablation condition hands the constant to the decider."""
    from app.model_agent.environment import EditEnv
    from app.model_generator.editing import EditSession

    shapes = _restaurant_shapes()
    session = EditSession.from_shacl(shapes)
    env = EditEnv(session, shapes)

    schema = env.edit_schema()
    props = schema["properties"]
    names = [ent.iri_token for ent in session.entities]
    labels = [prop.label for ent in session.entities for prop in ent.properties]
    assert props["entity"]["enum"] == names
    assert props["source"]["enum"] == names
    assert props["target"]["enum"] == names
    assert props["field"]["enum"] == labels
    assert props["fields"]["items"]["enum"] == labels
    assert "Price" in labels
    assert props["position"]["minimum"] == 0
    assert props["position"]["maximum"] >= 1
    # The static base schema must stay enum-free (the ablation baseline).
    assert "enum" not in EDIT_SCHEMA["properties"]["field"]

    # A mutation is reflected in the next build.
    session.move_entity(names[-1], 0)
    assert env.edit_schema()["properties"]["entity"]["enum"][0] == names[-1]

    # The loop hands the chosen condition to the decider.
    dynamic = ScriptedDecider([{"action": "done", "rationale": "ok"}])
    agentic_generate(shapes, dynamic, checkers=(_stub_green,))
    assert "enum" in dynamic.schemas[0]["properties"]["entity"]  # type: ignore[index]

    static = ScriptedDecider([{"action": "done", "rationale": "ok"}])
    agentic_generate(shapes, static, checkers=(_stub_green,), dynamic_schema=False)
    assert static.schemas[0] is EDIT_SCHEMA
