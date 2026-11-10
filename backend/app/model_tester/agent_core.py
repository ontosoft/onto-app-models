"""The environment-agnostic agent core: an observe -> decide -> act loop.

The tester treats a running FAM application as a black box that an *agent*
operates the way an end user would. One iteration of the loop is one user
interaction:

1. **observe** — the environment renders the current application page as
   plain text: the form fields with their constraints, the clickable buttons,
   notification messages, and whether the process has finished. The agent
   never sees selectors or graph nodes; it has to understand the page the way
   a user understands a screen.
2. **decide** — a decision function turns (system prompt, step prompt) into
   exactly ONE action: fill a field, click a button, or finish the test with
   a pass/fail verdict. The step prompt contains the history of previous
   actions and their outcomes, so the agent can react to rejections or
   errors without the environment keeping LLM state.
3. **act** — the environment applies the action and reports the outcome as a
   short sentence (e.g. that a submit was rejected and the same form was
   presented again), which feeds back into the next step's history.

Two design decisions matter here:

* **The decision function is pluggable** (any ``Decider`` callable). Real
  runs use ``OllamaDecider`` — a local model whose output is constrained by
  the ``format`` JSON schema, i.e. the sampler can only produce tokens that
  keep the reply valid against ``ACTION_SCHEMA``. With small local models
  this constrained decoding is far more dependable than tool-calling.
  CI tests plug in deterministic scripted deciders instead, so the loop,
  the environment and the oracles are exercised without an LLM.
* **The loop knows nothing about where the pages come from.** Stage 1 runs
  it against the engine's exchange protocol (``env_protocol.ProtocolEnv``);
  stage 2 will run the identical loop against the rendered frontend in a
  browser. Keeping the core shared is what makes the planned differential
  model-vs-UI comparison meaningful: same agent, same prompts, different
  observation channel.
"""

from __future__ import annotations

import json
import logging
import os
import time
from collections.abc import Callable
from dataclasses import dataclass
from dataclasses import field as dataclass_field
from typing import Any, Protocol

logger = logging.getLogger("ontoui_app")

#: The JSON schema sent to Ollama as the ``format`` parameter. Ollama uses it
#: for constrained decoding: every sampled token must keep the output parseable
#: as an instance of this schema, so the reply is always well-formed JSON with
#: a known shape. The per-key ``description`` texts double as inline
#: documentation for the model (they are part of what it conditions on).
ACTION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "reasoning": {
            "type": "string",
            "description": "One short sentence: why this action.",
        },
        "action": {"type": "string", "enum": ["fill", "click", "finish"]},
        "field": {
            "type": "string",
            "description": "fill only: the field name exactly as shown.",
        },
        "value": {
            "type": "string",
            "description": "fill only: the text to enter.",
        },
        "button": {
            "type": "string",
            "description": "click only: the button label exactly as shown.",
        },
        "verdict": {
            "type": "string",
            "enum": ["pass", "fail"],
            "description": "finish only.",
        },
        "reason": {
            "type": "string",
            "description": "finish only: what was observed.",
        },
    },
    # "reasoning" is required on purpose: forcing the model to verbalise a
    # justification before the action improves small-model reliability and
    # gives the transcript an explanation for every step.
    "required": ["action", "reasoning"],
}


@dataclass
class AgentAction:
    """One decision of the agent — the Python mirror of ``ACTION_SCHEMA``.

    Only the keys that belong to the chosen ``action`` are meaningful
    (``field``/``value`` for fill, ``button`` for click, ``verdict``/``reason``
    for finish); the rest stay ``None``. The environment validates the
    meaningful ones and answers with a corrective outcome text instead of
    raising, so a confused agent gets a chance to recover on the next step.
    """

    action: str  # "fill" | "click" | "finish"
    reasoning: str = ""
    field: str | None = None
    value: str | None = None
    button: str | None = None
    verdict: str | None = None  # "pass" | "fail" (finish only)
    reason: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AgentAction:
        """Build an action from parsed model output, tolerating missing keys.

        Constrained decoding guarantees well-formed JSON but not sensible
        content — a model may still omit optional keys or pick an unknown
        action string. Everything lands in the dataclass as-is; the loop and
        the environment deal with nonsense explicitly.
        """
        return cls(
            action=str(data.get("action", "")),
            reasoning=str(data.get("reasoning", "")),
            field=data.get("field"),
            value=data.get("value"),
            button=data.get("button"),
            verdict=data.get("verdict"),
            reason=data.get("reason"),
        )

    def describe(self) -> str:
        """One human-readable line for transcripts, logs and history prompts."""
        if self.action == "fill":
            return f'fill "{self.field}" with "{self.value}"'
        if self.action == "click":
            return f'click "{self.button}"'
        if self.action == "finish":
            return f"finish ({self.verdict}): {self.reason}"
        return f"unknown action '{self.action}'"


class Environment(Protocol):
    """What the agent loop needs from an environment.

    Stage 1 implements it protocol-level (``ProtocolEnv`` drives the
    AppEngine exchange loop in-process); stage 2 adds a browser-level
    implementation over the same three members. ``apply`` never raises for
    agent mistakes — it returns the outcome (success or complaint) as text,
    which the loop feeds back to the agent as history.
    """

    def observe(self) -> str: ...

    def apply(self, action: AgentAction) -> str: ...

    @property
    def finished(self) -> bool: ...


#: A decision function: decide(system_prompt, step_prompt) -> (action, llm_ms).
#: ``llm_ms`` is the model latency in milliseconds (0 for scripted deciders);
#: it is recorded per step so runs can be compared on cost, not just outcome.
Decider = Callable[[str, str], tuple[AgentAction, int]]


@dataclass
class Step:
    """One loop iteration as recorded in the transcript: what the agent saw,
    what it decided (including its stated reasoning), what happened, and how
    long the decision took."""

    index: int
    observation: str
    action: AgentAction
    outcome: str
    llm_ms: int = 0


@dataclass
class Transcript:
    """The full record of one agent run.

    ``verdict`` is the *agent's own* pass/fail judgement from its finish
    action — deliberately kept separate from the harness oracles (process
    completion, SHACL round-trip, DL trace consistency), so an agent that
    talks itself into "pass" cannot overrule the objective checks. ``aborted``
    marks runs the loop had to stop (stuck repetition or step budget), where
    no verdict exists.
    """

    mode: str
    steps: list[Step] = dataclass_field(default_factory=list)
    verdict: str | None = None  # the agent's own pass/fail, None if aborted
    reason: str = ""
    aborted: bool = False

    @property
    def llm_ms_total(self) -> int:
        return sum(s.llm_ms for s in self.steps)

    def to_dict(self) -> dict[str, Any]:
        """JSON-serializable form, used by the runner's report files."""
        return {
            "mode": self.mode,
            "verdict": self.verdict,
            "reason": self.reason,
            "aborted": self.aborted,
            "llm_ms_total": self.llm_ms_total,
            "steps": [
                {
                    "index": s.index,
                    "observation": s.observation,
                    "action": s.action.describe(),
                    "reasoning": s.action.reasoning,
                    "outcome": s.outcome,
                    "llm_ms": s.llm_ms,
                }
                for s in self.steps
            ],
        }


def _user_prompt(history: list[str], observation: str) -> str:
    """Compose the per-step prompt: history first, current page second.

    The history lines carry the environment's outcome texts, so rejections
    ("the same form was presented again ...") are visible to the agent without
    any server-side conversation state — each LLM call is self-contained,
    which keeps the context small enough for local 7B models.
    """
    past = "\n".join(history) if history else "(none yet)"
    return (
        f"Previous actions and outcomes:\n{past}\n\n"
        f"Current page:\n{observation}\n\n"
        "Answer with the next action as JSON."
    )


def run_agent(
    env: Environment,
    decide: Decider,
    system_prompt: str,
    mode: str,
    max_steps: int = 30,
) -> Transcript:
    """Run the observe -> decide -> act loop until the agent finishes.

    The loop itself never judges the application; it only moves the agent and
    records everything. Termination is one of:

    * the agent chooses ``finish`` (normal end, carries its verdict),
    * the identical action is taken three times in a row (a stuck agent —
      e.g. clicking a button that leads nowhere), or
    * ``max_steps`` is exhausted (budget guard for runaway loops in the
      model under test, which can contain genuine process cycles).

    The last two mark the transcript ``aborted``: the run is inconclusive and
    the harness treats it as failed.
    """
    transcript = Transcript(mode=mode)
    history: list[str] = []
    repeats = 0
    last_described = ""

    for index in range(max_steps):
        observation = env.observe()
        action, llm_ms = decide(system_prompt, _user_prompt(history, observation))
        logger.debug("agent step %d: %s", index, action.describe())

        if action.action == "finish":
            transcript.steps.append(
                Step(index, observation, action, "finished", llm_ms)
            )
            transcript.verdict = action.verdict
            transcript.reason = action.reason or ""
            return transcript

        outcome = env.apply(action)
        transcript.steps.append(Step(index, observation, action, outcome, llm_ms))
        history.append(f"step {index}: {action.describe()} -> {outcome}")

        described = action.describe()
        repeats = repeats + 1 if described == last_described else 1
        last_described = described
        if repeats >= 3:
            transcript.aborted = True
            transcript.reason = (
                f"aborted: action repeated {repeats} times ({described})"
            )
            return transcript

    transcript.aborted = True
    transcript.reason = f"aborted: reached max_steps ({max_steps})"
    return transcript


class OllamaDecider:
    """Decide via a local Ollama model with schema-constrained JSON output.

    Deliberately minimal: one stateless ``chat`` call per step (system prompt
    plus the self-contained step prompt), ``temperature 0`` so repeated runs
    of the same model on the same pages reproduce, and ``ACTION_SCHEMA`` as
    the ``format`` so the reply parses by construction. The host defaults to
    the OLLAMA_HOST environment variable, falling back to the local dev
    container; inside the Docker network it would be ``http://ollama:11434``.
    """

    def __init__(
        self,
        model: str = "qwen2.5:7b-instruct",
        host: str | None = None,
        num_ctx: int = 8192,
    ) -> None:
        import ollama

        self.model = model
        # 8k context fits system prompt (incl. the SHACL shapes), history and
        # one page comfortably; raise it for models with many large forms.
        self.num_ctx = num_ctx
        self._client = ollama.Client(
            host=host or os.environ.get("OLLAMA_HOST", "http://localhost:11434")
        )

    def __call__(self, system_prompt: str, user_prompt: str) -> tuple[AgentAction, int]:
        started = time.monotonic()
        response = self._client.chat(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            format=ACTION_SCHEMA,
            options={"temperature": 0, "num_ctx": self.num_ctx},
        )
        raw = response.message.content or "{}"
        ms = int((time.monotonic() - started) * 1000)
        return AgentAction.from_dict(json.loads(raw)), ms


# --- System prompts ----------------------------------------------------------
#
# The system prompt is the only place the agent learns about the application:
# its role, the action format, the mode's rules, and the SHACL shapes the model
# under test was generated from. The shapes are the agent's specification — it
# derives valid (or deliberately invalid) input values from them, the same way
# the round-trip oracle later validates the produced graph against them.

_ACTION_FORMAT = """Each step you receive the current page (fields, buttons, messages) and you
answer with exactly ONE action as JSON:
- fill a field:   {"action": "fill", "field": "<field name exactly as shown>", "value": "<text>", "reasoning": "..."}
- click a button: {"action": "click", "button": "<button label exactly as shown>", "reasoning": "..."}
- end the test:   {"action": "finish", "verdict": "pass" or "fail", "reason": "<what you observed>", "reasoning": "..."}"""

_COOPERATIVE_RULES = """Behave like a diligent end user (cooperative mode):
- Fill EVERY field of a form with sensible data that is VALID for the SHACL
  shapes below (respect datatypes and constraints such as pattern, minLength,
  maxLength, enum), then click the submit button.
- On notification/message pages, click the button to continue.
- Create exactly TWO instances of each entity type whenever the application
  offers an "Add another ..." button. Do NOT count yourself — READ the count
  the page shows you: "ALREADY SUBMITTED WITH THIS FORM: n" or "INSTANCES
  SUBMITTED WITH THE PREVIOUS FORM: n". If that number is 1, click the "Add
  another ..." button and fill the next instance with DIFFERENT values. If it
  is 2, click the button that continues instead. Never create a third
  instance of the same entity type.
- If a submit is REJECTED (the same form comes back with a validation
  report) although every value satisfies the constraints shown on the page,
  do NOT retry: finish immediately with verdict "fail" and quote the
  validation message in "reason" — the application rejected valid data.
- NEVER finish while the page says APPLICATION FINISHED: no (the ONLY
  exception is the rejected-valid-data rule above) — there is always another
  button to click first. A confirmation message is not the end.
- Only when the page says APPLICATION FINISHED: yes, finish with verdict
  "pass" if everything behaved correctly (the forms matched the shapes, valid
  data was accepted, the process completed); otherwise verdict "fail" and
  name the discrepancy in "reason"."""

_ADVERSARIAL_RULES = """Try to break the application with invalid input (adversarial mode):
- On the FIRST form, pick exactly ONE field that has a constraint and fill it
  with a value that VIOLATES that constraint. Violate only what is declared:
  minLength=5 is violated by a SHORTER value (e.g. "ab"), pattern=^[0-9]{5}$
  by a non-matching value (e.g. "ABC"). A long value violates nothing unless
  maxLength is declared.
- Fill the other fields validly. Then click submit IMMEDIATELY — do not
  change the invalid field again before submitting.
- The application MUST reject the data: the same form must be presented
  again. If instead the invalid data is accepted, finish immediately with
  verdict "fail" and say so in "reason".
- After a rejection, correct the field with a valid value, submit again, and
  continue cooperatively (click through messages) to the end.
- Create exactly TWO instances of each entity type whenever the application
  offers an "Add another ..." button. READ the shown count ("ALREADY
  SUBMITTED WITH THIS FORM: n" / "INSTANCES SUBMITTED WITH THE PREVIOUS
  FORM: n"): at 1 click "Add another ...", at 2 click the button that
  continues.
- NEVER finish while the page says APPLICATION FINISHED: no — there is always
  another button to click first.
- Only when the page says APPLICATION FINISHED: yes, finish with verdict
  "pass" if the invalid data was rejected and the corrected run completed;
  otherwise verdict "fail"."""


def build_system_prompt(mode: str, shapes_ttl: str) -> str:
    """Assemble the system prompt for one test run (see comment block above)."""
    rules = _COOPERATIVE_RULES if mode == "cooperative" else _ADVERSARIAL_RULES
    return (
        "You are an autonomous QA agent testing a form-based application that "
        "was generated from the SHACL shapes below. You interact with it step "
        "by step through an exchange protocol.\n\n"
        f"{_ACTION_FORMAT}\n\n{rules}\n\n"
        f"SHACL shapes the application was generated from:\n{shapes_ttl}"
    )
