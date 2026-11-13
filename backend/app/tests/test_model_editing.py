"""Edit-session contract: IR operations -> rendered model -> green light.

The operations are the future LLM agent's action space (design draft,
Part C), so these tests pin three properties: (1) an edited model still
earns the full green light end to end (the engine really serves the nested
row layout), (2) invalid operations are refused with precise EditError
messages (structurally broken states are unexpressible), and (3) the
rendered graph reflects the edits (rows, positions, loops, connections).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from rdflib import RDF, Graph, Namespace, URIRef

from app.model_generator.editing import EditError, EditSession
from app.model_generator.meta_shapes import validate_fam_model
from app.model_tester import run_model_test
from app.model_tester.violations import DeterministicDecider

OBOP = Namespace("http://purl.org/net/obop/")
BASE = "http://example.org/generated/"

EXAMPLES = Path(__file__).parent.parent / "model_generator" / "examples"


def _restaurant_shapes() -> str:
    return (EXAMPLES / "restaurant.shapes.ttl").read_text(encoding="utf-8")


def test_edited_model_earns_the_green_light() -> None:
    """Group Price+Description into a row and move Description first: the
    rendered model must still pass meta-shapes AND a full cooperative run
    (so the engine demonstrably serves the nested row layout)."""
    shapes = _restaurant_shapes()
    session = EditSession.from_shacl(shapes)
    session.group_fields("Price", "Description")
    session.reorder_field("Dish name", 2)
    generated = session.render()

    graph = Graph()
    graph.parse(data=generated.rdf, format="turtle")
    row = URIRef(f"{BASE}dish_row_0")
    assert (row, RDF.type, OBOP.HorizontalLayout) in graph
    price = URIRef(f"{BASE}field_dish_price")
    description = URIRef(f"{BASE}field_dish_description")
    assert (price, OBOP.belongsToVisual, row) in graph
    assert (description, OBOP.belongsToVisual, row) in graph

    report = run_model_test(
        generated.rdf,
        shapes,
        "cooperative",
        DeterministicDecider(shapes, adversarial=False),
        dl_oracle=False,
    )
    assert report.passed, [o.detail for o in report.oracles if not o.passed]


def test_operations_refuse_invalid_edits() -> None:
    session = EditSession.from_shacl(_restaurant_shapes())

    with pytest.raises(EditError, match="no field named"):
        session.reorder_field("No such field", 0)
    with pytest.raises(EditError, match="must share a form"):
        session.group_fields("Restaurant name", "Dish name")
    with pytest.raises(EditError, match="at least two"):
        session.group_fields("Price")
    with pytest.raises(EditError, match="no entity named"):
        session.set_loop("pizza", True)
    with pytest.raises(EditError, match="already has a relation"):
        session.add_relation(
            "dish", "menu", "http://example.org/generated/restaurant/belongsToMenu"
        )
    with pytest.raises(EditError, match="not an absolute IRI"):
        session.add_relation("menu", "dish", "belongsToMenu")
    with pytest.raises(EditError, match="has no relation"):
        session.remove_relation("menu", "http://example.org/nothing")


def test_relations_and_loops_round_trip_through_the_ir() -> None:
    """add/remove_relation keep the loop flags consistent and the rendered
    graph carries (or drops) the obop:Connection accordingly."""
    session = EditSession.from_shacl(_restaurant_shapes())

    # ingredient is looped because dish->hasIngredient is unbounded; after
    # removing that relation nothing targets ingredient multiply any more.
    assert session.entity("ingredient").looped
    session.remove_relation(
        "dish", "http://example.org/generated/restaurant/hasIngredient"
    )
    assert not session.entity("ingredient").looped

    # a new multiple relation makes its target loopable again
    session.add_relation(
        "menu",
        "ingredient",
        "http://example.org/generated/restaurant/uses",
        multiple=True,
    )
    assert session.entity("ingredient").looped

    generated = session.render()
    graph = Graph()
    graph.parse(data=generated.rdf, format="turtle")
    assert (
        URIRef(f"{BASE}menu_ingredient_connection"),
        RDF.type,
        OBOP.Connection,
    ) in graph
    assert (URIRef(f"{BASE}dish_ingredient_connection"), None, None) not in graph

    conforms, report = validate_fam_model(generated.rdf)
    assert conforms, report


def test_set_loop_toggle_is_rendered() -> None:
    """Turning menu's loop off removes its Add-another branch; the model
    still satisfies the meta-shapes."""
    session = EditSession.from_shacl(_restaurant_shapes())
    session.set_loop("menu", False)
    generated = session.render()

    graph = Graph()
    graph.parse(data=generated.rdf, format="turtle")
    assert (URIRef(f"{BASE}add_another_action_menu"), None, None) not in graph

    conforms, report = validate_fam_model(generated.rdf)
    assert conforms, report


def test_summary_reflects_the_edits() -> None:
    session = EditSession.from_shacl(_restaurant_shapes())
    session.group_fields("Address", "Postal code")
    text = session.summary()
    assert "form 0: business_entity" in text
    assert "field 'Address' [row 0]" in text
    assert "relation http://schema.org/hasMenu -> menu (multiple)" in text
