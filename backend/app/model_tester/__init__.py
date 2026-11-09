"""model_tester — agentic testing of FAM models (stage 1: protocol level).

An LLM agent plays the end user directly against the AppEngine exchange loop,
the same JSON protocol the real frontend speaks, so a generated model can be
tested and confirmed ("green light") without a browser. Oracles per run:
process completion, SHACL round-trip of the produced knowledge graph, and
OWL-DL consistency of the observed execution trace (Pellet over
FAM + OBOP + BBO + trace ABox).

The agent core is environment-agnostic: stage 2 adds a browser environment
(Playwright) over the same loop, enabling differential model-vs-UI testing;
stage 3 a UX-smell TBox classified by the reasoner.
"""

from .agent_core import (
    AgentAction,
    OllamaDecider,
    Transcript,
    build_system_prompt,
    run_agent,
)
from .env_protocol import ProtocolEnv, TraceStep
from .oracles import OracleResult
from .runner import TestReport, run_model_test

__all__ = [
    "AgentAction",
    "OllamaDecider",
    "OracleResult",
    "ProtocolEnv",
    "TestReport",
    "TraceStep",
    "Transcript",
    "build_system_prompt",
    "run_agent",
    "run_model_test",
]
