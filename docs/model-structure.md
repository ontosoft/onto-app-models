# Model structure (FAM)

An application in OntoUI is defined by a single RDF knowledge graph — the
**functional application model (FAM)**. Two vocabularies describe two layers
with distinct responsibilities:

| Layer | Vocabulary | Responsibility |
|-------|-----------|----------------|
| UI structure | [OBOP](http://purl.org/net/obop/) | *How the forms look*: blocks, fields, layouts, buttons, actions |
| Process | BBO (BPMN-based ontology) | *When each form is shown* and what happens after a submit: start events, user tasks, gateways, script tasks, end events |

The engine keeps the layers separate:

- **Loading** a model (`AppStaticModelFactory`) parses both layers into the
  internal static model.
- **Translating** a form into its JSONForms `schema`/`uischema`
  (`Form.create_functional_json_form_schemas`) uses only the OBOP layer.
- **Running** the application (`ProcessEngine`) walks the BBO process; when
  the token reaches a user task, the engine translates that task's form and
  sends it to the frontend.

A model without a BBO process can therefore be loaded and translated (this is
how the translation tests in
`backend/app/tests/test_onto_models_to_jsonforms.py` work), but it cannot be
run — `run_application()` needs a main process to place the token on.

## The OBOP layer by example

A minimal hand-written form: one block with one input field, a main vertical
layout, and a nested horizontal layout holding a Submit/Cancel button pair.

```turtle
@prefix :     <http://example.org/logicinterface/testing/> .
@prefix dc:   <http://purl.org/dc/elements/1.1/> .
@prefix v1:   <http://purl.org/goodrelations/v1#> .
@prefix owl:  <http://www.w3.org/2002/07/owl#> .
@prefix rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix xsd:  <http://www.w3.org/2001/XMLSchema#> .
@prefix obop: <http://purl.org/net/obop/> .

# One block = one page/form shown to the user.
:block_1 a owl:NamedIndividual , obop:Block ;
    obop:hasPositionNumber "1"^^xsd:int ;
    dc:title "block_1 for Form" .

# The main layout of the form: the layout element that belongsTo the block.
:vertical_layout_1 a owl:NamedIndividual , obop:VerticalLayout ;
    obop:belongsTo :block_1 ;
    obop:hasPositionNumber "0"^^xsd:int .

# An input field. containsDatatype names the data property under which the
# submitted value is stored in the output knowledge graph.
:field_1 a owl:NamedIndividual , obop:Field ;
    obop:belongsTo :block_1 ;
    obop:belongsToVisual :vertical_layout_1 ;
    obop:containsDatatype v1:legalName ;
    obop:hasLabel "Field 1" ;
    obop:hasPositionNumber "0"^^xsd:int .

# A sublayout nested inside the main layout (belongsToVisual, NOT belongsTo —
# only the main layout belongs to the block directly).
:horizontal_layout_1 a owl:NamedIndividual , obop:HorizontalLayout ;
    obop:belongsToVisual :vertical_layout_1 ;
    obop:hasPositionNumber "1"^^xsd:int .

# Buttons activate actions; the action's RDF type determines the behaviour.
:button_1 a owl:NamedIndividual , obop:Button ;
    obop:belongsTo :block_1 ;
    obop:belongsToVisual :horizontal_layout_1 ;
    obop:activatesAction :action_1 ;
    obop:hasLabel "Submit" ;
    obop:hasPositionNumber "0"^^xsd:int .

:button_2 a owl:NamedIndividual , obop:Button ;
    obop:belongsTo :block_1 ;
    obop:belongsToVisual :horizontal_layout_1 ;
    obop:activatesAction :action_2 ;
    obop:hasLabel "Cancel" ;
    obop:hasPositionNumber "1"^^xsd:int .

:action_1 a owl:NamedIndividual , obop:SubmitBlockAction .
:action_2 a owl:NamedIndividual , obop:CancelBlockAction .
```

Reading rules the engine applies:

- `obop:Block` is the unit presented as one form; its **main layout** is the
  layout element with `obop:belongsTo` pointing at the block.
- Every visible element names its layout parent with `obop:belongsToVisual`;
  `obop:hasPositionNumber` orders siblings within a layout.
- The action type classifies the button: `obop:SubmitBlockAction` → submit,
  `obop:CancelBlockAction` → cancel, `obop:SHACLValidation` (and subclasses) →
  validation, anything else → plain action.
- Field labels become JSON schema property names; constraints from the SHACL
  property shape attached to a field (`obop:specifiedBy`) are carried into the
  schema (`pattern`, `minLength`, `required` from `sh:minCount`, …) and
  enforced again server-side on submit, with values typed by `sh:datatype`.

This example lives in the repository as the test fixture
`backend/app/tests/test_models/test_submit_cancel_buttons.ttl`; the exact
JSONForms output it translates to is asserted in
`backend/app/tests/test_onto_models_to_jsonforms.py`.

## The BBO layer

The process layer is a BPMN process expressed in BBO: a main process with a
start event, user tasks, exclusive gateways, script tasks and end events
(subprocesses nest the same structure). A user task executes an
`obop:GenerateJSONForm` action whose `obop:actionInBlock` names the block to
display. After a submit, conditional sequence flows route the token with
`obop:routesOn` — either on the action the user chose (e.g. cancel) or on an
engine decision such as the per-form SHACL validation outcome
(`obop:FormValidationConforms` / `obop:FormValidationViolation`), which is how
validation loops ("the same form comes back with the report") and entity
loops ("Add another …") are modeled.

## Complete, runnable examples

- `backend/app_models/enter-string-form.ttl` — the smallest complete model
  (one form, full process).
- `backend/app_models/restaurant-preprocessed.ttl` — a hand-built
  multi-subprocess model (restaurant → menus → dishes → ingredients) with
  loops, connections between entities and instance pickers.
- Most models are **generated from SHACL shapes** by
  `backend/app/model_generator` (inputs in `model_generator/examples/`); the
  generator emits both layers, including per-form validation gateways.
- Every stored model can be exported as a BPMN 2.0 diagram
  (`GET /api/v1/appmodels/{id}/bpmn`, or "View Model" in the frontend) to
  inspect the process layer graphically.
