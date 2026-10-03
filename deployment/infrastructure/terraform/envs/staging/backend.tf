terraform {
  required_version = ">= 1.5.0"

  # State lives in Postgres, not on a runner's disk: on a Forgejo runner, job
  # containers are destroyed after every run, and a local state file dies
  # with them (which is how the first apply's state was lost).
  #
  # The database is the forge stack's Postgres (database terraform_state,
  # reachable as db:5432 from job containers on the forge's compose
  # network). One database holds many projects' states side by side; the
  # schema below is ours, next to the sibling project's "staging" schema.
  #
  # The connection string comes from PG_CONN_STR in the environment rather
  # than -backend-config, which keeps the password out of git. The pg
  # backend takes a Postgres advisory lock per operation, so two concurrent
  # runs cannot corrupt the state.
  backend "pg" {
    schema_name = "onto_app_staging"
  }

  required_providers {
    openstack = {
      source  = "terraform-provider-openstack/openstack"
      version = "~> 3.4"
    }
  }
}
