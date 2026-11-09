"""Protocol-level environment: the agent plays the frontend's role in-process.

Why this exists
---------------
The real frontend talks to a running model through a small JSON protocol
(``/app_exchange_post`` / ``/app_exchange_get``): the engine sends *pages* —
either a JSONForms layout (schema + uischema + data) or a notification — and
the frontend answers with *action messages* built by ``buildActionMessage`` in
``frontend/src/lib/ontoRunnerApi.ts``. Everything a user can do in the
generated app passes through this protocol, so an agent that speaks it
faithfully can test the model's complete behaviour — forms, validation,
gateways, loops, termination — without HTTP, database or browser. That is
what stage 1 of the model tester does, directly against an in-process
:class:`AppEngine`.

The two translations
--------------------
This class translates in both directions, and the translation defines what
the agent can and cannot know:

* **Page -> observation** (:meth:`observe`). The JSON the engine would send
  to the frontend is rendered as plain text, for example::

      PAGE TYPE: form
      FIELDS:
        - "Restaurant name" (string, required) = <empty>
        - "Address" (string) = "Main street 1"
      BUTTONS:
        - "Submit" [submit]
      APPLICATION FINISHED: no

  Schema properties become fields (with constraints and the currently
  entered value), uischema button elements become buttons (with their action
  type), Label elements and notification payloads become MESSAGE lines. The
  RDF graph nodes stay hidden on purpose: the agent sees only what a user
  would see on a rendered screen, which keeps this observation comparable to
  the stage-2 browser observation (an accessibility snapshot).

* **Action -> message** (:meth:`apply`). A *click* is looked up among the
  page's buttons and translated into the identical ``message_content`` the
  frontend would send for that button's action pointer — e.g. for a submit::

      {"action_type": "submit",
       "action_graph_node": "<the action the button fires>",
       "form_graph_node":   "<the form being submitted>",
       "form_data":         {"Restaurant name": "Acme", ...}}

  A *fill* never reaches the engine: exactly like typing in the browser, it
  only mutates the local ``form_data``, which travels as one piece when a
  submit button is clicked.

The execution trace
-------------------
As a by-product the environment records what actually happened, in the
model's own vocabulary (:class:`TraceStep`): which forms were presented,
which model actions were performed, and which engine decisions the run
revealed. The engine never names its decisions over the protocol, but they
are observable from the outside: a submit that brings the *same form* back
means the per-form SHACL validation decided ``obop:FormValidationViolation``;
a submit that moves on means ``obop:FormValidationConforms``.
``reasoning.check_trace_consistency`` later asserts this trace as an ABox
into the model graph and lets Pellet judge whether the observed run is
DL-consistent with the model and the OBOP axioms (e.g. the disjointness of
``obop:Action`` and ``obop:EngineDecision``).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from rdflib import Namespace

from app.app_engine.app_engine import AppEngine
from app.contracts.engine import AppExchangeGetOutput

logger = logging.getLogger("ontoui_app")

OBOP = Namespace("http://purl.org/net/obop/")

#: Keys of a JSON-Schema property that are layout metadata, not user-facing
#: constraints ("position" orders the fields, "type" is shown separately).
#: Everything else (pattern, minLength, maxLength, enum, ...) is a constraint
#: the agent must respect and therefore appears in the observation.
_NON_CONSTRAINT_KEYS = {"type", "position"}


@dataclass
class TraceStep:
    """One observed event of the run, expressed in model vocabulary.

    ``kind`` is one of:

    - ``form_presented``    — ``node`` is the obop block (form) that was shown
      to the agent.
    - ``action_performed``  — ``node`` is the model action a clicked button
      fired (the button's ``action_graph_node``).
    - ``decision_observed`` — ``node`` is the engine decision the run revealed
      (``obop:FormValidationConforms`` / ``obop:FormValidationViolation``).

    The trace deliberately stores IRIs as plain strings: it is evidence about
    the run, collected without interpreting the model. Interpretation happens
    once, in the DL oracle, where each kind is asserted with the matching OBOP
    class and the reasoner draws the conclusions.
    """

    kind: str
    node: str


class ProtocolEnv:
    """Drive one model run through the AppEngine exchange loop.

    The constructor performs the same startup sequence as the frontend's
    AppRunner component: load the model into a fresh engine, start the
    process engine, send ``initiate_exchange``, and fetch the first page.
    Loading already runs the model through the engine's own load-time checks
    (Pellet/HermiT reasoning over FAM + OBOP + BBO), so a DL-inconsistent
    model never reaches the agent — the tester fails as early as a real
    deployment would.
    """

    def __init__(self, rdf_string: str, model_name: str = "model-under-test") -> None:
        # Same lifecycle as AppRunner: load -> run -> initiate -> first page.
        self.engine = AppEngine()
        self.engine.load_inner_app_model(rdf_string=rdf_string, model_name=model_name)
        self.engine.run_application()
        self.engine.process_received_client_data(
            {"message_type": "initiate_exchange", "message_content": {}}
        )
        self.page: AppExchangeGetOutput = self.engine.read_new_model_layout()

        #: Local form state, the counterpart of the frontend's ``formData``:
        #: fills land here and are sent in one piece with a submit click.
        #: Initialised from the page's ``data`` because the engine pre-fills
        #: re-presented forms with the user's previous entries.
        self.form_data: dict[str, Any] = dict(self._content().get("data") or {})

        #: Latest non-empty cumulative output graph (Turtle). The engine sends
        #: the graph with most responses but occasionally with an empty string
        #: (e.g. the final end-event message); keeping the last non-empty one
        #: mirrors what the frontend's GraphPanel shows and is what the
        #: round-trip oracle validates against the input shapes.
        self.output_graph: str = self.page.output_knowledge_graph or ""

        #: Observed run events, consumed by the DL trace oracle.
        self.trace: list[TraceStep] = []

        #: How often a submit was answered with the same form again — the
        #: protocol-level signature of a validation rejection. The adversarial
        #: oracle requires this to be >= 1 (invalid data MUST be rejected).
        self.validation_rejections = 0

        self._record_presented_form()

    # ------------------------------------------------------------------ pages

    def _content(self) -> dict[str, Any]:
        """The current page's ``message_content`` (always a dict, see the
        AppExchangeGetOutput contract)."""
        return self.page.message_content or {}

    def _buttons(self) -> list[dict[str, Any]]:
        """All button elements of the current uischema, in document order.

        The uischema is a nested layout tree (VerticalLayout/Group/... with
        ``elements`` lists). Buttons are the leaves the engine emits with
        ``type: "button"``, a ``label`` and a list of action pointers — see
        ``form_elements.create_jsonform_ui_schema_element``. A generic walk is
        used instead of fixed paths so any layout nesting a model chooses is
        covered.
        """
        found: list[dict[str, Any]] = []

        def walk(node: Any) -> None:
            if isinstance(node, dict):
                if node.get("type") == "button":
                    found.append(node)
                for value in node.values():
                    walk(value)
            elif isinstance(node, list):
                for value in node:
                    walk(value)

        walk(self._content().get("uischema"))
        return found

    def _label_texts(self) -> list[str]:
        """Texts of uischema Label elements.

        Models express notification screens as message-box layouts whose only
        content is Label elements plus an OK button (see the engine's
        ``validate_output_knowledge_graph``), so these texts are the "message"
        a user reads on such pages.
        """
        found: list[str] = []

        def walk(node: Any) -> None:
            if isinstance(node, dict):
                if node.get("type") == "Label" and node.get("text"):
                    found.append(str(node["text"]))
                for value in node.values():
                    walk(value)
            elif isinstance(node, list):
                for value in node:
                    walk(value)

        walk(self._content().get("uischema"))
        return found

    def _control_field_names(self) -> set[str]:
        """Property names that have an actual Control element in the uischema.

        The engine also emits schema properties for Label elements (their text
        becomes a property name), but JSONForms never renders those as inputs
        — only properties referenced by a Control's ``#/properties/<name>``
        scope appear on the screen. Restricting the observation to these keeps
        the agent's world identical to what a user sees and free of phantom
        fields on notification pages.
        """
        names: set[str] = set()

        def walk(node: Any) -> None:
            if isinstance(node, dict):
                scope = node.get("scope")
                if node.get("type") == "Control" and isinstance(scope, str):
                    names.add(scope.rsplit("/", 1)[-1])
                for value in node.values():
                    walk(value)
            elif isinstance(node, list):
                for value in node:
                    walk(value)

        walk(self._content().get("uischema"))
        return names

    def _message_text(self) -> str:
        """The message of a non-layout page (notification/information/error).

        The engine is not fully uniform here — end events send ``{"message":
        ...}``, some paths ``{"message_content": ...}`` — so both keys are
        tried, falling back to the raw content (same tolerance as the
        frontend's ``asMessage`` helper).
        """
        content = self._content()
        return str(content.get("message") or content.get("message_content") or content)

    @property
    def finished(self) -> bool:
        """True once the process token reached an end event of the main
        process (the engine's ``app_finished`` flag) — the condition the
        process-completion oracle checks."""
        process = self.engine.process_engine_instance
        return bool(process and process.app_state.app_finished)

    # ------------------------------------------------------------ observation

    def observe(self) -> str:
        """Render the current page as text — the agent's whole world view.

        The format (see the module docstring for an example) is stable on
        purpose: the LLM prompts explain it, and the scripted deciders in the
        tests parse the ``FIELDS:`` / ``BUTTONS:`` / ``APPLICATION FINISHED:``
        markers. Change it only together with both.
        """
        lines: list[str] = []

        if self.page.message_type == "layout":
            # A layout is either a data-entry form or a message box (labels +
            # an OK button); both carry schema/uischema, forms also fields.
            lines.append(
                "PAGE TYPE: form"
                if self.page.layout_type == "form"
                else "PAGE TYPE: message"
            )
            for text in self._label_texts():
                lines.append(f"MESSAGE: {text}")

            schema = self._content().get("schema") or {}
            properties: dict[str, Any] = schema.get("properties") or {}
            required: list[str] = schema.get("required") or []
            # Only properties with a Control in the uischema are real inputs;
            # the rest (Label texts leaked into the schema) are invisible to
            # a user and therefore invisible to the agent.
            visible = self._control_field_names()
            fields = {
                name: spec for name, spec in properties.items() if name in visible
            }
            if fields:
                lines.append("FIELDS:")
                # "position" carries the model's declared field order (R3);
                # present the fields the way the rendered form would.
                ordered = sorted(
                    fields.items(), key=lambda kv: kv[1].get("position", 0)
                )
                for name, spec in ordered:
                    # First the JSON type, then every real constraint the
                    # schema declares (pattern, minLength, enum, ...), then
                    # "required" — everything the agent needs to construct a
                    # valid (or deliberately invalid) value.
                    constraints = [str(spec.get("type", "string"))]
                    constraints += [
                        f"{key}={value}"
                        for key, value in spec.items()
                        if key not in _NON_CONSTRAINT_KEYS
                    ]
                    if name in required:
                        constraints.append("required")
                    current = self.form_data.get(name)
                    shown = f'"{current}"' if current not in (None, "") else "<empty>"
                    lines.append(f'  - "{name}" ({", ".join(constraints)}) = {shown}')

            buttons = self._buttons()
            if buttons:
                lines.append("BUTTONS:")
                for button in buttons:
                    # Show the action type ([submit], [cancel], ...) so the
                    # agent can tell the submit button from a cancel button
                    # even when a model labels them unhelpfully.
                    pointer = (button.get("actions") or [{}])[0]
                    label = str(button.get("label", ""))
                    lines.append(f'  - "{label}" [{pointer.get("type", "other")}]')
        else:
            # notification / information / error — a plain message page.
            lines.append(f"PAGE TYPE: {self.page.message_type}")
            lines.append(f"MESSAGE: {self._message_text()}")

        lines.append(f"APPLICATION FINISHED: {'yes' if self.finished else 'no'}")
        return "\n".join(lines)

    # ----------------------------------------------------------------- acting

    def apply(self, action: Any) -> str:
        """Apply one agent action; answer with an outcome sentence, never raise.

        Agent mistakes (unknown field, unknown button, unknown action type)
        come back as corrective text naming the valid options. The loop feeds
        that text into the next step's history, so the agent can repair
        itself — a run only dies on the loop's own guards, not on a typo of
        the model.
        """
        if action.action == "fill":
            return self._apply_fill(str(action.field or ""), str(action.value or ""))
        if action.action == "click":
            return self._apply_click(str(action.button or ""))
        return f"unknown action type '{action.action}' (use fill, click or finish)"

    def _apply_fill(self, field: str, value: str) -> str:
        """Type into a field: update the local form state only (no engine
        round-trip — the engine sees the data with the next submit)."""
        properties: dict[str, Any] = (self._content().get("schema") or {}).get(
            "properties"
        ) or {}
        # Same visibility rule as observe(): a user can only type into fields
        # that are rendered, i.e. referenced by a Control in the uischema.
        visible = self._control_field_names()
        if field not in properties or field not in visible:
            known = ", ".join(f'"{name}"' for name in properties if name in visible)
            return (
                f'no field named "{field}" on this page; '
                f"the fields are: {known or '(none)'}"
            )
        self.form_data[field] = value
        return "ok"

    def _apply_click(self, label: str) -> str:
        """Click a button: translate its first action pointer into the exact
        message the frontend would send, post it, and read the next page."""
        # Resolve the label the way a user matches a button: exact
        # (case-insensitive) first, substring as fallback for slightly
        # abbreviated LLM answers ("Submit" for "Submit form").
        buttons = self._buttons()
        button = next(
            (
                b
                for b in buttons
                if str(b.get("label", "")).casefold() == label.casefold()
            ),
            None,
        ) or next(
            (
                b
                for b in buttons
                if label.casefold() in str(b.get("label", "")).casefold()
            ),
            None,
        )
        if button is None:
            known = ", ".join(f'"{b.get("label", "")}"' for b in buttons) or "(none)"
            return f'no button named "{label}" on this page; the buttons are: {known}'

        # A button carries the model actions it can fire; like the frontend,
        # take the first pointer (multi-action buttons are not used by the
        # generator, and the factory warns about multi-trigger conditions).
        pointer = (button.get("actions") or [{}])[0]
        action_type = str(pointer.get("type", "other"))
        action_node = str(pointer.get("graph_node", ""))
        form_node = str(self._content().get("graph_node", ""))

        # Mirror of the frontend's buildActionMessage — the engine must not be
        # able to tell this tester apart from the real frontend. An empty
        # action_graph_node is legitimate: the OK button of an engine-made
        # message box carries no model action and just advances the process.
        if action_type == "submit":
            message_content: dict[str, Any] = {
                "action_type": "submit",
                "action_graph_node": action_node,
                "form_graph_node": form_node,
                "form_data": dict(self.form_data),
            }
        elif action_type == "cancel":
            # Cancel discards the current entry: the engine routes on the
            # action node alone (the exclusive gateway matches it against the
            # cancel condition), so no form data is sent.
            message_content = {
                "action_type": "cancel",
                "action_graph_node": action_node,
            }
        elif action_type == "shacl_validation":
            message_content = {
                "action_type": "shacl_validation",
                "action_graph_node": action_node,
            }
        else:
            message_content = {
                "action_type": "other",
                "action_graph_node": action_node,
                "form_graph_node": form_node,
            }

        if action_node:
            # Only real model actions enter the trace; the empty "proceed"
            # node of engine message boxes corresponds to nothing in the FAM.
            self.trace.append(TraceStep("action_performed", action_node))

        # The frontend's exchange is always post-then-get; the post's return
        # value is ignored there too.
        self.engine.process_received_client_data(
            {"message_type": "action", "message_content": message_content}
        )
        self.page = self.engine.read_new_model_layout()

        # Adopt the fresh page's state: a re-presented form arrives with the
        # user's previous entries in "data", a new form arrives empty, and a
        # non-layout page has no form state at all.
        self.form_data = (
            dict(self._content().get("data") or {})
            if self.page.message_type == "layout"
            else {}
        )
        if (self.page.output_knowledge_graph or "").strip():
            self.output_graph = self.page.output_knowledge_graph

        outcome = f'clicked "{button.get("label", "")}"'
        if action_type == "submit" and action_node:
            # A model submit reveals an engine decision, observable from the
            # page transition alone: same form again = the per-form SHACL
            # validation rejected the data (obop:FormValidationViolation);
            # anything else = it conformed. Both go into the trace; the
            # rejection also becomes the outcome sentence so the agent (and
            # the adversarial oracle) see it explicitly.
            new_form_node = str(self._content().get("graph_node", ""))
            if self.page.message_type == "layout" and new_form_node == form_node:
                self.validation_rejections += 1
                self.trace.append(
                    TraceStep("decision_observed", str(OBOP.FormValidationViolation))
                )
                outcome = (
                    "the same form was presented again "
                    "(the submitted data was rejected by validation)"
                )
            else:
                self.trace.append(
                    TraceStep("decision_observed", str(OBOP.FormValidationConforms))
                )
        self._record_presented_form()
        return outcome

    # ------------------------------------------------------------------ trace

    def _record_presented_form(self) -> None:
        """If the current page is a form, note which model block was shown
        (message boxes built by the engine itself have no graph node and are
        skipped — they correspond to nothing in the FAM)."""
        if self.page.message_type == "layout":
            node = str(self._content().get("graph_node", ""))
            if node:
                self.trace.append(TraceStep("form_presented", node))
