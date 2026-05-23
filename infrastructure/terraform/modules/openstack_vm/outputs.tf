output "vm_ip" {
  description = "Address used to reach the VM: the floating IP when allocated, otherwise the fixed IP on the project network."
  value = var.assign_floating_ip ? (
    openstack_networking_floatingip_v2.fip[0].address
    ) : (
    openstack_compute_instance_v2.vm.network[0].fixed_ip_v4
  )
}

output "vm_name" {
  value = openstack_compute_instance_v2.vm.name
}

output "key_pair_name" {
  value = openstack_compute_keypair_v2.deploy.name
}