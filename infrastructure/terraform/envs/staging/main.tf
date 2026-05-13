# Module is used to define things in one place
# and achieve DRY
module "vm" {
  source = "../../modules/openstack_vm"

  name        = "staging-docker"
  image       = "Ubuntu 22.04"
  flavor      = "mb1.medium" 
  key_pair    = "mac-schluessel"
  network_name = "DHBW" 
  floating_ip_pool = "public"

  security_groups = ["default", "ssh", "http-https"]

  user_data = <<-EOF
    #cloud-config
    swap:
      filename: /swapfile
      size: 4294967296
      maxsize: 4294967296
  EOF

  metadata = {
    env  = "staging"
    role = "docker"
  }
}

output "vm_ip" {
  value = module.vm.vm_ip
}