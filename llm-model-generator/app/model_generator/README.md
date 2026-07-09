# model_generator

Turn a **SHACL shapes file** into a **complete, runnable OntoUI application** that
guides a user through entering data — producing a knowledge graph that conforms
to those shapes.

```
SHACL shapes  ──►  model_generator  ──►  OntoUI model (BBO process + OBOP UI + SHACL)
                                          │
                                          └─► owlprocessor runs it as a real app
                                              (multi-step forms → validated knowledge graph)
```

The same engine that runs the hand-written example models runs the generated
ones unchanged — verified end-to-end in the browser for both a single-field form
and the full 4-subprocess restaurant, generated from a ~25-line shapes file.

---

## Why this matters

A SHACL shapes file already formalizes *what valid data looks like* for a domain.
This tool reuses it as the single source of truth to also generate the **UI** and
the **runtime validation** — three things that are normally built and maintained
separately. The research-relevant consequences:

1. **Democratized KG population** — domain experts populate a knowledge graph
   without writing RDF/SPARQL. This targets the biggest bottleneck in applied
   semantic web: getting good *instance* data in.
2. **Conformance by construction** — SHACL constraints are enforced at entry
   time, so the output graph is valid by design (large downstream data-quality
   saving).
3. **Schema evolution = regeneration** — when the ontology changes, regenerate
   the app instead of re-hand-coding forms.
4. **Process, not just forms** — the BBO/OBOP layer adds a *workflow*
   (multi-step entry, submit/cancel, a final validation). It generates an
   interactive *application*, not a single form per shape.

## Where it is useful

Domains that have (a) formalized SHACL/ontologies, (b) domain-expert (non-RDF)
contributors, and (c) real cost to bad data:

- **Research data management / FAIR & Open Science** — conformant metadata
  capture (DCAT-AP, schema.org, domain profiles).
- **Life sciences / biomedical** — OBO ontologies, FHIR-RDF, sample/biobank
  annotation, clinical registries.
- **Environmental & geospatial monitoring** — SOSA/SSN observations, ENVO-typed
  sampling, field data collection.
- **Cultural heritage / GLAM** — CIDOC-CRM, Europeana EDM cataloguing.
- **Industry 4.0 / digital twins** — Asset Administration Shells, product/asset
  descriptions.
- **Public sector / open government data** — EU Core Vocabularies, CPSV-AP.
- **Citizen science** — Darwin Core biodiversity records and similar.
- **Enterprise data governance / MDM** — internal ontologies as data contracts.
- **KG bootstrapping & teaching** — stand up a throwaway data-entry app to seed
  test instances, or teach SHACL/KG construction by "define a shape → get an app".

Less suited to: highly dynamic/conditional UIs beyond what shapes express, bulk
ingestion (use R2RML/RML), or domains with no formalized shapes.

## What is distinctive (vs. existing SHACL-to-form tools)

- **SHACL + BBO + OBOP** — generates an *executable application with a workflow*,
  not just a static form.
- **Self-validating models** — SHACL is used both to generate the app and to
  validate the generated *model itself*.
- **Hybrid rule-based + LLM-agent generation** — a deterministic rule core builds
  the structure; an LLM enriches the semantics it underspecifies (labels, widget
  hints, ordering); an agent drives a *generate → run → validate → repair* loop.

## How it works

A deterministic transform (no LLM in the core, so output is reproducible):

| SHACL element | becomes |
|---|---|
| `sh:NodeShape` (+ `sh:targetClass`) | one self-contained data-entry **subprocess** + an OBOP **block** + a runtime **shape** |
| `sh:property` | a **form field** bound to the property + a property shape |
| (per subprocess) | the BBO chain `start → form → user → gateway →(submit) save → confirmation → notification → end`; `(cancel) abort → cancel-end` |
| (per model) | subprocesses chained in the main process, then **one final SHACL validation**, then end |
| `sh:order` on a shape | the subprocess sequence |

Built as rdflib triples (no string-template/whitespace pitfalls). Every generated
model is gated on: parses, `validate_model() == 0`, and the factory builds a form
per block.

### Package layout
- `ir.py` — `EntitySpec` / `PropSpec` (the parsed shapes).
- `shacl_reader.py` — SHACL NodeShapes → IR.
- `templates.py` — the rule core that emits the model triples.
- `builder.py` — `generate_appmodel_from_shacl(shapes) -> {rdf, jsonld}` (dual-write ready).
- `__main__.py` — CLI.
- `examples/*.shapes.ttl` — input fixtures (string-form, restaurant).

## Usage

```python
from model_generator import generate_appmodel_from_shacl

gm = generate_appmodel_from_shacl(open("shapes.ttl").read())
gm.rdf      # Turtle (source of truth, -> knowledge_graph_rdf)
gm.jsonld   # JSON-LD object (-> knowledge_graph_json, JSONB)
```

```bash
# CLI (run from llm-model-generator/app)
python -m model_generator model_generator/examples/restaurant.shapes.ttl -o model.ttl
```

## Status

- **Phase 1** ✅ — single-entity generation; validates, runs to completion (engine + browser).
- **Phase 2** ✅ — multi-entity (restaurant from 4 shapes); 0 issues, correct order, runs to completion (engine + browser).
- **Phase 3** — meta-SHACL self-check.
- **Phase 4** — `POST /appmodels/generate-from-shacl` endpoint (CLI already in).
- **Phase 5** — Ollama enrichment hook (labels/widgets) behind a flag.
- **Phase 6** — generalized Playwright + agent repair loop.

> Note: the runtime engine is single-tenant; the automated test/repair loop
> (Phase 6) must reset the engine between model runs.
