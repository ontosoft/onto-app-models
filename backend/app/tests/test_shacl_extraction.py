"""extract_embedded_shapes: the SHACL subgraph of a mixed model graph.

The method must identify shapes the way the SHACL spec does - by type, by
target declaration, or by being referenced from another shape - so it also
works on models this project's generator did not produce.
"""

from app_engine.app_model_factory import AppStaticModelFactory
from rdflib import RDF, Graph, Literal, Namespace

SH = Namespace("http://www.w3.org/ns/shacl#")
OBOP = Namespace("http://purl.org/net/obop/")
EX = Namespace("http://example.org/")

MIXED_MODEL = """
@prefix sh:   <http://www.w3.org/ns/shacl#> .
@prefix obop: <http://purl.org/net/obop/> .
@prefix ex:   <http://example.org/> .

# Model (non-shape) triples that must stay out of the shapes graph.
ex:block_1 a obop:Block ;
    obop:targetClass ex:Person .

# Typed shape with a blank-node property shape.
ex:person_shape a sh:NodeShape ;
    sh:targetClass ex:Person ;
    sh:property [
        sh:path ex:name ;
        sh:minLength 2 ;
    ] .

# Untyped shape: only its target declaration marks it as a shape.
ex:address_shape
    sh:targetClass ex:Address ;
    sh:property ex:city_prop .

# Named property shape, reachable only through the reference above.
ex:city_prop
    sh:path ex:city ;
    sh:maxLength 40 .

# Named shape reachable only as an sh:or list member.
ex:org_shape a sh:NodeShape ;
    sh:targetClass ex:Org ;
    sh:property [
        sh:path ex:contact ;
        sh:or ( ex:email_prop [ sh:path ex:phone ] ) ;
    ] .

ex:email_prop
    sh:path ex:email ;
    sh:pattern "@" .
"""


def _extracted() -> tuple[Graph, Graph]:
    g = Graph()
    g.parse(data=MIXED_MODEL, format="turtle")
    return g, AppStaticModelFactory.extract_embedded_shapes(g)


def test_extraction_finds_typed_untyped_named_and_list_shapes():
    _, shapes = _extracted()

    # typed shape, incl. its blank-node property shape
    assert (EX.person_shape, SH.targetClass, EX.Person) in shapes
    assert shapes.value(predicate=SH.minLength, object=Literal(2)) is not None
    # untyped shape, found via its sh:targetClass
    assert (EX.address_shape, SH.targetClass, EX.Address) in shapes
    # named property shape, found via the sh:property reference
    assert (EX.city_prop, SH.maxLength, Literal(40)) in shapes
    # named shape that is only an sh:or list member
    assert (EX.email_prop, SH.pattern, Literal("@")) in shapes
    # blank-node sh:or list member comes along via the CBD
    assert shapes.value(predicate=SH.path, object=EX.phone) is not None


def test_extraction_leaves_the_model_triples_alone():
    g, shapes = _extracted()

    assert (EX.block_1, RDF.type, OBOP.Block) not in shapes
    assert (EX.block_1, OBOP.targetClass, EX.Person) not in shapes

    # The complement (what the OWL reasoners get) keeps the model and
    # loses the shapes.
    remainder = g - shapes
    assert (EX.block_1, RDF.type, OBOP.Block) in remainder
    assert (EX.person_shape, SH.targetClass, EX.Person) not in remainder
    assert remainder.value(predicate=SH.minLength, object=Literal(2)) is None
