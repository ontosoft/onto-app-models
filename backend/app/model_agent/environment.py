"""The design agent's environment: an EditSession behind the agent protocol.

Where the tester's ``ProtocolEnv`` wraps a RUNNING application (observe a
page, apply a click), this environment wraps a model UNDER CONSTRUCTION:
observe the IR summary, apply one edit operation. It satisfies the same
``Environment`` protocol from ``model_tester.agent_core`` - observe/apply/
finished - so loop, transcript and instrumentation stay shared between the
tester agent and the design agent.

The ``done`` action is where part D of the design draft lives: the session
renders, and the candidate runs through the checker cascade, cheapest
first. A red checker does not end the run - its report becomes the next
observation (repair feedback), until the repair budget is exhausted.
"""

from __future__ import annotations

from collections.abc import Callable

from app.model_generator.builder import GeneratedModel
from app.model_generator.editing import EditError, EditSession
from app.model_tester import run_model_test
from app.model_tester.reasoning import check_trace_consistency
from app.model_tester.violations import DeterministicDecider

from .actions import EDIT_SCHEMA, EditAction

#: A checker: (fam_ttl, shapes_ttl) -> (ok, detail). The detail of a red
#: checker is fed back to the agent verbatim, so it must be specific enough
#: to act on (a validation report, a reasoner explanation, a failing oracle).
Checker = Callable[[str, str], tuple[bool, str]]


def pellet_consistent(fam_ttl: str, shapes_ttl: str) -> tuple[bool, str]:
    """Checker 1: the model alone is OWL-DL-consistent (no trace).

    An empty trace makes ``check_trace_consistency`` a pure model audit:
    OBOP's V 0.2 TBox (disjointness, functionality, domains/ranges) against
    the generated individuals. ~2 s with Pellet; catches category confusion
    the meta-shapes cannot (they check structure, not vocabulary logic).
    """
    consistent, detail = check_trace_consistency(fam_ttl, [])
    return consistent, detail or "the model is DL-consistent"


def green_light(fam_ttl: str, shapes_ttl: str) -> tuple[bool, str]:
    """Checker 2: the full model_tester green light, both modes scripted.

    Runs the generated application end to end with the deterministic
    deciders (cooperative: valid data to completion; adversarial: one
    declared-invalid submit must be rejected). ``dl_oracle=False`` because
    checker 1 already proved the model itself consistent - rerunning Pellet
    over model+trace here would double the wall clock for little gain; it
    stays available for confirmation-grade runs via the tester CLI.
    """
    for mode in ("cooperative", "adversarial"):
        decider = DeterministicDecider(shapes_ttl, adversarial=(mode == "adversarial"))
        report = run_model_test(fam_ttl, shapes_ttl, mode, decider, dl_oracle=False)
        if report.passed:
            continue
        # Collect what actually went red: failing oracles first, then the
        # transcript's own abort/fail reason, plus the last step so the
        # agent sees WHERE the run stood when it went wrong.
        reasons = [f"{o.name}: {o.detail}" for o in report.oracles if not o.passed]
        if report.transcript and report.transcript.reason:
            reasons.append(report.transcript.reason)
        tail = ""
        if report.transcript and report.transcript.steps:
            last = report.transcript.steps[-1]
            tail = f" Last step: {last.action.describe()} -> {last.outcome}"
        return False, f"{mode} run failed - {'; '.join(reasons)}.{tail}"
    return True, "green light in both modes"


#: Part D order: cheapest first, stop at the first red. (The FAM meta-shapes
#: need no entry here - they are a post-condition inside render() itself.)
DEFAULT_CHECKERS: tuple[Checker, ...] = (pellet_consistent, green_light)


class EditEnv:
    """Implements the agent ``Environment`` protocol over an EditSession.

    ``apply`` never raises for agent mistakes: an :class:`EditError` or a
    missing parameter comes back as a corrective outcome text that the loop
    feeds into the next step's history - the same contract as
    ``ProtocolEnv.apply``, and the mechanism by which a confused agent can
    recover instead of crashing the run.
    """

    def __init__(
        self,
        session: EditSession,
        shapes_ttl: str,
        checkers: tuple[Checker, ...] | None = None,
        max_repair_rounds: int = 5,
    ) -> None:
        self.session = session
        self.shapes_ttl = shapes_ttl
        self.checkers = DEFAULT_CHECKERS if checkers is None else checkers
        self.max_repair_rounds = max_repair_rounds
        #: Failed 'done' attempts so far (= repair rounds used).
        self.repair_rounds = 0
        #: One list per 'done' attempt: [{"checker", "passed", "detail"}, ...]
        #: - the raw material for the evaluation metrics (part D).
        self.checker_reports: list[list[dict[str, object]]] = []
        self._feedback: str | None = None
        self._finished = False
        self._result: GeneratedModel | None = None

    # ------------------------------------------------------------ protocol

    @property
    def finished(self) -> bool:
        return self._finished

    @property
    def confirmed(self) -> bool:
        """True only when a rendered candidate passed EVERY checker."""
        return self._result is not None

    @property
    def result(self) -> GeneratedModel | None:
        """The confirmed model, or None (not finished / budget exhausted)."""
        return self._result

    def observe(self) -> str:
        """The agent's view: the IR summary, plus pending repair feedback.

        The summary comes from ``EditSession.summary()`` - exactly the state
        the operations manipulate, nothing more. After a red 'done' the
        checker's report is appended, so the next decision is made WITH the
        failure in view (the repair loop of part D).
        """
        text = self.session.summary()
        if self._feedback:
            text += (
                "\n\nREPAIR FEEDBACK - the last 'done' was rejected, "
                f"fix the model first:\n{self._feedback}"
            )
        return text

    def apply(self, action: EditAction) -> str:
        """Apply one action and report the outcome as a short text."""
        try:
            return self._dispatch(action)
        except EditError as err:
            # The operation refused to apply; its message is written as
            # repair feedback ("no field named X - the fields are: ...").
            return f"rejected: {err}"

    # ------------------------------------------------------------ internals

    def _dispatch(self, action: EditAction) -> str:
        """Map an EditAction onto the EditSession API.

        Missing parameters get a corrective text naming what is needed
        (constrained decoding fixes the shape of a reply, not its sense).
        """
        a = action.action
        if a == "inspect":
            return self.session.summary()
        if a == "done":
            return self._verify()
        if a == "reorder_field":
            if not action.field or action.position is None:
                return "reorder_field needs 'field' and 'position'"
            self.session.reorder_field(action.field, action.position)
            return "ok"
        if a == "group_fields":
            if not action.fields:
                return "group_fields needs 'fields': two or more field labels"
            self.session.group_fields(*action.fields)
            return "ok - the fields now share one horizontal row"
        if a == "move_entity":
            if not action.entity or action.position is None:
                return "move_entity needs 'entity' and 'position'"
            self.session.move_entity(action.entity, action.position)
            return "ok"
        if a == "set_loop":
            if not action.entity or action.looped is None:
                return "set_loop needs 'entity' and 'looped' (true/false)"
            self.session.set_loop(action.entity, action.looped)
            return "ok"
        if a == "add_relation":
            if not (action.source and action.target and action.property_iri):
                return "add_relation needs 'source', 'target' and 'property_iri'"
            self.session.add_relation(
                action.source,
                action.target,
                action.property_iri,
                multiple=bool(action.multiple),
            )
            return "ok - the forms are now connected"
        if a == "remove_relation":
            if not (action.source and action.property_iri):
                return "remove_relation needs 'source' and 'property_iri'"
            self.session.remove_relation(action.source, action.property_iri)
            return "ok"
        allowed = ", ".join(EDIT_SCHEMA["properties"]["action"]["enum"])
        return f"unknown action '{a}' - allowed actions: {allowed}"

    def _verify(self) -> str:
        """Render the candidate and run the checker cascade (part D).

        Green: the run is finished and the model confirmed. Red: the first
        failing checker's detail becomes the next observation's repair
        feedback; after ``max_repair_rounds`` failed attempts the run is
        finished WITHOUT a confirmed model. render() may raise ValueError
        on a meta-shape violation - deliberately not caught: the closed
        operations cannot produce one, so that would be a generator bug,
        never agent feedback.
        """
        rendered = self.session.render()
        attempt: list[dict[str, object]] = []
        for checker in self.checkers:
            name = getattr(checker, "__name__", repr(checker))
            ok, detail = checker(rendered.rdf, self.shapes_ttl)
            attempt.append({"checker": name, "passed": ok, "detail": detail})
            if ok:
                continue
            self.checker_reports.append(attempt)
            self.repair_rounds += 1
            if self.repair_rounds >= self.max_repair_rounds:
                self._finished = True
                return (
                    f"checker {name} failed and the repair budget "
                    f"({self.max_repair_rounds}) is exhausted: {detail}"
                )
            self._feedback = f"{name}: {detail}"
            return (
                f"not confirmed - checker {name} failed:\n{detail}\n"
                "Fix the model with further operations, then try 'done' again."
            )
        self.checker_reports.append(attempt)
        self._feedback = None
        self._result = rendered
        self._finished = True
        return "confirmed: every checker passed"
