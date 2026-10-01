# Optional second interface, so one host can serve both address families.
#
# Attached to the running instance instead of adding a second `network` block
# to it: that argument forces replacement, and staging keeps all container
# data on the root disk.

data "openstack_networking_network_v2" "secondary" {
  count = var.secondary_network_name == null ? 0 : 1
  name  = var.secondary_network_name
}

# The gateway Ansible routes replies through. A null name is simply omitted
# from the filter, which works only where the network has a single IPv4 subnet
# - DHBWv4 has two, so callers there must name one.
data "openstack_networking_subnet_v2" "secondary_v4" {
  count      = var.secondary_network_name == null ? 0 : 1
  network_id = data.openstack_networking_network_v2.secondary[0].id
  ip_version = 4
  name       = var.secondary_subnet_name
}

# The instance takes security groups by name, a port takes IDs - hence the
# lookup. Without it the port would fall back to "default", which allows no
# ingress at all, and the address would be up and unreachable.
data "openstack_networking_secgroup_v2" "secondary" {
  for_each = var.secondary_network_name == null ? toset([]) : toset(var.security_groups)
  name     = each.value
}

resource "openstack_networking_port_v2" "secondary" {
  count      = var.secondary_network_name == null ? 0 : 1
  name       = "${var.name}-secondary"
  network_id = data.openstack_networking_network_v2.secondary[0].id

  # Pinned to the same subnet the gateway above comes from. Left to Neutron,
  # the address could be drawn from the other subnet, and the routing rule
  # Ansible writes would point at a gateway that does not serve it.
  fixed_ip {
    subnet_id = data.openstack_networking_subnet_v2.secondary_v4[0].id
  }

  security_group_ids = [
    for g in data.openstack_networking_secgroup_v2.secondary : g.id
  ]
}

resource "openstack_compute_interface_attach_v2" "secondary" {
  count       = var.secondary_network_name == null ? 0 : 1
  instance_id = openstack_compute_instance_v2.vm.id
  port_id     = openstack_networking_port_v2.secondary[0].id
}
