"""Model-edit operations over the IR: the action space of the agentic generator.

Step 3 of the design draft (docs/agentic-model-generator.md, Part C): a
closed set of operations that manipulate the parsed IR - never raw Turtle -
so every expressible edit is syntactically well-formed by construction. The
unchanged builder renders the edited IR through the same pipeline as a
deterministic generation (OWL axioms, embedded shapes, FAM meta-shape
post-condition). A future LLM agent picks these operations via constrained
decoding; until then they are a plain Python API.

Error contract: an operation either applies or raises :class:`EditError`
with a message precise enough to serve as repair feedback for an agent
("no field named X - the fields are: ..."). Nothing is partially applied.

Deliberately NOT in v1 (see the draft): ``merge_forms``/``split_form`` and
cross-entity ``assign_field`` - one block populates one entity instance, so
these need engine support for multi-shape blocks first (they would violate
meta-shape M3c today). Layout expressiveness is a flat "row" grouping for
now; the known upgrade path is a LayoutSpec tree in the IR (sections, tabs -
the natural moment to extend OBOP with that vocabulary), to which ``row``
groups migrate trivially as one-level horizontal children.
"""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field as dataclass_field

from rdflib import Graph

from .builder import GeneratedModel, assemble_model, serialize_model
from .ir import EntitySpec, PropSpec, RelationSpec
from .shacl_reader import _local, _snake, read_shapes
from .templates import DEFAULT_BASE


class EditError(ValueError):
    """An operation that cannot be applied; the message is repair feedback."""


@dataclass
class EditSession:
    """Holds the parsed IR of one model and applies edit operations to it.

    Create with :meth:`from_shacl`, apply operations, inspect with
    :meth:`summary`, and produce the model with :meth:`render` - repeatedly,
    if desired: the session owns the IR, rendering never mutates it.
    """

    shapes: Graph
    entities: list[EntitySpec]
    base: str = DEFAULT_BASE
    per_form_validation: bool = True
    owl_axioms: bool = True
    _next_row: int = dataclass_field(default=0)

    @classmethod
    def from_shacl(cls, shapes_ttl: str, base: str = DEFAULT_BASE) -> EditSession:
        """Parse the input shapes into a fresh session (the generator's draft)."""
        shapes = Graph()
        shapes.parse(data=shapes_ttl, format="turtle")
        entities = read_shapes(shapes)
        if not entities:
            raise EditError(
                "No SHACL NodeShape with sh:targetClass found in the input shapes."
            )
        return cls(shapes=shapes, entities=entities, base=base)

    # ------------------------------------------------------------- lookups

    def entity(self, name: str) -> EntitySpec:
        """Find an entity by iri_token or label (case-insensitive)."""
        wanted = name.strip().casefold()
        for ent in self.entities:
            if wanted in (ent.iri_token.casefold(), ent.label.casefold()):
                return ent
        known = ", ".join(e.iri_token for e in self.entities)
        raise EditError(f"no entity named {name!r} - the entities are: {known}")

    def field(self, name: str) -> tuple[EntitySpec, PropSpec]:
        """Find a form field by label or iri_token (case-insensitive)."""
        wanted = name.strip().casefold()
        for ent in self.entities:
            for prop in ent.properties:
                if wanted in (prop.label.casefold(), prop.iri_token.casefold()):
                    return ent, prop
        known = ", ".join(
            prop.label for ent in self.entities for prop in ent.properties
        )
        raise EditError(f"no field named {name!r} - the fields are: {known}")

    # ---------------------------------------------------------- operations

    def reorder_field(self, field_name: str, position: int) -> None:
        """Move a field to ``position`` (0-based) within its own form."""
        ent, prop = self.field(field_name)
        ent.properties.remove(prop)
        position = max(0, min(int(position), len(ent.properties)))
        ent.properties.insert(position, prop)
        self._renumber(ent)

    def group_fields(self, *field_names: str) -> int:
        """Render the named fields side by side in one horizontal row.

        All fields must belong to the same form; they are made consecutive
        (at the first member's position) and get a shared row id, which the
        builder renders as a nested HorizontalLayout. Returns the row id.
        """
        if len(field_names) < 2:
            raise EditError("group_fields needs at least two fields")
        found = [self.field(name) for name in field_names]
        entities = {id(ent) for ent, _ in found}
        if len(entities) > 1:
            placed = ", ".join(
                f"{prop.label!r} is on form {ent.iri_token!r}" for ent, prop in found
            )
            raise EditError(
                f"fields of one row must share a form, but: {placed}. "
                "Moving a field to another entity's form is not supported - "
                "a field populates the instance of its own entity."
            )
        props = [prop for _, prop in found]
        if len(set(map(id, props))) != len(props):
            raise EditError("the same field appears twice in the group")
        ent = found[0][0]
        row = self._next_row
        self._next_row += 1
        anchor = min(ent.properties.index(prop) for prop in props)
        for prop in props:
            ent.properties.remove(prop)
        for offset, prop in enumerate(props):
            prop.row = row
            ent.properties.insert(anchor + offset, prop)
        self._renumber(ent)
        return row

    def move_entity(self, entity_name: str, position: int) -> None:
        """Move an entity's subprocess to ``position`` in the main sequence."""
        ent = self.entity(entity_name)
        self.entities.remove(ent)
        position = max(0, min(int(position), len(self.entities)))
        self.entities.insert(position, ent)
        for index, each in enumerate(self.entities):
            each.order = index

    def set_loop(self, entity_name: str, looped: bool) -> None:
        """Enable/disable the "Add another ..." loop of an entity's form."""
        self.entity(entity_name).looped = bool(looped)

    def add_relation(
        self,
        source_name: str,
        target_name: str,
        property_iri: str,
        multiple: bool = False,
    ) -> None:
        """Connect two entities: instances get linked via ``property_iri``.

        Renders as an obop:Connection plus an instance picker on the later
        form; ``multiple=True`` also marks the target entity loopable.
        """
        source = self.entity(source_name)
        target = self.entity(target_name)
        if "://" not in property_iri:
            raise EditError(
                f"{property_iri!r} is not an absolute IRI - the connection "
                "needs the object property to store, e.g. "
                "http://schema.org/hasMenu"
            )
        if any(rel.path == property_iri for rel in source.relationships):
            raise EditError(
                f"{source.iri_token!r} already has a relation {property_iri}"
            )
        source.relationships.append(
            RelationSpec(
                path=property_iri,
                iri_token=_snake(_local(property_iri)),
                target_iri_token=target.iri_token,
                order=len(source.relationships),
                multiple=multiple,
            )
        )
        if multiple:
            target.looped = True

    def remove_relation(self, source_name: str, property_iri: str) -> None:
        """Remove the relation of ``source_name`` stored via ``property_iri``.

        The ex-target's loop flag is recomputed from the remaining relations
        (it stays on only while some multiple-relation still targets it).
        """
        source = self.entity(source_name)
        match = next(
            (rel for rel in source.relationships if rel.path == property_iri), None
        )
        if match is None:
            known = ", ".join(rel.path for rel in source.relationships) or "(none)"
            raise EditError(
                f"{source.iri_token!r} has no relation {property_iri} - "
                f"its relations are: {known}"
            )
        source.relationships.remove(match)
        target = self.entity(match.target_iri_token)
        target.looped = any(
            rel.multiple and rel.target_iri_token == target.iri_token
            for ent in self.entities
            for rel in ent.relationships
        )

    # ------------------------------------------------------------- output

    def summary(self) -> str:
        """Human/LLM-readable state of the IR: the agent's observation."""
        lines = []
        for index, ent in enumerate(self.entities):
            loop = " [loops]" if ent.looped else ""
            lines.append(f"form {index}: {ent.iri_token} ({ent.label}){loop}")
            for prop in ent.properties:
                row = f" [row {prop.row}]" if prop.row is not None else ""
                lines.append(f"  - field {prop.label!r}{row}")
            for rel in ent.relationships:
                many = " (multiple)" if rel.multiple else ""
                lines.append(f"  - relation {rel.path} -> {rel.target_iri_token}{many}")
        return "\n".join(lines)

    def render(self) -> GeneratedModel:
        """Build the model from the edited IR - same pipeline, same
        post-condition (FAM meta-shapes) as a deterministic generation."""
        graph = assemble_model(
            self.shapes,
            self.entities,
            self.base,
            self.per_form_validation,
            self.owl_axioms,
        )
        return serialize_model(graph)

    # ------------------------------------------------------------ helpers

    @staticmethod
    def _renumber(ent: EntitySpec) -> None:
        """Keep PropSpec.order dense and aligned with the list order (the
        builder positions by list order; sh:order in the embedded shape
        follows)."""
        for index, prop in enumerate(ent.properties):
            prop.order = index
