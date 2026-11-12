"""Assemble one model test: environment + agent + oracles = a TestReport.

This is the piece a worker job (or, for now, a developer at the CLI) calls:
give it a model and a mode, get back a verdict with evidence. The flow is

    shapes.ttl --(model_generator)--> FAM model
    FAM model  --(ProtocolEnv)------> running application (in-process engine)
    agent loop --(Decider)----------> transcript + execution trace
    oracles    --------------------->  TestReport (the "green light" or not)

``run_model_test`` runs ONE mode (the name avoids pytest's ``test_*``
collection convention, so importing it into a test module stays harmless);
the CLI (``python -m app.model_tester.runner``)
runs both modes by default, because a model is only *confirmed* when it
behaves with a cooperative user AND rejects an adversarial one:

* **cooperative** — the agent enters valid data; the run must complete, the
  produced graph must round-trip against the input shapes, and the trace must
  be DL-consistent.
* **adversarial** — the agent first enters data violating the shapes; the
  engine MUST reject it (same form presented again). Acceptance of invalid
  data is a generator/engine bug. After the rejection the agent corrects the
  value and completes the run, so completion and trace are still checked;
  the round-trip oracle is skipped because its subject (what happens to valid
  data) is the cooperative run's job.

Example (local Ollama, from backend/ with the top-level .env loaded)::

    uv run python -m app.model_tester.runner \
        --shapes app/model_generator/examples/string_form.shapes.ttl \
        --out /tmp/report.json
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import dataclass
from dataclasses import field as dataclass_field
from pathlib import Path
from typing import Any

from app.model_generator import generate_appmodel_from_shacl
from app.model_tester.agent_core import (
    AgentAction,
    Decider,
    OllamaDecider,
    Transcript,
    build_system_prompt,
    run_agent,
)
from app.model_tester.env_protocol import ProtocolEnv
from app.model_tester.oracles import OracleResult, fam_well_formed, shacl_round_trip
from app.model_tester.reasoning import check_trace_consistency
from app.model_tester.violations import DeterministicDecider

logger = logging.getLogger("ontoui_app")


@dataclass
class TestReport:
    """The outcome of one agent run against one model, with all the evidence.

    ``passed`` is the harness's conclusion: every oracle green AND the agent
    itself finished with verdict "pass" (an aborted/stuck run can never pass,
    even if the oracles saw nothing wrong — inconclusive is not confirmed).
    The agent's verdict alone can likewise never turn a red oracle green; the
    two judge different things (subjective behaviour vs objective properties).
    """

    mode: str
    passed: bool
    oracles: list[OracleResult] = dataclass_field(default_factory=list)
    transcript: Transcript | None = None
    validation_rejections: int = 0
    completed: bool = False
    #: Final cumulative output knowledge graph (Turtle) — what the frontend's
    #: GraphPanel would show at the end of the run. Kept in the report so the
    #: produced data can be inspected without re-running the test.
    output_graph: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "passed": self.passed,
            "completed": self.completed,
            "validation_rejections": self.validation_rejections,
            "oracles": [oracle.to_dict() for oracle in self.oracles],
            "transcript": self.transcript.to_dict() if self.transcript else None,
            "output_graph": self.output_graph,
        }


def run_model_test(
    fam_ttl: str,
    shapes_ttl: str,
    mode: str,
    decide: Decider,
    max_steps: int = 30,
    dl_oracle: bool = True,
) -> TestReport:
    """Run one agent test of ``fam_ttl`` in ``mode`` and judge it.

    ``shapes_ttl`` serves double duty: it goes into the agent's system prompt
    as the specification to enter (or violate) data against, and it is the
    shapes graph of the round-trip oracle. ``dl_oracle=False`` skips the
    Pellet check (~10-25 s) for quick iterations; a confirmation run keeps it.
    """
    env = ProtocolEnv(fam_ttl)
    transcript = run_agent(
        env, decide, build_system_prompt(mode, shapes_ttl), mode, max_steps
    )

    oracles: list[OracleResult] = []

    # Oracle 0: the model itself must be well-formed (FAM meta-shapes).
    # Independent of the run — the deterministic generator already enforces
    # it as a post-condition, so this guards agent-edited models.
    oracles.append(fam_well_formed(fam_ttl))

    # Oracle 1: the process must have reached an end event of the main
    # process. In adversarial mode this covers the post-rejection recovery
    # (reject invalid -> accept corrected -> finish).
    oracles.append(
        OracleResult(
            "process_completed",
            env.finished,
            "the process reached an end event"
            if env.finished
            else "the process did not reach an end event",
        )
    )

    if mode == "cooperative":
        # Oracle 2: the collected data must conform to the input shapes.
        oracles.append(shacl_round_trip(shapes_ttl, env.output_graph))
    else:
        # Adversarial oracle instead: the invalid submission MUST have been
        # rejected at least once. validation_rejections counts submits that
        # were answered with the same form again.
        rejected = env.validation_rejections >= 1
        oracles.append(
            OracleResult(
                "invalid_data_rejected",
                rejected,
                f"{env.validation_rejections} submit(s) were rejected by validation"
                if rejected
                else "no submit was ever rejected — the application accepted "
                "data that violates the shapes",
            )
        )

    if dl_oracle:
        # Oracle 3: the observed trace must not contradict the model (Pellet).
        consistent, detail = check_trace_consistency(fam_ttl, env.trace)
        oracles.append(OracleResult("dl_trace_consistency", consistent, detail))

    passed = (
        all(oracle.passed for oracle in oracles)
        and not transcript.aborted
        and transcript.verdict == "pass"
    )
    return TestReport(
        mode=mode,
        passed=passed,
        oracles=oracles,
        transcript=transcript,
        validation_rejections=env.validation_rejections,
        completed=env.finished,
        output_graph=env.output_graph,
    )


def _live(decide: Decider) -> Decider:
    """Wrap a decider so every decision prints immediately.

    Redirected stdout is block-buffered, so a long CPU-bound run would stay
    silent until the process exits; the flushed line per decision makes the
    run observable with ``tail -f`` while it works.
    """

    def wrapped(system_prompt: str, user_prompt: str) -> tuple[AgentAction, int]:
        action, ms = decide(system_prompt, user_prompt)
        print(f"  [live] {action.describe()} ({ms / 1000:.1f}s)", flush=True)
        return action, ms

    return wrapped


def main(argv: list[str] | None = None) -> int:
    """CLI: generate a model from shapes, test it in both modes, print/save
    the reports. Exit code 0 = green light (all requested modes passed)."""
    parser = argparse.ArgumentParser(
        description="Agentic protocol-level test of a generated FAM model"
    )
    parser.add_argument(
        "--shapes",
        default="app/model_generator/examples/string_form.shapes.ttl",
        help="SHACL shapes file to generate the model under test from",
    )
    parser.add_argument(
        "--mode",
        choices=["cooperative", "adversarial", "both"],
        default="both",
        help="which agent mode(s) to run (default: both — confirmation needs both)",
    )
    parser.add_argument(
        "--model",
        default="qwen2.5:7b-instruct",
        help="Ollama model name for the agent",
    )
    parser.add_argument(
        "--decider",
        choices=["mixed", "llm", "scripted"],
        default="mixed",
        help="mixed (default): LLM for the cooperative run, deterministic "
        "shapes-derived decider for the adversarial run — the confirmation "
        "setup. llm: the LLM in both modes (exploration). scripted: "
        "deterministic in both modes (fast, no Ollama needed).",
    )
    parser.add_argument(
        "--ollama-host",
        default=None,
        help="Ollama base URL (default: $OLLAMA_HOST or http://localhost:11434)",
    )
    parser.add_argument("--max-steps", type=int, default=30)
    parser.add_argument(
        "--no-dl-oracle",
        action="store_true",
        help="skip the Pellet trace-consistency oracle (faster iterations)",
    )
    parser.add_argument(
        "--out",
        default=None,
        help="write the full JSON report (incl. transcripts) to this file",
    )
    args = parser.parse_args(argv)

    shapes_ttl = Path(args.shapes).read_text(encoding="utf-8")
    print(f"Generating the model under test from {args.shapes} ...")
    generated = generate_appmodel_from_shacl(shapes_ttl)

    modes = ["cooperative", "adversarial"] if args.mode == "both" else [args.mode]

    # The Ollama client is only built when some mode actually uses the LLM,
    # so fully scripted runs work without a reachable Ollama.
    llm_decide: Decider | None = None

    def decider_for(mode: str) -> Decider:
        nonlocal llm_decide
        use_llm = args.decider == "llm" or (
            args.decider == "mixed" and mode == "cooperative"
        )
        if use_llm:
            if llm_decide is None:
                llm_decide = _live(
                    OllamaDecider(model=args.model, host=args.ollama_host)
                )
            return llm_decide
        return _live(
            DeterministicDecider(shapes_ttl, adversarial=(mode == "adversarial"))
        )

    reports: list[TestReport] = []
    for mode in modes:
        agent_name = (
            args.model
            if args.decider == "llm"
            or (args.decider == "mixed" and mode == "cooperative")
            else "deterministic"
        )
        decide = decider_for(mode)
        print(f"\n=== {mode} run (agent: {agent_name}) ===", flush=True)
        report = run_model_test(
            generated.rdf,
            shapes_ttl,
            mode,
            decide,
            max_steps=args.max_steps,
            dl_oracle=not args.no_dl_oracle,
        )
        reports.append(report)

        transcript = report.transcript
        if transcript:
            for step in transcript.steps:
                print(
                    f"  step {step.index}: {step.action.describe()} -> {step.outcome}"
                )
            print(
                f"  agent verdict: {transcript.verdict} ({transcript.reason})"
                + (" [ABORTED]" if transcript.aborted else "")
            )
        for oracle in report.oracles:
            mark = "PASS" if oracle.passed else "FAIL"
            print(f"  oracle {oracle.name}: {mark} — {oracle.detail.splitlines()[0]}")
        print(f"  => {mode}: {'PASSED' if report.passed else 'FAILED'}")

    confirmed = all(report.passed for report in reports)
    print(f"\nMODEL {'CONFIRMED (green light)' if confirmed else 'NOT CONFIRMED'}")

    if args.out:
        Path(args.out).write_text(
            json.dumps([report.to_dict() for report in reports], indent=2),
            encoding="utf-8",
        )
        print(f"Full report written to {args.out}")

    return 0 if confirmed else 1


if __name__ == "__main__":
    sys.exit(main())
