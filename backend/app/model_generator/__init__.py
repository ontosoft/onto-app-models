"""model_generator — turn a SHACL shapes file into a complete OntoUI app model.

Deterministic rule core (this package) builds the BBO process + OBOP UI layer +
embedded validation SHACL from SHACL NodeShapes, mirroring the hand-built
restaurant pattern. Optional LLM enrichment and the test/repair loop live
outside the core.
"""

from .builder import (
    GeneratedModel,
    generate_appmodel_from_shacl,
    generate_model_graph,
)

__all__ = [
    "GeneratedModel",
    "generate_appmodel_from_shacl",
    "generate_model_graph",
]
