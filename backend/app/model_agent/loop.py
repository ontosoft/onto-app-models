"""The design loop: observe the IR -> decide one edit -> apply -> repeat.

Step 4 of the design draft (docs/agentic-model-generator.md, parts C-D).
Structurally the tester's ``run_agent`` loop - same history mechanism, same
repeat guard, same ``Step``/``Transcript`` records, so runs of the design
agent and the tester agent are directly comparable. The one structural
difference: the tester loop ends on the agent's own ``finish`` action
(the agent judges the app), while this loop ends when the ENVIRONMENT is
finished - a candidate only counts once the checkers confirmed it, and an
agent cannot talk itself past them.
"""

from __future__ import annotations

import json
import logging
import os
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from app.model_generator.builder import GeneratedModel
from app.model_generator.editing import EditSession
from app.model_generator.templates import DEFAULT_BASE
from app.model_tester.agent_core import Step, Transcript

from .actions import EDIT_SCHEMA, EditAction
from .environment import Checker, EditEnv

logger = logging.getLogger("ontoui_app")

#: A decision function: decide(system_prompt, step_prompt) -> (action, llm_ms).
#: Same contract as the tester's ``Decider``, with EditAction as the payload;
#: scripted deciders (tests) return llm_ms=0.
EditDecider = Callable[[str, str], tuple[EditAction, int]]


def _user_prompt(history: list[str], observation: str) -> str:
    """Compose the per-step prompt: history first, current model second.

    Mirrors the tester's ``_user_prompt``: the history lines carry the
    environment's outcome texts (rejections, repair feedback pointers), so
    each LLM call is self-contained - no server-side conversation state,
    and the context stays small enough for local 7B models.
    """
    past = "\n".join(history) if history else "(none yet)"
    return (
        f"Previous operations and outcomes:\n{past}\n\n"
        f"Current model:\n{observation}\n\n"
        "Answer with the next operation as JSON."
    )


def run_edit_loop(
    env: EditEnv,
    decide: EditDecider,
    system_prompt: str,
    max_steps: int = 20,
) -> Transcript:
    """Run the loop until the environment finishes or a guard trips.

    Termination is one of:

    * ``env.finished`` after an apply - either a confirmed candidate or an
      exhausted repair budget (the environment distinguishes them via
      ``env.confirmed``; the transcript's verdict mirrors that),
    * the identical operation three times in a row (stuck agent), or
    * ``max_steps`` exhausted.

    The last two mark the transcript ``aborted``, same as the tester loop.
    """
    transcript = Transcript(mode="design")
    history: list[str] = []
    repeats = 0
    last_described = ""

    for index in range(max_steps):
        observation = env.observe()
        action, llm_ms = decide(system_prompt, _user_prompt(history, observation))
        logger.debug("design agent step %d: %s", index, action.describe())

        outcome = env.apply(action)
        transcript.steps.append(Step(index, observation, action, outcome, llm_ms))
        history.append(f"step {index}: {action.describe()} -> {outcome}")

        if env.finished:
            transcript.verdict = "pass" if env.confirmed else "fail"
            transcript.reason = outcome
            return transcript

        described = action.describe()
        repeats = repeats + 1 if described == last_described else 1
        last_described = described
        if repeats >= 3:
            transcript.aborted = True
            transcript.reason = (
                f"aborted: operation repeated {repeats} times ({described})"
            )
            return transcript

    transcript.aborted = True
    transcript.reason = f"aborted: reached max_steps ({max_steps})"
    return transcript


# --- System prompt -----------------------------------------------------------
#
# The system prompt is the only place the agent learns its role, the
# operation format, the design rules and the SHACL shapes the draft was
# generated from. The current model state arrives per step (observation),
# never here - the prompt stays constant across the whole run.

_OPERATION_FORMAT = """Each step you receive the current model (its forms with their fields and
relations) and you answer with exactly ONE operation as JSON:
- move a field within its form:
  {"action": "reorder_field", "field": "<field label exactly as shown>", "position": <0-based>, "reasoning": "..."}
- show fields side by side in one row (fields of the SAME form only):
  {"action": "group_fields", "fields": ["<label>", "<label>"], "reasoning": "..."}
- reorder the forms:
  {"action": "move_entity", "entity": "<form name>", "position": <0-based>, "reasoning": "..."}
- toggle a form's "Add another ..." loop:
  {"action": "set_loop", "entity": "<form name>", "looped": true|false, "reasoning": "..."}
- link two forms' instances:
  {"action": "add_relation", "source": "<form>", "target": "<form>", "property_iri": "<absolute IRI>", "multiple": true|false, "reasoning": "..."}
- remove such a link:
  {"action": "remove_relation", "source": "<form>", "property_iri": "<IRI>", "reasoning": "..."}
- re-read the current model: {"action": "inspect", "reasoning": "..."}
- finish and hand the design to verification:
  {"action": "done", "rationale": "<why the design is good now>", "reasoning": "..."}"""

_DESIGN_RULES = """You are improving a DRAFT: the model below was generated deterministically
from the SHACL shapes, it is already correct but plain. Rules:
- Make a SMALL number of targeted edits - at most about 6, then send
  "done". Improve the design, do not rebuild it.
- Group fields that belong together semantically into one row (for
  example price + description, postal code + city, first + last name).
  Never group more than three fields into one row.
- Put the most identifying field of a form (a name or title) first.
- The forms already come in a sensible order; move a form only if that
  order is clearly wrong. reorder_field and move_entity ALWAYS need the
  integer "position".
- Keep every field and every form. Do not invent relations that are not
  backed by the shapes.
- If an operation is rejected, never repeat it unchanged: fix exactly
  what the rejection names, or do something else. After two rejections
  of the same operation, send "done".
- When you are satisfied, send "done". The design is then verified. If
  verification rejects it, the model view shows REPAIR FEEDBACK naming
  what is wrong - fix exactly that, then send "done" again."""


def build_design_prompt(shapes_ttl: str, instructions: str | None = None) -> str:
    """Assemble the system prompt for one design run.

    ``instructions`` is the caller's extra design brief (e.g. a user wish
    like "keep the menu form minimal") - appended after the general rules
    so it can override them in the model's attention.
    """
    extra = (
        f"\n\nAdditional instructions from the caller:\n{instructions}"
        if instructions
        else ""
    )
    return (
        "You are a form-design agent. A deterministic generator has drafted "
        "a form application model from the SHACL shapes below; you improve "
        "its design with the operations listed, one per step.\n\n"
        f"{_OPERATION_FORMAT}\n\n{_DESIGN_RULES}{extra}\n\n"
        f"SHACL shapes the draft was generated from:\n{shapes_ttl}"
    )


# --- Entry point -------------------------------------------------------------


@dataclass
class AgenticResult:
    """Everything one design run produced - the unit the evaluation counts.

    ``confirmed`` is the only success criterion: the checkers' verdict,
    never the agent's own. ``checker_reports`` holds every 'done' attempt's
    checker outcomes, ``repair_rounds`` how many of those were red - the
    raw numbers behind part D's metrics (green-light rate, repairs to
    green, operations per run).
    """

    confirmed: bool
    model: GeneratedModel | None
    transcript: Transcript
    repair_rounds: int
    checker_reports: list[list[dict[str, object]]]

    def to_dict(self) -> dict[str, Any]:
        """JSON-serializable form for the CLI's report file (the model's
        Turtle is written separately, it does not belong in a JSON log)."""
        return {
            "confirmed": self.confirmed,
            "repair_rounds": self.repair_rounds,
            "checker_reports": self.checker_reports,
            "transcript": self.transcript.to_dict(),
        }


def agentic_generate(
    shapes_ttl: str,
    decide: EditDecider,
    *,
    instructions: str | None = None,
    base: str = DEFAULT_BASE,
    max_steps: int = 20,
    max_repair_rounds: int = 5,
    checkers: tuple[Checker, ...] | None = None,
) -> AgenticResult:
    """Generate a model agentically: deterministic draft + LLM edits + checkers.

    The propose-verify-repair pipeline of the design draft in one call:
    parse the shapes into the deterministic draft (``EditSession.from_shacl``
    - "repair, not construction"), let the decider edit it through
    :func:`run_edit_loop`, and let the checker cascade confirm or reject
    every 'done'. ``checkers=None`` means the real cascade; tests inject
    stubs to exercise the repair path without Ollama.
    """
    session = EditSession.from_shacl(shapes_ttl, base=base)
    env = EditEnv(
        session,
        shapes_ttl,
        checkers=checkers,
        max_repair_rounds=max_repair_rounds,
    )
    system_prompt = build_design_prompt(shapes_ttl, instructions)
    transcript = run_edit_loop(env, decide, system_prompt, max_steps=max_steps)
    return AgenticResult(
        confirmed=env.confirmed,
        model=env.result,
        transcript=transcript,
        repair_rounds=env.repair_rounds,
        checker_reports=env.checker_reports,
    )


class OllamaEditDecider:
    """Decide via a local Ollama model, constrained by EDIT_SCHEMA.

    The design-agent twin of the tester's ``OllamaDecider``, and minimal in
    the same ways: one stateless ``chat`` call per step, ``temperature 0``
    for reproducible runs, the schema as ``format`` so the reply parses by
    construction, lazy ``import ollama`` so the module loads without a
    reachable Ollama. The host defaults to the OLLAMA_HOST environment
    variable, falling back to the local dev container.
    """

    def __init__(
        self,
        model: str = "qwen2.5:7b-instruct",
        host: str | None = None,
        num_ctx: int = 8192,
    ) -> None:
        import ollama

        self.model = model
        # 8k context fits system prompt (incl. the SHACL shapes), history
        # and one model summary comfortably.
        self.num_ctx = num_ctx
        self._client = ollama.Client(
            host=host or os.environ.get("OLLAMA_HOST", "http://localhost:11434")
        )

    def __call__(self, system_prompt: str, user_prompt: str) -> tuple[EditAction, int]:
        started = time.monotonic()
        response = self._client.chat(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            format=EDIT_SCHEMA,
            options={"temperature": 0, "num_ctx": self.num_ctx},
        )
        raw = response.message.content or "{}"
        ms = int((time.monotonic() - started) * 1000)
        return EditAction.from_dict(json.loads(raw)), ms
