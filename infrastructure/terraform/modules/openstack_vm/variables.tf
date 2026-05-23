variable "name" {}
variable "image" {}
variable "flavor" {}

# SSH public key material. Terraform registers this as an OpenStack keypair
# so the runner's private key always matches what is injected into the VM.
variable "public_key" {
  type = string
}

variable "network_name" {}

# Whether to allocate an OpenStack floating IP. Set to false when the deployer
# is on the same internal network as the VM (e.g. on-campus / VPN reaches the
# project network directly); the module then exposes the fixed IP via vm_ip.
variable "assign_floating_ip" {
  type    = bool
  default = true
}

# Only consulted when assign_floating_ip = true.
variable "floating_ip_pool" {
  type    = string
  default = ""
}

variable "security_groups" {
  type = list(string)
}

variable "metadata" {
  type = map(string)
}

variable "user_data" {
  type    = string
  default = null
}

# Size in GB of a Cinder data volume attached to the VM; the env's user_data
# is expected to format and mount it at /var/lib/docker so container storage
# is decoupled from the (small) root disk. 0 = no volume.
variable "docker_data_volume_size_gb" {
  type    = number
  default = 0
}