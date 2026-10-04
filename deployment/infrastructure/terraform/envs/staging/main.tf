# The staging Docker host. Cluster-specific values (image, flavor, networks,
# how Ansible connects) live in variables.tf; this file only wires them to
# the module.

# No user_data: everything that prepares the host lives in the deploy
# playbook. cloud-init cannot handle the Cinder volume (it is attached only
# after the instance reports ACTIVE - a race cloud-init lost on this
# cluster), and its swapfile necessarily landed on the 10 GB root disk,
# which it filled to 100% together with the GGUF. The playbook puts both
# swap and model_files on the data volume instead.

module "vm" {
  source = "../../modules/openstack_vm"

  name       = "staging-onto-app"
  image      = var.image
  flavor     = var.flavor
  public_key = var.ssh_public_key

  network_name = var.network_name
  connect_via  = var.connect_via

  # Second interface for public IPv4 next to the IPv6 primary (A record and
  # ACME http-01 reachability). null = single-homed.
  secondary_network_name = var.secondary_network_name
  secondary_subnet_name  = var.secondary_subnet_name

  # Referencing the resource rather than a bare name gives Terraform the
  # dependency, so the group and its rules exist before the instance is
  # built.
  security_groups = ["default", openstack_networking_secgroup_v2.ontoapp_vm.name]

  # The secondary port needs IDs (a plan-time name lookup cannot resolve the
  # group this plan creates). "default" pre-exists in every tenant, so its
  # lookup is safe at plan time.
  secondary_security_group_ids = [
    data.openstack_networking_secgroup_v2.default.id,
    openstack_networking_secgroup_v2.ontoapp_vm.id,
  ]

  docker_data_volume_size_gb = var.docker_data_volume_size_gb

  metadata = {
    env  = "staging"
    role = "docker"
  }
}

output "vm_ip" {
  value = module.vm.vm_ip
}

# The address the A record for the app hostname points at.
output "vm_ipv4" {
  value = module.vm.secondary_ipv4
}

# Consumed by the Ansible step that writes the netplan config.
output "vm_ipv4_gateway" {
  value = module.vm.secondary_gateway_ipv4
}

output "vm_ipv4_mac" {
  value = module.vm.secondary_mac
}
