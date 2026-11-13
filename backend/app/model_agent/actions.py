"""The edit-action vocabulary: what the design agent is allowed to say.

The schema below is the whole interface between the LLM and the model: it is
passed to Ollama as the ``format`` parameter, so constrained decoding
guarantees every reply parses into an :class:`EditAction`. The action names
are exactly the v1 operations of ``model_generator.editing.EditSession``,
plus ``inspect`` (re-read the current model summary) and ``done`` (hand the
candidate to the checkers). Typed parameters are used instead of a generic
string-to-string ``args`` object: small local models are markedly more
reliable when every key has its own type and description to condition on
(same experience as the tester's ``ACTION_SCHEMA``).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

#: JSON schema for Ollama's ``format`` parameter. Ollama uses it for
#: constrained decoding: every sampled token must keep the output parseable
#: as an instance of this schema, so the reply is always well-formed JSON
#: with a known shape. The per-key ``description`` texts double as inline
#: documentation for the model - they are part of what it conditions on.
EDIT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "reasoning": {
            "type": "string",
            "description": "One short sentence: why this operation.",
        },
        "action": {
            "type": "string",
            "enum": [
                "reorder_field",
                "group_fields",
                "move_entity",
                "set_loop",
                "add_relation",
                "remove_relation",
                "inspect",
                "done",
            ],
        },
        "field": {
            "type": "string",
            "description": "reorder_field only: the field label exactly as shown.",
        },
        "position": {
            "type": "integer",
            "description": "reorder_field/move_entity: the target position, 0-based.",
        },
        "fields": {
            "type": "array",
            "items": {"type": "string"},
            "description": "group_fields only: two or more field labels of "
            "the SAME form, to be rendered side by side in one row.",
        },
        "entity": {
            "type": "string",
            "description": "move_entity/set_loop: the form (entity) name.",
        },
        "looped": {
            "type": "boolean",
            "description": "set_loop only: true shows an 'Add another ...' "
            "button on the form, false removes it.",
        },
        "source": {
            "type": "string",
            "description": "add_relation/remove_relation: the form whose "
            "instance stores the link.",
        },
        "target": {
            "type": "string",
            "description": "add_relation only: the form whose instance is linked to.",
        },
        "property_iri": {
            "type": "string",
            "description": "add_relation/remove_relation: the absolute IRI "
            "of the object property that stores the link.",
        },
        "multiple": {
            "type": "boolean",
            "description": "add_relation only: true if one source instance "
            "links many target instances (makes the target form loop).",
        },
        "rationale": {
            "type": "string",
            "description": "done only: why the design is good now.",
        },
    },
    # "reasoning" is required on purpose: forcing the model to verbalise a
    # justification before the operation improves small-model reliability
    # and gives the transcript an explanation for every step.
    "required": ["action", "reasoning"],
}


@dataclass
class EditAction:
    """One decision of the design agent - the Python mirror of EDIT_SCHEMA.

    Only the keys that belong to the chosen ``action`` are meaningful; the
    rest stay ``None``. The environment validates the meaningful ones and
    answers with a corrective outcome text instead of raising, so a confused
    agent gets a chance to recover on the next step.
    """

    action: str
    reasoning: str = ""
    field: str | None = None
    position: int | None = None
    fields: list[str] | None = None
    entity: str | None = None
    looped: bool | None = None
    source: str | None = None
    target: str | None = None
    property_iri: str | None = None
    multiple: bool | None = None
    rationale: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EditAction:
        """Build an action from parsed model output, tolerating missing keys.

        Constrained decoding guarantees well-formed JSON but not sensible
        content - a model may still omit keys or pick nonsense values. This
        constructor therefore never raises: wrong types are coerced where
        harmless and dropped to ``None`` where not, and the environment
        answers a nonsensical action with a corrective outcome text instead
        of an exception, so one bad reply never kills the whole run.
        """
        # The schema says integer, but a model may still emit "2" (string)
        # or something unusable; coerce if possible, else let the
        # environment complain about the missing position.
        position = data.get("position")
        try:
            position = int(position) if position is not None else None
        except (TypeError, ValueError):
            position = None
        # Same idea for the field list: accept any list by stringifying its
        # items, treat anything else (e.g. a single string) as absent.
        fields = data.get("fields")
        return cls(
            action=str(data.get("action", "")),
            reasoning=str(data.get("reasoning", "")),
            field=data.get("field"),
            position=position,
            fields=[str(f) for f in fields] if isinstance(fields, list) else None,
            entity=data.get("entity"),
            looped=data.get("looped"),
            source=data.get("source"),
            target=data.get("target"),
            property_iri=data.get("property_iri"),
            multiple=data.get("multiple"),
            rationale=data.get("rationale"),
        )

    def describe(self) -> str:
        """One human-readable line for this action. Three consumers:

        1. The step prompt's history ("step 0: group fields ... -> ok"):
           each LLM call is self-contained, so past actions reach the model
           as these lines, not as raw JSON.
        2. The loop's repeat guard compares consecutive ``describe()``
           strings to detect a stuck agent - which is why the parameters
           must be part of the text: two reorders of DIFFERENT fields must
           not count as a repetition.
        3. ``Transcript.to_dict()`` records this line per step in the run
           reports and logs.
        """
        if self.action == "reorder_field":
            return f'move field "{self.field}" to position {self.position}'
        if self.action == "group_fields":
            names = ", ".join(f'"{name}"' for name in (self.fields or []))
            return f"group fields {names or '(none)'} into one row"
        if self.action == "move_entity":
            return f'move form "{self.entity}" to position {self.position}'
        if self.action == "set_loop":
            state = "on" if self.looped else "off"
            return f'turn the loop of form "{self.entity}" {state}'
        if self.action == "add_relation":
            many = " (multiple)" if self.multiple else ""
            return (
                f'connect "{self.source}" -> "{self.target}" '
                f"via {self.property_iri}{many}"
            )
        if self.action == "remove_relation":
            return f'remove relation {self.property_iri} from "{self.source}"'
        if self.action == "inspect":
            return "inspect the current model"
        if self.action == "done":
            return f"done: {self.rationale or '(no rationale)'}"
        return f"unknown action '{self.action}'"
