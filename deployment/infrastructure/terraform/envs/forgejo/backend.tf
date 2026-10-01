terraform {
  required_version = ">= 1.5.0"

  # Local state, deliberately — this environment is the bootstrap.
  #
  # The planned end state stores the staging environment's state in a Postgres
  # running on the VM this environment creates. Storing THIS state there too
  # would be circular: the database would have to exist before the machine
  # hosting it could be built.
  #
  # The split is the usual one between bootstrap and managed infrastructure.
  # This VM is created once and changes rarely; a state file on the operator's
  # machine is proportionate to that.
  #
  # CONSEQUENCE: terraform.tfstate here is not in git and not on the runner. It
  # exists only where the last apply ran. Back it up together with the Forgejo
  # dumps — losing it means Terraform can no longer manage the VM, and a fresh
  # apply would build a second one alongside the first.
  backend "local" {}

  required_providers {
    openstack = {
      source  = "terraform-provider-openstack/openstack"
      version = "~> 3.4"
    }
  }
}
