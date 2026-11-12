"""Deterministic adversarial testing: derive the violation from the shapes.

Why no LLM here: three runs showed that a small local model cannot reliably
execute the adversarial *program* ("violate exactly ONE declared constraint
on the first form that has one, expect the rejection, correct, finish") on a
multi-form application — it invents violations where none are declared or
dithers after the rejection. But that program is not open-ended exploration;
it is a deterministic check, mechanically derivable from the SHACL shapes.
So the confirmation job runs it scripted (seconds, CI-able, no Ollama),
while the LLM agent keeps the role it is good at: cooperative/exploratory
runs that can surface EX/UX findings.

The decider consumes the SAME plain-text observations an LLM sees and emits
the SAME actions (``fill_form``/``click``/``finish``) — it is a drop-in
``Decider``, so loop, environment, trace and oracles stay identical. This
also keeps the observation format pinned by executable code.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass

from rdflib import Graph
from rdflib.namespace import SH

from app.model_tester.agent_core import AgentAction

#: Sentinel for "violate sh:minCount by leaving the field out of the submit".
OMIT = "<omit>"

_XSD = "http://www.w3.org/2001/XMLSchema#"

#: Datatypes whose lexical space excludes free text — any non-numeric string
#: (e.g. "abc") is an invalid literal for them, which the per-form validation
#: must reject (sh:datatype check on the typed literal).
_NUMERIC_DATATYPES = {
    f"{_XSD}decimal",
    f"{_XSD}integer",
    f"{_XSD}int",
    f"{_XSD}float",
    f"{_XSD}double",
}


@dataclass
class FieldSpec:
    """The violable knowledge about one form field, read from its shape."""

    name: str
    datatype: str | None = None
    min_length: int | None = None
    max_length: int | None = None
    pattern: str | None = None
    required: bool = False  # sh:minCount >= 1


def read_field_specs(shapes_ttl: str) -> dict[str, FieldSpec]:
    """Field name (sh:name) -> constraints, for every property shape.

    Relationship shapes (sh:node/sh:class, no sh:name) carry no form field
    and are skipped. Field names are unique across the generator's forms
    (they become JSON schema property names), so one flat dict suffices.
    """
    graph = Graph()
    graph.parse(data=shapes_ttl, format="turtle")
    specs: dict[str, FieldSpec] = {}
    for prop in graph.objects(None, SH.property):
        name = graph.value(prop, SH.name)
        if name is None:
            continue
        min_count = graph.value(prop, SH.minCount)
        min_length = graph.value(prop, SH.minLength)
        max_length = graph.value(prop, SH.maxLength)
        pattern = graph.value(prop, SH.pattern)
        datatype = graph.value(prop, SH.datatype)
        specs[str(name)] = FieldSpec(
            name=str(name),
            datatype=str(datatype) if datatype is not None else None,
            min_length=int(min_length) if min_length is not None else None,
            max_length=int(max_length) if max_length is not None else None,
            pattern=str(pattern) if pattern is not None else None,
            required=min_count is not None and int(min_count) >= 1,
        )
    return specs


# ----------------------------------------------------------- value synthesis


def _example_matching(pattern: str) -> str:
    """A value that fullmatches ``pattern``, or raise if none can be built.

    Tries common candidates first, then a tiny constructive fallback for the
    character-class/quantifier patterns the generator's examples use (e.g.
    ``^[0-9]{5}$``). Everything returned is VERIFIED with re.fullmatch, so a
    wrong guess can never leak into a run.
    """
    inner = pattern.lstrip("^").rstrip("$")
    candidates = ["12345", "Abcde", "Valid value", "42", "2024-01-01", "a@b.de"]
    for candidate in candidates:
        if re.fullmatch(inner, candidate):
            return candidate

    def expand(match: re.Match[str]) -> str:
        chars, count = match.group(1), int(match.group(2) or 1)
        sample = {"0-9": "1", "a-z": "a", "A-Z": "A"}.get(chars)
        if sample is None:
            sample = "1" if chars == "\\d" else chars[0]
        return sample * count

    built = re.sub(r"\[([^\]]+)\]\{(\d+)\}", expand, inner)
    built = re.sub(r"\\d\{(\d+)\}", lambda m: "1" * int(m.group(1)), built)
    if re.fullmatch(inner, built):
        return built
    raise ValueError(f"cannot synthesize a value matching pattern {pattern!r}")


def valid_value(spec: FieldSpec | None, enum_options: list[str]) -> str:
    """A value that satisfies everything the spec declares."""
    if enum_options:
        return enum_options[0]
    if spec is None:
        return "Valid text"
    if spec.datatype in _NUMERIC_DATATYPES:
        return "42" if "int" in spec.datatype else "12.99"
    if spec.datatype == f"{_XSD}boolean":
        return "true"
    if spec.datatype == f"{_XSD}date":
        return "2024-01-01"
    if spec.pattern:
        return _example_matching(spec.pattern)
    value = "Valid text"
    if spec.min_length and len(value) < spec.min_length:
        value += "x" * (spec.min_length - len(value))
    if spec.max_length and len(value) > spec.max_length:
        value = value[: spec.max_length]
    return value


def invalid_value(spec: FieldSpec | None) -> str | None:
    """A value violating ONE declared constraint, OMIT to leave the field
    out (sh:minCount), or None when the field cannot be violated at all."""
    if spec is None:
        return None
    if spec.min_length and spec.min_length >= 1:
        return "x" * (spec.min_length - 1)
    if spec.max_length:
        return "x" * (spec.max_length + 1)
    if spec.pattern:
        for candidate in ("definitely-invalid §", "x"):
            if not re.fullmatch(spec.pattern.lstrip("^").rstrip("$"), candidate):
                return candidate
    if spec.datatype in _NUMERIC_DATATYPES:
        return "abc"
    if spec.required:
        return OMIT
    return None


# ------------------------------------------------------ observation parsing

_FIELD_LINE = re.compile(r'^  - "([^"]+)" \(([^)]*)\) = .+$', re.MULTILINE)
_BUTTON_LINE = re.compile(r'^  - "([^"]+)" \[([a-z_]+)\]$', re.MULTILINE)


def _parse_fields(observation: str) -> list[tuple[str, list[str]]]:
    """[(field name, enum options)] in page order."""
    fields: list[tuple[str, list[str]]] = []
    for name, constraints in _FIELD_LINE.findall(observation):
        enum_match = re.search(r"enum=(\[.*?\])", constraints)
        options = ast.literal_eval(enum_match.group(1)) if enum_match else []
        fields.append((name, [str(option) for option in options]))
    return fields


def _parse_buttons(observation: str) -> list[tuple[str, str]]:
    """[(label, action type)] in page order."""
    return _BUTTON_LINE.findall(observation)


# ------------------------------------------------------------------ decider


class DeterministicDecider:
    """Scripted stand-in for the LLM, for confirmation runs in both modes.

    Cooperative (``adversarial=False``): fill every form validly, click
    through messages, never enter loops ("Add another ..." is never
    clicked), finish pass once the application reports it is done.

    Adversarial (``adversarial=True``): same navigation, but the FIRST form
    that has a violable field gets exactly one violation; the rejection is
    recognised by the re-presented form carrying the validation report, the
    values are corrected, and the run continues to the end. Acceptance of
    the invalid submit, or an end reached without any rejection, finishes
    with verdict "fail".
    """

    def __init__(self, shapes_ttl: str, adversarial: bool) -> None:
        self.specs = read_field_specs(shapes_ttl)
        self.adversarial = adversarial
        self.awaiting_rejection = False
        self.rejection_seen = False

    def _fill_all_valid(
        self, fields: list[tuple[str, list[str]]], button: str
    ) -> AgentAction:
        return AgentAction(
            action="fill_form",
            reasoning="fill every field with shape-conforming values",
            fields={
                name: valid_value(self.specs.get(name), options)
                for name, options in fields
            },
            button=button,
        )

    def __call__(self, system: str, prompt: str) -> tuple[AgentAction, int]:
        # The observation is the last section of the step prompt; history
        # above it is not needed — all state lives in this object.
        observation = prompt.rsplit("Current page:\n", 1)[-1]

        if "APPLICATION FINISHED: yes" in observation:
            if self.adversarial and not self.rejection_seen:
                return AgentAction(
                    action="finish",
                    verdict="fail",
                    reason="the run finished without a single validation "
                    "rejection — either the model declares no violable "
                    "constraint or invalid data was accepted",
                ), 0
            return AgentAction(
                action="finish", verdict="pass", reason="completed as expected"
            ), 0

        fields = _parse_fields(observation)
        buttons = _parse_buttons(observation)

        if fields:
            submit = next(
                (label for label, kind in buttons if kind == "submit"),
                buttons[0][0] if buttons else "",
            )
            if self.awaiting_rejection:
                if "MESSAGE: Validation Report" not in observation:
                    return AgentAction(
                        action="finish",
                        verdict="fail",
                        reason="a new form appeared after the invalid submit — "
                        "the application accepted data violating the shapes",
                    ), 0
                # The expected rejection: correct everything and move on.
                self.awaiting_rejection = False
                self.rejection_seen = True
                return self._fill_all_valid(fields, submit), 0

            if self.adversarial and not self.rejection_seen:
                target = next(
                    (
                        (name, invalid_value(self.specs.get(name)))
                        for name, _ in fields
                        if invalid_value(self.specs.get(name)) is not None
                    ),
                    None,
                )
                if target is not None:
                    name, bad = target
                    values = {
                        field: valid_value(self.specs.get(field), options)
                        for field, options in fields
                        if field != name
                    }
                    if bad != OMIT:
                        values[name] = str(bad)
                    self.awaiting_rejection = True
                    return AgentAction(
                        action="fill_form",
                        reasoning=f"violate the declared constraint of {name!r}",
                        fields=values,
                        button=submit,
                    ), 0
            return self._fill_all_valid(fields, submit), 0

        # Message page right after the invalid submit: the engine moved on,
        # i.e. the violating data was accepted and even confirmed.
        if self.awaiting_rejection:
            return AgentAction(
                action="finish",
                verdict="fail",
                reason="the application confirmed a submit that violates "
                "the shapes instead of rejecting it",
            ), 0

        # Plain message/confirmation page: continue, but never into a loop.
        label = next(
            (
                label
                for label, _ in buttons
                if not label.casefold().startswith("add another")
            ),
            buttons[0][0] if buttons else None,
        )
        if label is not None:
            return AgentAction(
                action="click", button=label, reasoning="continue past the message"
            ), 0
        return AgentAction(
            action="finish", verdict="fail", reason="page offers nothing to do"
        ), 0
