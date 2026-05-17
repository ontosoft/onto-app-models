#!/usr/bin/env bash
#
# tf-local.sh — local Terraform driver for OntoUI infrastructure.
#
# Encapsulates everything we worked out by hand:
#   * loads the per-environment OpenStack application credential from .secrets
#     and maps <ENV>_OS_* -> OS_* (stripping the surrounding quotes / CR that
#     broke the manual `export` loop),
#   * supplies the `ssh_public_key` variable the Terraform config requires,
#   * runs terraform in the correct env directory.
#
# It mirrors what the GitHub Actions workflows do, for single-operator local
# use via the local state backend (see infrastructure/README.md).
#
# Usage:
#   infrastructure/scripts/tf-local.sh <staging|production> <action> [extra terraform args...]
#
#   action = init | plan | plan-destroy | apply | destroy
#
# Examples:
#   infrastructure/scripts/tf-local.sh staging plan-destroy
#   infrastructure/scripts/tf-local.sh staging destroy -auto-approve
#   SSH_KEY_FILE=~/.ssh/openstack-key \
#     infrastructure/scripts/tf-local.sh staging apply
#
# SSH key handling:
#   * destroy / plan / plan-destroy / init: a dummy key is fine (resources are
#     only read or removed), so no key is required.
#   * apply: you MUST provide a real key, otherwise the VM gets an unusable
#     keypair. Set SSH_KEY_FILE=/path/to/PRIVATE_key (its public half is
#     derived automatically) or export TF_VAR_ssh_public_key yourself.
#
set -euo pipefail

ENV="${1:?Usage: tf-local.sh <staging|production> <init|plan|plan-destroy|apply|destroy> [args...]}"
ACTION="${2:?Usage: tf-local.sh <staging|production> <init|plan|plan-destroy|apply|destroy> [args...]}"
shift 2

case "$ENV" in
  staging|production) ;;
  *) echo "ERROR: environment must be 'staging' or 'production' (got '$ENV')" >&2; exit 1 ;;
esac

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SECRETS_FILE="$REPO_ROOT/.secrets"
ENV_DIR="$REPO_ROOT/infrastructure/terraform/envs/$ENV"

[ -f "$SECRETS_FILE" ] || { echo "ERROR: $SECRETS_FILE not found" >&2; exit 1; }
[ -d "$ENV_DIR" ]      || { echo "ERROR: $ENV_DIR not found" >&2; exit 1; }

# Map <ENV-UPPER>_OS_* from .secrets into OS_*. Strip a trailing CR and one
# layer of surrounding double/single quotes (the .secrets values are quoted
# for `act`'s dotenv parser; a naive shell `export` keeps them literally).
# Secret values are never printed.
PREFIX="$(printf '%s' "$ENV" | tr '[:lower:]' '[:upper:]')_OS_"
while IFS='=' read -r k v; do
  case "$k" in
    "${PREFIX}"*)
      v="${v%$'\r'}"
      v="${v#\"}"; v="${v%\"}"
      v="${v#\'}"; v="${v%\'}"
      export "OS_${k#"${PREFIX}"}"="$v"
      ;;
  esac
done < "$SECRETS_FILE"

: "${OS_AUTH_URL:?no ${PREFIX}AUTH_URL found in .secrets — check the env prefix}"
echo ">> OpenStack credentials loaded for '$ENV' (region: ${OS_REGION_NAME:-unset})"

# ssh_public_key — required by the Terraform config (variable has no default).
if [ -z "${TF_VAR_ssh_public_key:-}" ]; then
  if [ -n "${SSH_KEY_FILE:-}" ]; then
    TF_VAR_ssh_public_key="$(ssh-keygen -y -f "$SSH_KEY_FILE")"
    export TF_VAR_ssh_public_key
    echo ">> ssh_public_key derived from \$SSH_KEY_FILE"
  elif [ "$ACTION" = "apply" ]; then
    echo "ERROR: 'apply' needs a real SSH key, otherwise the VM is unreachable." >&2
    echo "       Re-run with: SSH_KEY_FILE=/path/to/private_key $0 $ENV apply" >&2
    exit 1
  else
    export TF_VAR_ssh_public_key="dummy"
    echo ">> ssh_public_key=dummy (sufficient for '$ACTION')"
  fi
fi

cd "$ENV_DIR"
terraform init -input=false

case "$ACTION" in
  init)         : ;;
  plan)         terraform plan "$@" ;;
  plan-destroy) terraform plan -destroy "$@" ;;
  apply)        terraform apply "$@" ;;
  destroy)      terraform destroy "$@" ;;
  *) echo "ERROR: unknown action '$ACTION' (init|plan|plan-destroy|apply|destroy)" >&2; exit 1 ;;
esac
