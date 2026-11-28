# Agentic-design evaluation runs

Durable archive for the design-agent experiment reports. Every run of the
agent writes a JSON report (`--report`); commit it here so results survive
machine cleanups and stay diffable.

## How to produce a run

From `backend/` (local Ollama) or via an SSH tunnel to the staging Ollama:

```bash
cd backend && set -a && source ../.env && set +a
uv run python -m app.model_agent app/model_generator/examples/restaurant.shapes.ttl \
  --model <ollama-model> \
  --ollama-host http://localhost:11435 \
  -o ../evaluation/runs/runN_<model>_<prompt>.ttl \
  --report ../evaluation/runs/runN_<model>_<prompt>.json
```

Naming: `runN_<model>_<prompt>.json`, e.g. `run6_qwen14b_sharpened.json`.
Note the schema/prompt variant in the table below with every run.

## Run log

| Run | Date | Model | Prompt | Schema | Result |
|---|---|---|---|---|---|
| 1 | 2026-11 | qwen2.5:7b-instruct | original | position optional | ✗ not confirmed — 20 steps burned without converging |
| 2 | 2026-11 | qwen2.5:7b-instruct | sharpened | position optional | ✓ confirmed in 6 steps |
| 4 | 2026-11-16 | qwen2.5:14b-instruct | original | position optional | ✗ repeat-guard abort at step 8 — 3× `move_entity` without `position` after 5 flawless edits |
| 5 | 2026-11-16 | qwen2.5:14b-instruct | sharpened | position optional | ✗ repeat-guard abort at step 12 — same failure after 9 good edits (incl. first `set_loop`) |
| 6 | 2026-11-17 | qwen2.5:7b-instruct | original | position required | ✓ confirmed in 4 steps, 0 repair rounds |
| 7 | 2026-11-17 | qwen2.5:7b-instruct | sharpened | position required | ✓ confirmed in 10 steps, 0 repair rounds |
| 8 | 2026-11-17 | qwen2.5:14b-instruct | original | position required | ✓ confirmed in 12 steps, 0 repair rounds |
| 9 | 2026-11-17 | qwen2.5:14b-instruct | sharpened | position required | ✓ confirmed in 12 steps, 0 repair rounds |
| 10 | 2026-11-17 | qwen2.5:14b-instruct | sharpened | dynamic enums | ✓ confirmed in 12 steps, 0 repair rounds |
| 11 | 2026-11-17 | qwen2.5:14b-instruct | sharpened | static (ablation) | ✓ confirmed in 12 steps, 0 repair rounds |
| 12 | 2026-11-24 | qwen2.5:14b-instruct | sharpened | dynamic enums | ✓ confirmed in 11 steps, 0 repair rounds — conference scenario |
| 13 | 2026-11-24 | qwen2.5:14b-instruct | sharpened | static (ablation) | ✓ confirmed in 11 steps, 0 repair rounds — conference scenario |

Reports for runs 1–5 were written to a session scratchpad and lost; the
step transcripts are preserved in the research notes. Key finding of the
2×2 matrix (7B/14B × original/sharpened): the `move_entity`-without-
`position` failure is schema-rooted — the flat `EDIT_SCHEMA` could not make
`position` per-action required, and constrained decoding guarantees valid
JSON but not action-specific fields. Neither prompt sharpening nor model
scale removes it; the larger model hits it more often because it attempts
form reordering at all. Fixed by making `position` globally required in
`backend/app/model_agent/actions.py` (runs ≥ 6 use the fixed schema).

Runs 10/11 are the dynamic-schema ablation pair (c6d193a, `--schema`
switch; reports ≥ 10 record their condition themselves): on the small
restaurant shapes both conditions produced STEP-IDENTICAL action
sequences and identical latency (~10.8 s/step) — a null result showing
the enums are cost-neutral; their protective value must be measured on
larger shape sets where dangling references actually occur.

Runs 12/13 repeated the ablation pair on the larger conference scenario
(`conference.shapes.ttl`, 7 entities / 21 fields / 7 relations, commit
5360e76; executed server-side, `--num-ctx 16384`): again step-identical
sequences, isomorphic output graphs, identical latency (~14.1 s/step),
both confirmed in 11 steps. New finding: BOTH conditions were rejected
twice for grouping "Reviewer name" with "Affiliation" — "Affiliation"
exists on two entities and the environment resolved it to the wrong
(author) form. Dynamic enums guard against nonexistent labels but not
against AMBIGUOUS ones; fixing that needs entity-scoped reference
resolution or per-step reasoning guards (improvement-ladder rungs 2–3).

Runs 6–9 repeated the full matrix with the fixed schema (staging Ollama,
8 vCPU; original-prompt cells from a worktree that reverts only loop.py
to its pre-sharpening version, so the prompt is the sole variable):
**4/4 confirmed, 0 repair rounds** — including both cells that failed
before. `move_entity` now always carries its position. The schema, not
prompt wording or model scale, was the binding constraint.
