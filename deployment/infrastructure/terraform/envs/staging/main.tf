# The staging Docker host. Cluster-specific values (image, flavor, networks,
# how Ansible connects) live in variables.tf; this file only wires them to
# the module.

locals {
  cloud_init_base = <<-EOT
    #cloud-config
    swap:
      filename: /swapfile
      size: 4294967296
      maxsize: 4294967296
  EOT

  # Format and mount the attached Cinder volume at /var/lib/docker BEFORE
  # Docker is installed by Ansible. Only appended when a volume is attached;
  # without it the wait loop below would stall the first boot for two
  # minutes and then error.
  cloud_init_docker_volume = <<-EOT
    runcmd:
      - |
        set -eu
        for _ in $(seq 1 60); do [ -b /dev/vdb ] && break; sleep 2; done
        blkid /dev/vdb >/dev/null 2>&1 || mkfs.ext4 -F -L docker-data /dev/vdb
        mkdir -p /var/lib/docker
        mountpoint -q /var/lib/docker || mount /dev/vdb /var/lib/docker
        grep -q '^/dev/vdb /var/lib/docker ' /etc/fstab \
          || echo '/dev/vdb /var/lib/docker ext4 defaults,nofail 0 2' >> /etc/fstab
  EOT

  user_data = var.docker_data_volume_size_gb > 0 ? "${local.cloud_init_base}${local.cloud_init_docker_volume}" : local.cloud_init_base
}

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
  user_data                  = local.user_data

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
