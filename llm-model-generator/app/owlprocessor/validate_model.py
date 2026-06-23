"""Static validation of an application model before it is executed.

These checks operate purely on the parsed rdflib graph and catch model errors
that would otherwise surface at runtime as cryptic failures (e.g. infinite
recursion in ProcessEngine.move_token). Keeping them here — decoupled from the
model-building factory — lets the same validation run from other places (API
create/update, a CLI lint, tests, the seeder) without importing the factory.

Structure:
  * ``validate_model(graph)``      — umbrella entry point. Runs every validator,
                                     logs the findings, returns them.
  * ``validate_control_flow(graph)`` — one validation category (BBO control
                                     flow). Future categories (layouts, forms,
                                     actions, ...) get their own validate_* and
                                     are added to ``validate_model``.

Nothing raises: a flawed model still loads, but the problems are visible.
"""

import logging
from dataclasses import dataclass
from enum import Enum

from rdflib import Graph

logger = logging.getLogger("ontoui_app")

BBO_PREFIX = "PREFIX bbo: <https://www.irit.fr/recherches/MELODI/ontologies/BBO#>"


class IssueCategory(str, Enum):
    CONTAINER_MISMATCH = "container_mismatch"
    DEAD_END = "dead_end"
    DANGLING_REFERENCE = "dangling_reference"


@dataclass(frozen=True)
class ValidationIssue:
    """A single model problem found during validation."""

    category: IssueCategory
    message: str
    subject: str  # the offending flow / node URI

    def __str__(self) -> str:
        return self.message


# --- Control-flow checks -----------------------------------------------------

def find_container_mismatches(graph: Graph) -> list[ValidationIssue]:
    """A sequence flow whose container differs from its source node's container.

    The engine looks for the next flow only inside the source node's container,
    so such a flow is unreachable -> "No next flow found" -> move_token recurses
    without end.
    """
    query = f"""
    {BBO_PREFIX}
    SELECT ?flow ?flowContainer ?source ?sourceContainer WHERE {{
        ?flow   bbo:has_sourceRef ?source ;
                bbo:has_container ?flowContainer .
        ?source bbo:has_container ?sourceContainer .
        FILTER (?flowContainer != ?sourceContainer)
    }}
    """
    issues: list[ValidationIssue] = []
    for row in graph.query(query):
        issues.append(
            ValidationIssue(
                category=IssueCategory.CONTAINER_MISMATCH,
                subject=str(row.flow),
                message=(
                    f"Container mismatch: flow <{row.flow}> is in "
                    f"<{row.flowContainer}> but its source <{row.source}> is in "
                    f"<{row.sourceContainer}>; the engine searches the source's "
                    f"container, so this flow is unreachable."
                ),
            )
        )
    return issues


def find_dead_ends(graph: Graph) -> list[ValidationIssue]:
    """A flow node with no outgoing sequence flow that is not a bbo:EndEvent.

    The process token arrives but cannot advance from here.
    """
    query = f"""
    {BBO_PREFIX}
    SELECT ?node WHERE {{
        ?node bbo:has_container ?container .
        FILTER NOT EXISTS {{ ?f bbo:has_sourceRef ?node }}
        FILTER NOT EXISTS {{ ?node a bbo:EndEvent }}
        FILTER NOT EXISTS {{ ?node a bbo:NormalSequenceFlow }}
        FILTER NOT EXISTS {{ ?node a bbo:ConditionalSequenceFlow }}
    }}
    """
    issues: list[ValidationIssue] = []
    for row in graph.query(query):
        issues.append(
            ValidationIssue(
                category=IssueCategory.DEAD_END,
                subject=str(row.node),
                message=(
                    f"Dead-end node <{row.node}>: no outgoing sequence flow and "
                    f"not a bbo:EndEvent; the process token cannot advance from here."
                ),
            )
        )
    return issues


def find_dangling_references(graph: Graph) -> list[ValidationIssue]:
    """A flow whose source/target points to a node that is never defined.

    Typically a rename where the flow reference was not updated (e.g. a flow
    points to ``user_gets_notification`` while the node is
    ``user_gets_notification_general_data``). The engine logs "invalid source or
    target" and cannot navigate the flow.
    """
    query = f"""
    {BBO_PREFIX}
    SELECT ?flow ?ref ?which WHERE {{
        {{ ?flow bbo:has_sourceRef ?ref . BIND("source" AS ?which) }}
        UNION
        {{ ?flow bbo:has_targetRef ?ref . BIND("target" AS ?which) }}
        FILTER NOT EXISTS {{ ?ref a ?anyType }}
    }}
    """
    issues: list[ValidationIssue] = []
    for row in graph.query(query):
        issues.append(
            ValidationIssue(
                category=IssueCategory.DANGLING_REFERENCE,
                subject=str(row.flow),
                message=(
                    f"Dangling reference: flow <{row.flow}> {row.which} points to "
                    f"<{row.ref}>, which is not defined anywhere in the model."
                ),
            )
        )
    return issues


def validate_control_flow(graph: Graph) -> list[ValidationIssue]:
    """Run the BBO control-flow checks. One validation category of the model."""
    issues: list[ValidationIssue] = []
    issues.extend(find_container_mismatches(graph))
    issues.extend(find_dead_ends(graph))
    issues.extend(find_dangling_references(graph))
    return issues


# --- Umbrella entry point ----------------------------------------------------

def validate_model(graph: Graph) -> list[ValidationIssue]:
    """Run every model validator, log the findings, and return them.

    Add further categories (layouts, forms, actions, ...) here as their own
    ``validate_*`` functions. Does not raise — the caller decides what to do.
    """
    issues: list[ValidationIssue] = []
    issues.extend(validate_control_flow(graph))
    # Future: issues.extend(validate_layouts(graph)), validate_forms(graph), ...

    for issue in issues:
        logger.warning(issue.message)

    if issues:
        logger.warning("Model validation found %d issue(s).", len(issues))
    else:
        logger.info("Model validation passed: no issues found.")
    return issues
