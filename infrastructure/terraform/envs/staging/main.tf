# Module is used to define things in one place
# and achieve DRY
module "vm" {
  source = "../../modules/openstack_vm"

  name         = "staging-docker"
  image        = "Ubuntu 22.04"
  flavor       = "m1.extra_large"
  public_key   = var.ssh_public_key
  network_name = "DHBW"

  # No public floating-IP pool is usable from off-campus on this OpenStack;
  # deploy reaches the VM via its fixed IP on the network (requires the
  # operator to be in the network / a full-tunnel VPN). Flip to true and set
  # floating_ip_pool when a routable pool is available.
  assign_floating_ip = false

  security_groups = ["default", "ssh", "http-https"]

  # Container storage on a separate Cinder volume

  docker_data_volume_size_gb = 0
  # Cinder volume is only installed if docker_data_volume_size_gb > 0

  # cloud-init: swap + format/mount the attached Cinder volume at
  # /var/lib/docker BEFORE Docker is installed by Ansible.
  user_data = <<-EOF
    #cloud-config
    swap:
      filename: /swapfile
      size: 4294967296
      maxsize: 4294967296
    runcmd:
      - |
        set -eu
        for _ in $(seq 1 60); do [ -b /dev/vdb ] && break; sleep 2; done
        blkid /dev/vdb >/dev/null 2>&1 || mkfs.ext4 -F -L docker-data /dev/vdb
        mkdir -p /var/lib/docker
        mountpoint -q /var/lib/docker || mount /dev/vdb /var/lib/docker
        grep -q '^/dev/vdb /var/lib/docker ' /etc/fstab \
          || echo '/dev/vdb /var/lib/docker ext4 defaults,nofail 0 2' >> /etc/fstab
  EOF

  metadata = {
    env  = "staging"
    role = "docker"
  }
}

output "vm_ip" {
  value = module.vm.vm_ip
}