"""Objective pass/fail checks applied to a finished agent run.

The agent's own verdict is an opinion; the oracles are the judgement. Each
oracle answers one independent question about the run and together they
justify the "green light":

1. **FAM well-formedness** (:func:`fam_well_formed`) — does the model under
   test satisfy the FAM meta-shapes? A static check of the MODEL,
   not the run: the deterministic generator enforces it as a post-condition,
   so here it guards agent-edited or hand-written models, in milliseconds.
2. **process completion** — did the token reach an end event of the main
   process? (Checked in the runner from the environment's ``finished`` flag;
   it needs no helper here.)
3. **SHACL round-trip** (:func:`shacl_round_trip`) — does the knowledge graph
   the application produced conform to the very shapes the model was generated
   from? This closes the loop of the whole approach: shapes -> generated app
   -> collected data -> validated against the same shapes.
4. **DL trace consistency** (``reasoning.check_trace_consistency``) — does the
   observed run contradict the model's own axioms? Complementary to (3): SHACL
   judges the *data* under closed-world constraints, Pellet judges the
   *behaviour* under open-world DL semantics.

Every oracle returns an :class:`OracleResult` instead of raising: a failed
check is a finding about the model under test, never an error of the tester.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pyshacl import validate
from rdflib import Graph

from app.model_generator.meta_shapes import validate_fam_model


@dataclass
class OracleResult:
    """One oracle's answer: which check, did it pass, and the evidence text
    (validation report, reasoner explanation, counts) a human needs to
    understand a red light without rerunning anything."""

    name: str
    passed: bool
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "passed": self.passed, "detail": self.detail}


def fam_well_formed(fam_ttl: str) -> OracleResult:
    """Validate the model under test against the FAM meta-shapes.

    Judges the model's static structure (fields placed and shape-backed,
    blocks reachable and submittable, property shapes covered, ...) before
    any behaviour is considered — the cheapest gate, and the first one an
    agent-generated model has to pass.
    """
    conforms, report = validate_fam_model(fam_ttl)
    return OracleResult(
        "fam_well_formed",
        conforms,
        "the model satisfies the FAM meta-shapes" if conforms else report[:2000],
    )


def shacl_round_trip(shapes_ttl: str, output_graph_ttl: str) -> OracleResult:
    """Validate the produced knowledge graph against the original input shapes.

    An empty output graph fails immediately: a cooperative run that stored
    nothing cannot round-trip, and pySHACL would vacuously report "conforms"
    on an empty graph (no focus nodes, no violations) — exactly the trap the
    R9 work in the generator is about, so it must not slip through here.
    """
    if not output_graph_ttl.strip():
        return OracleResult(
            "shacl_round_trip",
            False,
            "the application produced no output knowledge graph",
        )

    data_graph = Graph()
    data_graph.parse(data=output_graph_ttl, format="turtle")
    shapes_graph = Graph()
    shapes_graph.parse(data=shapes_ttl, format="turtle")

    conforms, _results_graph, results_text = validate(
        data_graph, shacl_graph=shapes_graph
    )
    # The report text is bounded: a badly broken model can produce hundreds of
    # violations, and the report only has to say *why* the light is red.
    return OracleResult("shacl_round_trip", bool(conforms), results_text.strip()[:2000])
