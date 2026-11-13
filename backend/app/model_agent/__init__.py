"""model_agent — the agentic model generator (step 4 of the design draft).

Sits on top of the two packages it wires together: ``model_generator``
provides the deterministic draft and the closed edit operations
(``EditSession``), ``model_tester`` provides the agent loop instrumentation
and the checkers that act as fitness function. An LLM (or a scripted
decider) picks edit operations via constrained decoding; every ``done``
runs the candidate through the checker cascade, red reports come back as
repair feedback, and only a candidate that passes every checker counts as
confirmed - the propose-verify-repair loop of docs/agentic-model-generator.md.
"""

from .actions import EDIT_SCHEMA, EditAction
from .environment import EditEnv
from .loop import (
    AgenticResult,
    OllamaEditDecider,
    agentic_generate,
    build_design_prompt,
    run_edit_loop,
)

__all__ = [
    "EDIT_SCHEMA",
    "AgenticResult",
    "EditAction",
    "EditEnv",
    "OllamaEditDecider",
    "agentic_generate",
    "build_design_prompt",
    "run_edit_loop",
]
