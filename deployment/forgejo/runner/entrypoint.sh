#!/bin/sh
set -eu

# Registration state lives in /data/.runner on a named volume, so this only
# runs once. The guard matters because re-registering with an already-consumed
# token fails, which would otherwise break every `docker compose restart`.
if [ ! -f /data/.runner ]; then
  if [ -z "${FORGEJO_RUNNER_TOKEN:-}" ]; then
    echo "ERROR: this runner is not registered and FORGEJO_RUNNER_TOKEN is empty." >&2
    echo "Get one from Site Administration -> Actions -> Runners -> Create new runner," >&2
    echo "put it in .env, then run: docker compose up -d runner" >&2
    exit 1
  fi
  echo "==> registering runner with ${FORGEJO_INSTANCE_URL}"
  forgejo-runner register \
    --no-interactive \
    --instance "${FORGEJO_INSTANCE_URL}" \
    --token "${FORGEJO_RUNNER_TOKEN}" \
    --name "${RUNNER_NAME}" \
    --labels "${RUNNER_LABELS}"
else
  echo "==> already registered, skipping"
fi

echo "==> starting runner daemon"
exec forgejo-runner daemon --config /data/config.yml
