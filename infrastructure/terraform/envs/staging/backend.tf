terraform {
  backend "local" {
    path = "terraform.tfstate"
  }

  required_providers {
    openstack = {
      source = "terraform-provider-openstack/openstack"
    }
  }
}