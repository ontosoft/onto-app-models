

module "vm" {
  source = "../../modules/openstack_vm"

  name             = "prod-docker"
  image            = "Ubuntu 22.04"
  flavor           = "mb1.medium"
  public_key       = var.ssh_public_key
  network_name     = "private"
  floating_ip_pool = "public"

  security_groups = ["default", "ssh"]

  metadata = {
    env  = "prod"
    role = "docker"
  }
}

output "vm_ip" {
  value = module.vm.vm_ip
}