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
  count   = var.assign_floating_ip ? 1 : 0
  pool    = var.floating_ip_pool
  port_id = openstack_compute_instance_v2.vm.network[0].port
}

# Optional Cinder volume for container storage (mounted at /var/lib/docker by
# cloud-init in user_data). Sized independently of the VM flavor.
resource "openstack_blockstorage_volume_v3" "docker_data" {
  count = var.docker_data_volume_size_gb > 0 ? 1 : 0
  name  = "${var.name}-docker-data"
  size  = var.docker_data_volume_size_gb
}

resource "openstack_compute_volume_attach_v2" "docker_data" {
  count       = var.docker_data_volume_size_gb > 0 ? 1 : 0
  instance_id = openstack_compute_instance_v2.vm.id
  volume_id   = openstack_blockstorage_volume_v3.docker_data[0].id
}
