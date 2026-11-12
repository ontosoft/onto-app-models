# Draft: the agent-based model generator

Status: **design draft** (2026-11-12) — nothing in here is implemented yet.
It specifies the three artifacts an LLM-based `model_generator` variant needs
*before* any LLM is involved: an axiomatization of OBOP that makes bad designs
inconsistent (Part A), SHACL meta-shapes that make incomplete designs invalid
(Part B), and a closed catalog of model-edit operations for the LLM to choose
from (Part C). Parts D and E describe the verification loop around them and
the reasoning-type matrix the research question asks about.

## 0. Architecture: propose — verify — repair

The deterministic generator (`backend/app/model_generator/`) maps SHACL shapes
to a FAM model by fixed rules. The agentic variant keeps every guarantee but
moves the *design decisions* (which fields on which form, what to group, where
to loop) to an LLM — made safe by the same pattern that already works in the
`model_tester`: the LLM only picks from a constrained action vocabulary, and
symbolic checkers judge the result.

```
shapes.ttl ──► deterministic generator ──► draft FAM ──┐
                                                       ▼
            ┌───────────────  LLM agent (edit-operation DSL, Part C) ◄─┐
            │                        │                                │
            │                        ▼                                │
            │            candidate FAM model                          │
            │                        │                                │
            │     ┌──────────────────┼──────────────────┐             │
            │     ▼                  ▼                  ▼             │
            │  OWL consistency   FAM meta-shapes   model_tester       │
            │  (Pellet, Part A)  (pySHACL, Part B) (green light)      │
            │     │                  │                  │             │
            │     └───────── all green? ────────────────┘             │
            │           no: reports back as repair feedback ──────────┘
            └── yes: CONFIRMED agent-generated FAM
```

Key decisions this draft commits to:

1. **Repair, not construction.** The agent starts from the deterministic
   draft and edits it, instead of writing a FAM from nothing. Every
   intermediate state is a complete model, every checker can run after every
   operation, and the deterministic generator doubles as the evaluation
   baseline.
2. **The LLM never writes Turtle.** It emits operations from a closed JSON
   schema (constrained decoding, exactly like the tester's `ACTION_SCHEMA`);
   the existing builder machinery executes them. Syntactic well-formedness is
   guaranteed by construction, so the checkers only have to judge semantics.
3. **The model_tester is the final oracle.** A candidate FAM counts as
   confirmed only after the existing green light (cooperative run + scripted
   adversary + SHACL round-trip + DL trace consistency, ~15 s per model).

## Part A — OBOP TBox axioms (OWL: make bad designs *inconsistent*)

Current state of `backend/app/ontologies/obop.owl`: 2 `owl:disjointWith`
axioms (the `EngineDecision`/`Action` pair the DL trace oracle relies on) and
10 object properties with `rdfs:domain owl:Thing`. A reasoner therefore
accepts almost any mis-assembled FAM. The axioms below close that gap; each
one names the broken design it turns into a Pellet inconsistency.

Prefixes: `obop: <http://purl.org/net/obop/>`, `owl`, `rdfs`, `xsd` as usual.

### A1 — Disjointness partition of the visual vocabulary *(new)*

```turtle
[] a owl:AllDisjointClasses ;
   owl:members ( obop:Layout obop:Field obop:Button obop:Label ) .
obop:Block         owl:disjointWith obop:VisualElement .
obop:Connection    owl:disjointWith obop:Connector .
obop:Loop          owl:disjointWith obop:Branching .
obop:HorizontalLayout owl:disjointWith obop:VerticalLayout .
```

Catches: an agent typing one node as both a layout and a field, reusing a
connection IRI as its own connector, or declaring a layout both horizontal
and vertical. This is the same move that made the trace oracle work
(commit for `EngineDecision ⊥ Action`): disjointness is what gives Pellet
teeth.

### A2 — Domains and ranges with content *(replaces the `owl:Thing` domains)*

```turtle
obop:belongsTo        rdfs:domain [ owl:unionOf ( obop:VisualElement obop:Action obop:Loop ) ] ;
                      rdfs:range  obop:Block .
obop:belongsToVisual  rdfs:domain obop:VisualElement ;
                      rdfs:range  obop:Layout .
obop:activatesAction  rdfs:domain obop:Button ;
                      rdfs:range  obop:Action .
obop:connectionHasSource rdfs:domain obop:Connection .
obop:connectionHasTarget rdfs:domain obop:Connection .
obop:hasConnector     rdfs:domain obop:Connection ;
                      rdfs:range  obop:Connector .
obop:hasPositionNumber rdfs:domain obop:VisualElement .
```

Catches (together with A1): `belongsToVisual` pointing at a `Field` instead
of a `Layout` — the range axiom infers `Layout`, the disjointness axiom
explodes. Without A1, domain/range axioms only *infer* types (OWA), they
never fail; the two parts work as a pair.

Caveat: domain/range tightening can retype nodes in **existing hand-written
models** that play loose. Before merging, run the engine's load-time
consistency check over `backend/app_models/*.ttl` and the two generator
examples — any model that goes inconsistent is either a real modeling bug
(fix the model) or evidence the axiom is too strict (weaken it). That audit
is part of the implementation task, not optional.

### A3 — Functionality (at most one) *(new)*

```turtle
obop:belongsTo           a owl:FunctionalProperty .   # one block per element
obop:belongsToVisual     a owl:FunctionalProperty .   # one layout per element
obop:hasPositionNumber   a owl:FunctionalProperty .
obop:containsDatatype    a owl:FunctionalProperty .
obop:connectionHasSource a owl:FunctionalProperty .
obop:connectionHasTarget a owl:FunctionalProperty .
```

Catches: an edit sequence that assigns a field to a second form without
removing it from the first — the field ends up with two `belongsToVisual`
values, functionality forces them equal, and the two layouts are distinct
named individuals. **Requires explicit inequality to fire**: OWL has no
unique-name assumption, so the generator must emit
`owl:AllDifferent` over the minted individuals (cheap: one axiom listing all
generated layout/field/button IRIs). Without it, A3 silently merges nodes
instead of complaining — worse than no axiom. Emit `owl:AllDifferent`
first, then A3.

### A4 — Existence requirements (reasoner Q&A, not validation) *(new)*

```turtle
obop:Button     rdfs:subClassOf [ a owl:Restriction ;
                  owl:onProperty obop:activatesAction ;
                  owl:someValuesFrom obop:Action ] .
obop:Connection rdfs:subClassOf [ a owl:Restriction ;
                  owl:onProperty obop:hasConnector ;
                  owl:someValuesFrom obop:Connector ] .
```

Under OWA these never *fail* on a missing action — that check belongs to the
meta-shapes (M6). Their value is inferential: they let the reasoner answer
"what must exist for this design to be realizable" and they type unnamed
fillers. Keep them, but do not expect red lights from them.

### A5 — Main layout, made explicit *(new property + axiom)*

Today "the main layout of a block" is implicit: the `Layout` that
`belongsTo` the block and has no `belongsToVisual`. Implicit structure is
invisible to both reasoners and shapes. Proposal:

```turtle
obop:hasMainLayout a owl:ObjectProperty , owl:FunctionalProperty ;
    rdfs:domain obop:Block ; rdfs:range obop:Layout ;
    rdfs:subPropertyOf [ owl:inverseOf obop:belongsTo ] .
```

The generator emits one `hasMainLayout` triple per block (one-line change in
`templates.py`); the engine may keep its current discovery logic unchanged —
the triple is additive. "Every block has **exactly one** main layout" then
becomes checkable: ≤1 by functionality here, ≥1 by meta-shape M2 (CWA).
Today that invariant lives in a runtime `ValueError`; after this it lives in
the model, where the generating agent can be corrected *before* the engine
runs.

### A6 — What OWL cannot catch (scope honesty)

Not expressible (or not worth the encoding contortions) in DL, deliberately
left to Parts B/E:

- *Completeness* of any kind ("every property shape is covered by a field",
  "the form has a submit button") — OWA; → meta-shapes.
- *Local uniqueness* ("position numbers unique among siblings of one
  layout") — needs comparison across siblings; → meta-shape M4 (SPARQL).
- *Reachability/termination* ("every block is reached by the process",
  "every loop can exit") — graph/temporal properties; → Part E.

### A7 — Pellet 2.3.1 constraints (hard requirement)

The engine's load-time reasoner is Pellet 2.3.1, which crashes on
`xsd:pattern` facets combined with cardinalities (documented in
`owl_axioms.py`, R10). All axioms above use only disjointness, domain/range,
functionality, `someValuesFrom` and inverse — OWL 2 RL-ish territory Pellet
2.3.1 handles. Rule for every future axiom: **add a regression test that
loads a model carrying the axiom through the actual Pellet step** before
relying on it (the R10 pattern story is the cautionary tale).

### A8 — Where the axioms live

In `obop.owl` itself, not merged per-model: they are claims about the OBOP
vocabulary, and every consumer (engine load check, DL trace oracle, the new
generator checkers) should see the same TBox. Version the change in the
ontology header comment.

## Part B — FAM meta-shapes (SHACL: make incomplete designs *invalid*)

A new shapes file, proposal `backend/app/ontologies/fam-meta.shapes.ttl`,
validated with pySHACL against candidate FAM models. This is the CWA
counterpart of Part A: OWL says "this design contradicts itself", the
meta-shapes say "this design is missing something". Checks, in priority
order:

| ID | Shape (informal) | Broken design it rejects | Mechanism |
|----|------------------|--------------------------|-----------|
| M1 | Every `obop:Field` has exactly 1 `belongsToVisual`, exactly 1 `hasPositionNumber`, ≥1 `obop:specifiedBy` pointing at it or a datatype | orphan field; unplaceable field; field with no property shape | plain `sh:property` counts |
| M2 | Every `obop:Block` has exactly 1 `obop:hasMainLayout` (after A5) | formless block / two root layouts | plain counts |
| M3 | Every `sh:PropertyShape` with `sh:name` in the embedded shapes is `obop:specifiedBy`-linked to exactly one field | the field→form assignment lost a property, or duplicated one — THE core correctness criterion for "assign fields to the right forms" | `sh:sparql` |
| M4 | `hasPositionNumber` values are unique among elements sharing a `belongsToVisual` (or main layout) | two fields on one position | `sh:sparql` |
| M5 | Every `obop:Block` is referenced from the BBO process (a `bbo:UserTask`-reachable `GenerateJSONForm` action) | unreachable dead form | `sh:sparql` over FAM+BBO |
| M6 | Every block with fields has ≥1 button whose action is an `obop:SubmitBlockAction` | form that can never submit | `sh:sparql` |
| M7 | Every `obop:Connection` has `connectionHasSource`, `connectionHasTarget`, ≥1 `hasConnector` | dangling relation — generated app would drop the triple | plain counts |
| M8 | Every `obop:Button` activates ≥1 action, sits in exactly one layout, has one position and a label | dead button that does nothing when clicked | plain counts |

Integration points (both cheap):

1. **Generator post-condition**: `generate_appmodel_from_shacl` validates its
   own output against the meta-shapes (a few ms with pySHACL). The
   deterministic generator should pass trivially — if it does not, either
   the generator or the meta-shape has a bug; both findings are valuable.
   This also pins the meta-shapes with executable coverage from day one.
2. **Fourth oracle in the model_tester**: `fam_well_formed` next to
   `process_completed` / `shacl_round_trip` / `dl_trace_consistency`, so the
   green light covers static well-formedness too. For the agentic loop this
   oracle is the *first* gate (fails in ms, before any engine run).

## Part C — The edit-operation DSL (what the LLM actually does)

The operation catalog deliberately mirrors `ir.py`: operations manipulate
`EntitySpec`/`PropSpec`/`RelationSpec` objects (the IR), and the existing
`builder.py` renders the edited IR to a FAM. The LLM never touches triples.
That keeps the DSL small, every operation total (it either applies or
returns a typed refusal string — same contract as `ProtocolEnv.apply`), and
the render step identical to the proven deterministic path.

### C1 — Operations

| Op | Parameters | Effect on the IR | OBOP triples affected (via builder) |
|----|------------|------------------|-------------------------------------|
| `assign_field` | `field`, `form` | move a `PropSpec` to another `EntitySpec`'s form | `belongsToVisual`, `hasPositionNumber`, embedded shape stays with its NodeShape (M3 guards the mapping) |
| `reorder_field` | `field`, `position` | change `PropSpec.order` | `hasPositionNumber` |
| `group_horizontal` | `fields[]` | wrap consecutive props in a nested row | new `HorizontalLayout` + `belongsToVisual` rewiring |
| `merge_forms` | `form_a`, `form_b` | one block/subprocess for two entities | blocks, layouts, BBO subprocess wiring |
| `split_form` | `form`, `fields[]` | opposite of merge: second block for the listed fields | same, inverted |
| `set_loop` | `entity`, `on/off`, `button_label` | toggle `EntitySpec.looped` | `obop:Loop`, loop condition, "Add another …" button |
| `connect` | `source`, `target`, `property` | add/adjust a `RelationSpec` | `Connection`, `Connector`, source/target |
| `set_button` | `form`, `kind` (`submit`/`cancel`), `label` | button labels/actions | `Button`, `SubmitBlockAction`/`CancelBlockAction` |
| `inspect` | — | no-op: returns the current IR summary | — |
| `done` | `rationale` | stop editing, hand to the checkers | — |

Everything else (IRI minting, position renumbering, BBO re-wiring after
merge/split) is the builder's job — exactly the state-keeping the tester
experiments showed a 7B model cannot be trusted with. If merge/split proves
too hairy to re-wire generically, cut both from v1; the remaining eight
operations already cover the research question's core ("assign fields to
the right forms, combine loops and other UI elements").

### C2 — Schema sketch (constrained decoding)

```json
{
  "type": "object",
  "properties": {
    "op": {"enum": ["assign_field", "reorder_field", "group_horizontal",
                     "merge_forms", "split_form", "set_loop", "connect",
                     "set_button", "inspect", "done"]},
    "args": {"type": "object", "additionalProperties": {"type": "string"}},
    "reasoning": {"type": "string"}
  },
  "required": ["op", "args"]
}
```

One op per LLM call, with the IR summary + the latest checker reports as the
observation — structurally the same loop as `agent_core.run_agent`, so the
transcript/repair-count instrumentation can be shared.

### C3 — Model size, realistically

The tester runs showed qwen2.5:7b executes *constrained single decisions*
fine and fails at *multi-step programs with invented state*. The DSL is
designed so each decision is single-step and the state lives in the IR —
that is the 7B-compatible shape. Still, plan the evaluation with at least
one larger model as a second data point; "which model capacity does
schema-constrained FAM design need" is itself a reportable result.

## Part D — Verification loop and evaluation

Loop (per candidate):

1. meta-shapes (ms) → 2. Pellet consistency (~seconds) → 3. model_tester
   green light (~15 s, scripted both modes) — ordered cheapest-first, stop
   at first red.
2. On red: feed back the *specific* artifact — the SHACL validation report
   (meta-shapes), the Pellet explanation (axioms), or the failing oracle +
   transcript tail (tester) — as the next observation. Cap repair rounds
   (e.g. 5), then fail the candidate.

Evaluation design (the publishable experiment):

- **Baseline**: deterministic generator, same shapes inputs.
- **Metrics**: green-light rate; repair iterations to green; operations per
  run; wall-clock; **design diversity** — number of structurally distinct
  confirmed FAMs per shapes input (e.g. modulo IRI renaming), which the
  deterministic generator cannot have (always 1) and the agent can.
- **Inputs**: the existing examples plus shapes crafted to force decisions
  (many properties → grouping pressure; multiple `sh:node` relations →
  loop/merge pressure).
- **Ablations**: with/without meta-shape feedback; with/without starting
  draft (repair vs construction); model sizes.

## Part E — Reasoning-type matrix (the "not only OWL-DL" part)

| Reasoning | Question it answers | Engine | Status |
|-----------|---------------------|--------|--------|
| OWL-DL (Pellet/HermiT) | "Does the design contradict the vocabulary?" (A1–A5); trace consistency | engine load check, `dl_trace_consistency` oracle | exists; Part A sharpens it |
| SHACL / CWA | "Is the design structurally complete?" (M1–M7); "does collected data conform?" | pySHACL | data side exists; meta-shapes are Part B |
| Workflow soundness (Petri-net style, van der Aalst) | "Does every run terminate? Is every form reachable? Can every loop exit?" over the BBO layer | BPMN export exists → check option-to-complete / no-dead-activity on it | **new**; the natural third checker, and the honest answer to loops — M5 approximates reachability, soundness proves it |
| Temporal (LTL over traces) | "Every rejected submit is eventually followed by the same form" and similar run properties | checkable over the tester's existing `TraceStep` sequences | cheap to add to the oracle family later |

The matrix is also the paper's framing: one generated artifact, four
complementary logics, each catching a failure class the others cannot —
with the agentic generator as the producer that makes the checkers
load-bearing.

## Suggested implementation order

1. **A5 + Part A axioms into `obop.owl`**, plus the `owl:AllDifferent`
   emission and the audit of existing models (A2 caveat). Small, no LLM,
   immediately strengthens the *existing* DL oracle.
2. **`fam-meta.shapes.ttl` + generator post-condition + `fam_well_formed`
   oracle.** Also LLM-free; the deterministic generator and both example
   shapes give instant test coverage.
3. **IR edit operations + builder re-render** behind a plain Python API
   (no LLM yet) — unit-testable: apply ops to the restaurant draft, assert
   the checkers stay green / turn red as intended.
4. **The LLM loop** on top (OllamaDecider-style, schema above).
5. Workflow-soundness checker on the BPMN export (independent track).

Steps 1–3 are each a normal, fully testable commit with no research risk;
the uncertainty is concentrated in step 4, where the instrumentation from
steps 1–3 is exactly what measures it.
