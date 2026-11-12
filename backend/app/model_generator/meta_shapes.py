"""Validate a FAM model against the FAM meta-shapes.

The meta-shapes (app/ontologies/fam-meta.shapes.ttl) judge the MODEL itself —
is every field placed and shape-backed, every block reachable and
submittable, every property shape covered by exactly one field — as opposed
to the embedded per-entity shapes, which judge the data a generated app
collects. See docs/agentic-model-generator.md, Part B, for the check list.

Used in two places: as a post-condition of the deterministic generator
(builder.generate_model_graph raises on a violation — that is a generator
bug by definition) and as the model_tester's ``fam_well_formed`` oracle,
where it is the cheapest gate for agent-edited models.
"""

from __future__ import annotations

from pathlib import Path

from pyshacl import validate
from rdflib import Graph

META_SHAPES_PATH = (
    Path(__file__).resolve().parent.parent / "ontologies" / "fam-meta.shapes.ttl"
)

_meta_shapes: Graph | None = None


def _meta_shapes_graph() -> Graph:
    """The parsed meta-shapes, loaded once per process."""
    global _meta_shapes
    if _meta_shapes is None:
        graph = Graph()
        graph.parse(META_SHAPES_PATH, format="turtle")
        _meta_shapes = graph
    return _meta_shapes


def validate_fam_model(fam: str | Graph) -> tuple[bool, str]:
    """Check ``fam`` (Turtle text or parsed graph) against the meta-shapes.

    Returns ``(conforms, report_text)``; the report carries the ``Mn:``
    messages of every violated check.
    """
    if isinstance(fam, Graph):
        data_graph = fam
    else:
        data_graph = Graph()
        data_graph.parse(data=fam, format="turtle")
    conforms, _results_graph, results_text = validate(
        data_graph, shacl_graph=_meta_shapes_graph()
    )
    return bool(conforms), results_text.strip()
