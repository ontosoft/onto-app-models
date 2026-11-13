"""CLI: design a model agentically from a SHACL shapes file.

    python -m app.model_agent shapes.ttl                      # local Ollama
    python -m app.model_agent shapes.ttl --model qwen2.5:7b-instruct \\
        -o model.ttl --report report.json

Run from backend/ with the project environment (uv run). The LLM decides
the edits; the checkers decide the outcome. Exit code 0 only for a
confirmed model.
"""

from __future__ import annotations

import argparse
import json
import sys

from app.model_generator.templates import DEFAULT_BASE

from .loop import EditDecider, OllamaEditDecider, agentic_generate


def _live(decide: EditDecider) -> EditDecider:
    """Print each decision as it is made - a design run takes seconds per
    LLM step, and watching the agent think is the whole point of a manual
    experiment run."""

    def wrapped(system_prompt: str, user_prompt: str):
        action, ms = decide(system_prompt, user_prompt)
        print(f"  [{ms:>6} ms] {action.describe()}", flush=True)
        if action.reasoning:
            print(f"            ({action.reasoning})", flush=True)
        return action, ms

    return wrapped


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="model_agent",
        description="Agentic model generation: deterministic draft + LLM "
        "edits + checker confirmation.",
    )
    parser.add_argument("shapes", help="Path to the input SHACL shapes Turtle file")
    parser.add_argument(
        "--model", default="qwen2.5:7b-instruct", help="Ollama model name"
    )
    parser.add_argument(
        "--ollama-host",
        default=None,
        help="Ollama base URL (default: OLLAMA_HOST env or localhost:11434)",
    )
    parser.add_argument(
        "--instructions",
        default=None,
        help="Extra design brief appended to the system prompt",
    )
    parser.add_argument(
        "--base", default=DEFAULT_BASE, help="Base IRI for the generated individuals"
    )
    parser.add_argument("--max-steps", type=int, default=20)
    parser.add_argument("--max-repair-rounds", type=int, default=5)
    parser.add_argument(
        "-o", "--output", help="Write the confirmed model's Turtle here"
    )
    parser.add_argument("--report", help="Write the full run report (JSON) here")
    args = parser.parse_args(argv)

    with open(args.shapes, encoding="utf-8") as fh:
        shapes_ttl = fh.read()

    decide = _live(OllamaEditDecider(model=args.model, host=args.ollama_host))
    print(f"designing with {args.model} ...", flush=True)
    result = agentic_generate(
        shapes_ttl,
        decide,
        instructions=args.instructions,
        base=args.base,
        max_steps=args.max_steps,
        max_repair_rounds=args.max_repair_rounds,
    )

    print(
        f"\n{'CONFIRMED' if result.confirmed else 'NOT CONFIRMED'} "
        f"after {len(result.transcript.steps)} steps, "
        f"{result.repair_rounds} repair round(s); {result.transcript.reason}"
    )
    if args.report:
        with open(args.report, "w", encoding="utf-8") as fh:
            json.dump(result.to_dict(), fh, indent=2)
        print(f"Wrote {args.report}", file=sys.stderr)
    if result.model is not None:
        if args.output:
            with open(args.output, "w", encoding="utf-8") as fh:
                fh.write(result.model.rdf)
            print(f"Wrote {args.output}", file=sys.stderr)
        else:
            sys.stdout.write(result.model.rdf)
    return 0 if result.confirmed else 1


if __name__ == "__main__":
    raise SystemExit(main())
