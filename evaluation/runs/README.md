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

Reports for runs 1–5 were written to a session scratchpad and lost; the
step transcripts are preserved in the research notes. Key finding of the
2×2 matrix (7B/14B × original/sharpened): the `move_entity`-without-
`position` failure is schema-rooted — the flat `EDIT_SCHEMA` could not make
`position` per-action required, and constrained decoding guarantees valid
JSON but not action-specific fields. Neither prompt sharpening nor model
scale removes it; the larger model hits it more often because it attempts
form reordering at all. Fixed by making `position` globally required in
`backend/app/model_agent/actions.py` (runs ≥ 6 use the fixed schema).

Runs 6–9 repeated the full matrix with the fixed schema (staging Ollama,
8 vCPU; original-prompt cells from a worktree that reverts only loop.py
to its pre-sharpening version, so the prompt is the sole variable):
**4/4 confirmed, 0 repair rounds** — including both cells that failed
before. `move_entity` now always carries its position. The schema, not
prompt wording or model scale, was the binding constraint.
