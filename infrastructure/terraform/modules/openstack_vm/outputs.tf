output "vm_ip" {
  value = openstack_networking_floatingip_v2.fip.address
}

output "vm_name" {
  value = openstack_compute_instance_v2.vm.name
}