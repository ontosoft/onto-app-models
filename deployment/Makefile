# Entry points for deployment way 1 (act from an operator's machine).
# Run from this directory: make deploy-staging DEPLOY_KEY=... STAGING_ENV=...

# Unencrypted private key for the deploy (public half becomes the OpenStack keypair).
DEPLOY_KEY ?= ~/.ssh/openstack-deploy
# The filled-in runtime .env (see .env.staging.example). Lives OUTSIDE the repo.
STAGING_ENV ?=
# plan = stop before any change; apply = full deploy.
MODE ?= apply

REPO_ROOT := $(abspath ..)
WORKFLOW := .forgejo/workflows/staging.yml

# The workflow runs on the `deploy` label (the Forgejo runner's). act knows no
# such platform, so map it to a generic runner image here.
ACT_PLATFORM := deploy=catthehacker/ubuntu:act-latest

.PHONY: help deploy-staging plan-staging
help:
	@echo "deploy-staging   Deploy staging via act (needs VPN). MODE=$(MODE)"
	@echo "plan-staging     Same, but terraform plan only (MODE=plan)."
	@echo "                 Vars: DEPLOY_KEY=$(DEPLOY_KEY) STAGING_ENV=$(STAGING_ENV)"

plan-staging: MODE = plan
plan-staging: deploy-staging

deploy-staging:
	@test -f .secrets || { echo "deployment/.secrets missing - copy .secrets.template and fill in STAGING_OS_*"; exit 1; }
	@test -n "$(STAGING_ENV)" || { echo "Set STAGING_ENV=/path/to/staging.env (see .env.staging.example)"; exit 1; }
	cd $(REPO_ROOT) && act workflow_dispatch -W $(WORKFLOW) --bind \
	  -P $(ACT_PLATFORM) \
	  --input mode=$(MODE) \
	  --secret-file deployment/.secrets \
	  -s SSH_PRIVATE_KEY="$$(cat $(DEPLOY_KEY))" \
	  -s STAGING_ENV_FILE="$$(cat $(STAGING_ENV))"
