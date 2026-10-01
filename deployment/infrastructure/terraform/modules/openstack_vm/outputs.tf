output "vm_ip" {
  description = "Address used to reach the VM, selected by connect_via."
  value = (
    var.connect_via == "floating_ipv4" ? openstack_networking_floatingip_v2.fip[0].address :
    var.connect_via == "fixed_ipv6" ? openstack_compute_instance_v2.vm.network[0].fixed_ip_v6 :
    openstack_compute_instance_v2.vm.network[0].fixed_ip_v4
  )
}

output "vm_name" {
  value = openstack_compute_instance_v2.vm.name
}

# null when single-homed. The address an A record points at, plus what Ansible
# needs to route replies back out of the secondary interface.
output "secondary_ipv4" {
  description = "Fixed IPv4 of the secondary interface."
  value       = one(openstack_networking_port_v2.secondary[*].all_fixed_ips[0])
}

output "secondary_gateway_ipv4" {
  value = one(data.openstack_networking_subnet_v2.secondary_v4[*].gateway_ip)
}

# Netplan matches on this rather than a name like ens4, which depends on probe
# order and is not stable across reboots.
output "secondary_mac" {
  value = one(openstack_networking_port_v2.secondary[*].mac_address)
}

output "key_pair_name" {
  value = openstack_compute_keypair_v2.deploy.name
}
