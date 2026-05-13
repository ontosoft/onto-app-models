terraform {
  required_providers {
    openstack = {
      source = "terraform-provider-openstack/openstack"
    }
  }
}

resource "openstack_compute_instance_v2" "vm" {
  name        = var.name
  image_name  = var.image
  flavor_name = var.flavor
  key_pair    = var.key_pair

  user_data = var.user_data
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
