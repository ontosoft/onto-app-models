"""The OWL-DL trace oracle: let Pellet judge an observed run.

The idea
--------
A FAM model is itself a knowledge graph with DL axioms (OBOP + BBO TBox, the
model's individuals as ABox). A test run of the generated application produces
*observations* — which forms appeared, which model actions were performed,
which engine decisions the run revealed. Those observations can be written
down as further ABox facts in the very same vocabulary. If the combined
ontology (model + OBOP + BBO + observed trace) is **inconsistent**, the run
contradicts what the model claims about itself: something that can only be an
``obop:EngineDecision`` acted as a clickable ``obop:Action``, or vice versa.

This is only meaningful because obop.owl carries the universal axioms added
for exactly this purpose (commit 727685f): ``obop:EngineDecision
owl:disjointWith obop:Action``, ``obop:SubmitBlockAction owl:disjointWith
obop:CancelBlockAction`` and an ``owl:AllDifferent`` over the four
validation-decision individuals. Without disjointness, OWL's open-world
semantics would merge the categories silently instead of complaining — a
consistency check would never fire.

How the trace becomes an ABox
-----------------------------
Every :class:`~app.model_tester.env_protocol.TraceStep` is asserted as an
individual in a dedicated trace namespace, linked to the model individual it
observed, and — this is the point — the observed individual is *typed by what
role it played in the run*:

- ``action_performed``  => the node was used as an action:  ``node a obop:Action``
- ``decision_observed`` => the node was read as a decision: ``node a obop:EngineDecision``
- ``form_presented``    => recorded as evidence only (no type assertion; any
  resource may serve as a block, there is no disjointness to exploit yet).

If the model declares (or entails) the opposite category for such a node, the
disjointness axioms make the whole ontology inconsistent and Pellet reports
it. A consistent result does NOT prove the run correct (open world: missing
facts are never an error — that is what the SHACL round-trip oracle is for);
it proves the run did not *contradict* the model. The two oracles are
complementary, which is why the runner always applies both.

Cost note: Pellet is a full DL reasoner started as a JVM process; one check
takes roughly 10–25 s and, unlike the engine's load-time reasoning, cannot be
cached (every run has a different trace). That is fine for a
model-confirmation job, but do not put this into a per-request code path.
"""

from __future__ import annotations

import logging

from owlready2 import OwlReadyInconsistentOntologyError, sync_reasoner_pellet
from rdflib import RDF, Graph, Namespace, URIRef

from app.app_engine.app_model_factory import AppStaticModelFactory
from app.model_tester.env_protocol import TraceStep

logger = logging.getLogger("ontoui_app")

OBOP = Namespace("http://purl.org/net/obop/")

#: Namespace for the trace individuals. Kept outside the model's own namespace
#: so trace facts are recognisable and can never collide with model nodes.
TRACE = Namespace("http://purl.org/net/obop/trace/")


def trace_to_graph(fam_ttl: str, trace: list[TraceStep]) -> Graph:
    """Merge the observed trace into the model graph as an ABox.

    Returns a new graph: the parsed FAM model plus one ``trace:step_<i>``
    individual per trace step, linked to the observed model node and typing
    that node by the role it played (see the module docstring). Steps with an
    empty node (engine-made message boxes) carry no evidence and are skipped.
    """
    graph = Graph()
    graph.parse(data=fam_ttl, format="turtle")

    for index, step in enumerate(trace):
        if not step.node:
            continue
        step_node = TRACE[f"step_{index}"]
        observed = URIRef(step.node)
        graph.add((step_node, RDF.type, TRACE.TraceStep))

        if step.kind == "action_performed":
            graph.add((step_node, TRACE.performedAction, observed))
            # The run used this node as something a user triggers — assert the
            # category and let the disjointness axioms object if the model
            # says otherwise.
            graph.add((observed, RDF.type, OBOP.Action))
        elif step.kind == "decision_observed":
            graph.add((step_node, TRACE.observedDecision, observed))
            graph.add((observed, RDF.type, OBOP.EngineDecision))
        elif step.kind == "form_presented":
            graph.add((step_node, TRACE.presentedBlock, observed))

    return graph


def check_trace_consistency(fam_ttl: str, trace: list[TraceStep]) -> tuple[bool, str]:
    """Run Pellet over model + OBOP + BBO + trace; report (consistent, detail).

    Reuses the engine's own loading path (``read_graph_owlready`` serialises
    the graph and loads it into an owlready2 World together with obop.owl and
    bbo.owl), so the oracle reasons over exactly the ontology stack the engine
    itself uses. Inconsistency is returned as a result, not raised: for the
    tester it is a finding about the run, not an error of the tester.
    """
    graph = trace_to_graph(fam_ttl, trace)
    world, _ontology = AppStaticModelFactory.read_graph_owlready(graph)
    try:
        with world:
            sync_reasoner_pellet(
                world,
                infer_property_values=True,
                infer_data_property_values=True,
            )
    except OwlReadyInconsistentOntologyError as error:
        # Pellet's explanation names the clashing individuals/axioms — keep the
        # head of it as the human-readable reason for the red light.
        detail = str(error).strip() or "Pellet reported an inconsistent ontology"
        logger.info("DL trace oracle: INCONSISTENT — %s", detail[:300])
        return False, (
            "the observed execution trace contradicts the model "
            f"(Pellet: inconsistent ontology): {detail[:1000]}"
        )

    steps_with_evidence = sum(1 for s in trace if s.node)
    return True, (
        f"the observed execution trace ({steps_with_evidence} evidence steps) "
        "is DL-consistent with the model and the OBOP axioms"
    )
