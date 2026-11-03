"""SHACL -> OWL axiom translation (generator rule R10).

Translates the value constraints of a shapes graph into OWL TBox axioms over
the target classes, so the constraint knowledge reaches the OWL reasoners
(Pellet/HermiT) that the engine runs over the generated model. The embedded
SHACL shapes themselves are subtracted from the reasoner input, because OWL
reasoners are semantically blind to the SHACL vocabulary - these axioms are
the OWL-visible counterpart of the same knowledge.

This is knowledge transfer, NOT validation: under OWL's open-world assumption
a minimum cardinality never "fails" on missing data - it licenses inferences
(satisfiability and subsumption checks, typing of property fillers, answers
to questions like "which properties must a C instance have?"). Validating the
collected data remains the job of the embedded SHACL shapes (per-form and
final validation). The engine reasons over the static model only, so the data
a user enters can never make the model inconsistent through these axioms.

Mapping, per node shape with an IRI ``sh:targetClass`` C and property shape
with an IRI ``sh:path`` p:

=============================  ================================================
SHACL                          OWL
=============================  ================================================
sh:datatype d                  C subClassOf (p only d); p a owl:DatatypeProperty
sh:class D /                   C subClassOf (p only D); p a owl:ObjectProperty
sh:node S2 (targetClass D)
sh:minCount n (n >= 1)         C subClassOf (p min n [d|D])
sh:maxCount n                  C subClassOf (p max n [d|D])
sh:in (v1 ... vk)              C subClassOf (p only {v1, ..., vk})
sh:min+maxLength /             C subClassOf (p only d[facets])
sh:min+maxInclusive /          (an OWL 2 datatype restriction)
sh:min+maxExclusive
sh:hasValue v                  C subClassOf (p value v)
=============================  ================================================

Skipped because OWL has no faithful counterpart (logged at debug level):
``sh:nodeKind``, the logical combinators ``sh:or/and/not/xone``, and property
shapes whose ``sh:path`` is not a plain IRI (inverse/sequence paths).

Also skipped: ``sh:pattern``. OWL 2 does define the xsd:pattern facet, but
Pellet 2.3.1 (which the engine runs at model load) crashes as soon as a
pattern-restricted range meets ANY cardinality on the same property - the
satisfiability check over the pattern fails. HermiT handles the same axioms
fine (verified: it bundles dk.brics.automaton for string facets), so the
pattern stays fully effective in the embedded SHACL layer for validation.
TODO: re-enable the xsd:pattern facet once the engine's reasoning step can
run HermiT-only (or a newer Pellet) for models that carry pattern facets.
"""

from __future__ import annotations

import logging

from rdflib import RDF, RDFS, BNode, Graph, Literal, Namespace, URIRef
from rdflib.collection import Collection
from rdflib.namespace import OWL, SH

logger = logging.getLogger("ontoui_app")

_XSD = Namespace("http://www.w3.org/2001/XMLSchema#")

# SHACL facet-like constraints and the XSD constraining facets they become in
# an OWL 2 datatype restriction (owl:withRestrictions). SHACL and OWL both
# borrow these from XML Schema, so the values carry over verbatim.
# sh:pattern is deliberately absent: Pellet 2.3.1 crashes on a pattern facet
# combined with any cardinality on the same property; HermiT would cope.
# TODO: re-add (SH.pattern, _XSD.pattern) once reasoning can go HermiT-only.
_FACETS = (
    (SH.minLength, _XSD.minLength),
    (SH.maxLength, _XSD.maxLength),
    (SH.minInclusive, _XSD.minInclusive),
    (SH.maxInclusive, _XSD.maxInclusive),
    (SH.minExclusive, _XSD.minExclusive),
    (SH.maxExclusive, _XSD.maxExclusive),
)


def shacl_to_owl_axioms(shapes: Graph) -> Graph:
    """Translate the constraints of ``shapes`` into an OWL TBox graph.

    Returns a separate graph so the caller decides where the axioms go
    (the generator merges them into the FAM model).
    """
    axioms = Graph()
    # set(): a shape with several sh:targetClass triples would otherwise be
    # visited once per triple and emit duplicate axioms.
    for node_shape in set(shapes.subjects(SH.targetClass, None)):
        target = shapes.value(node_shape, SH.targetClass)
        if not isinstance(target, URIRef):
            # a blank-node or literal target cannot serve as an OWL class IRI
            continue
        axioms.add((target, RDF.type, OWL.Class))
        for property_shape in shapes.objects(node_shape, SH.property):
            _translate_property_shape(shapes, axioms, target, property_shape)
    return axioms


def _translate_property_shape(
    shapes: Graph, axioms: Graph, target: URIRef, property_shape
) -> None:
    """Emit the OWL axioms for ONE property shape of the class ``target``.

    Each translatable constraint becomes its own anonymous owl:Restriction
    attached via ``target rdfs:subClassOf _:r`` - OWL's idiom for "every
    instance of target satisfies r". Keeping one restriction per constraint
    (instead of one big intersection) keeps the axioms readable and lets a
    reasoner pinpoint WHICH constraint clashes.
    """
    path = shapes.value(property_shape, SH.path)
    if not isinstance(path, URIRef):
        # an inverse/sequence path is a blank node - OWL restrictions can
        # only be built over a plain property IRI
        logger.debug(
            f"R10: skipping property shape {property_shape} "
            "(missing or non-IRI sh:path)"
        )
        return

    datatype = shapes.value(property_shape, SH.datatype)
    object_class = shapes.value(property_shape, SH["class"])
    if object_class is None:
        # sh:node points at another shape; its target class is the range.
        node_shape = shapes.value(property_shape, SH.node)
        if node_shape is not None:
            object_class = shapes.value(node_shape, SH.targetClass)
    # Object- vs datatype-side decides the OWL vocabulary below: allValuesFrom
    # over a class vs. a data range, onClass vs. onDataRange, property kind.
    is_object = isinstance(object_class, URIRef)

    # Declaring the property kind helps the reasoners: without it, owlready2
    # may load the property as an AnnotationProperty, which carries no
    # semantics and silences every restriction over it.
    if is_object:
        axioms.add((path, RDF.type, OWL.ObjectProperty))
    elif datatype is not None:
        axioms.add((path, RDF.type, OWL.DatatypeProperty))

    def restriction() -> BNode:
        """A fresh restriction on ``path``, already attached to ``target``."""
        r = BNode()
        axioms.add((r, RDF.type, OWL.Restriction))
        axioms.add((r, OWL.onProperty, path))
        axioms.add((target, RDFS.subClassOf, r))
        return r

    # --- range ("only"): class, restricted datatype, or plain datatype ------
    facet_values = [
        (xsd_facet, value)
        for sh_pred, xsd_facet in _FACETS
        if (value := shapes.value(property_shape, sh_pred)) is not None
    ]
    if shapes.value(property_shape, SH.pattern) is not None:
        logger.debug(
            f"R10: sh:pattern on {path} not translated to OWL "
            "(Pellet limitation, see module docstring)"
        )
    if is_object:
        # C subClassOf (p only D)
        axioms.add((restriction(), OWL.allValuesFrom, object_class))
    elif facet_values:
        # C subClassOf (p only d[facets]): an OWL 2 datatype restriction,
        # e.g. xsd:string restricted by xsd:pattern "^[A-Z].*".
        base = datatype if isinstance(datatype, URIRef) else _XSD.string
        restricted = BNode()
        axioms.add((restricted, RDF.type, RDFS.Datatype))
        axioms.add((restricted, OWL.onDatatype, base))
        facets = []
        for xsd_facet, value in facet_values:
            # one bnode per facet, e.g. [ xsd:maxLength 50 ]
            facet = BNode()
            axioms.add((facet, xsd_facet, value))
            facets.append(facet)
        # owl:withRestrictions takes the facets as an RDF list; Collection
        # writes the rdf:first/rdf:rest triples for us.
        facet_list = BNode()
        Collection(axioms, facet_list, facets)
        axioms.add((restricted, OWL.withRestrictions, facet_list))
        # a plain "only datatype" axiom would be redundant here: the
        # restricted datatype already narrows the base datatype
        axioms.add((restriction(), OWL.allValuesFrom, restricted))
    elif datatype is not None:
        # C subClassOf (p only d)
        axioms.add((restriction(), OWL.allValuesFrom, datatype))

    # --- sh:in: the value space is exactly this enumeration -----------------
    in_list = shapes.value(property_shape, SH["in"])
    if in_list is not None:
        # graph.items() walks the rdf:first/rdf:rest list of sh:in
        values = list(shapes.items(in_list))
        if values:
            one_of = BNode()
            value_list = BNode()
            Collection(axioms, value_list, values)
            # IRIs enumerate individuals (an owl:Class via owl:oneOf);
            # literals enumerate a data range (rdfs:Datatype via owl:oneOf)
            kind = (
                OWL.Class
                if any(isinstance(v, URIRef) for v in values)
                else RDFS.Datatype
            )
            axioms.add((one_of, RDF.type, kind))
            axioms.add((one_of, OWL.oneOf, value_list))
            axioms.add((restriction(), OWL.allValuesFrom, one_of))

    # --- cardinalities, qualified with the range when it is known -----------
    # "p min 1 xsd:string" says more than "p min 1": the filler must come
    # from the range. OWL demands xsd:nonNegativeInteger on the number.
    qualifier = object_class if is_object else datatype
    qualified_pred = OWL.onClass if is_object else OWL.onDataRange
    min_count = shapes.value(property_shape, SH.minCount)
    # minCount 0 is SHACL's way of saying "optional" - no axiom needed
    if min_count is not None and int(min_count) >= 1:
        r = restriction()
        n = Literal(int(min_count), datatype=_XSD.nonNegativeInteger)
        if isinstance(qualifier, URIRef):
            axioms.add((r, OWL.minQualifiedCardinality, n))
            axioms.add((r, qualified_pred, qualifier))
        else:
            axioms.add((r, OWL.minCardinality, n))
    max_count = shapes.value(property_shape, SH.maxCount)
    if max_count is not None:
        r = restriction()
        n = Literal(int(max_count), datatype=_XSD.nonNegativeInteger)
        if isinstance(qualifier, URIRef):
            axioms.add((r, OWL.maxQualifiedCardinality, n))
            axioms.add((r, qualified_pred, qualifier))
        else:
            axioms.add((r, OWL.maxCardinality, n))

    # --- sh:hasValue: every instance carries exactly this value -------------
    has_value = shapes.value(property_shape, SH.hasValue)
    if has_value is not None:
        axioms.add((restriction(), OWL.hasValue, has_value))
