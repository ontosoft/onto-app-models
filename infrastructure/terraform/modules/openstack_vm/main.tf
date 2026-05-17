terraform {
  required_providers {
    openstack = {
      source = "terraform-provider-openstack/openstack"
    }
  }
}

# Register the deploy public key as an OpenStack keypair. Only the public
# half is sent to OpenStack; the private key never enters Terraform state.
resource "openstack_compute_keypair_v2" "deploy" {
  name       = "${var.name}-key"
  public_key = var.public_key
}

resource "openstack_compute_instance_v2" "vm" {
  name        = var.name
  image_name  = var.image
  flavor_name = var.flavor
  key_pair    = openstack_compute_keypair_v2.deploy.name

  user_data       = var.user_data
  security_groups = var.security_groups

  network {
    name = var.network_name
  }

  metadata = var.metadata
}

resource "openstack_networking_floatingip_v2" "fip" {
  pool    = var.floating_ip_pool
  port_id = openstack_compute_instance_v2.vm.network[0].port
}
