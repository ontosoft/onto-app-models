variable "name" {}
variable "image" {}
variable "flavor" {}

# SSH public key material. Terraform registers this as an OpenStack keypair
# so the runner's private key always matches what is injected into the VM.
variable "public_key" {
  type = string
}

variable "network_name" {}

# Which address vm_ip returns - the address Ansible connects to:
#
#   fixed_ipv4     the instance's fixed IPv4. Correct when the network's IPv4
#                  subnet is publicly routable, as DHBW and DHBWv4 are.
#   fixed_ipv6     the instance's fixed IPv6, e.g. on DHBWV6.
#   floating_ipv4  allocate a floating IP from floating_ip_pool and use that.
#                  Needed when the network's fixed IPv4 is private.
#
# One variable rather than a separate address family and floating-IP flag,
# because those two would allow a fourth combination that does not exist:
# floating IPs are IPv4-only in OpenStack, so "floating IPv6" is meaningless.
variable "connect_via" {
  type = string

  validation {
    condition     = contains(["fixed_ipv4", "fixed_ipv6", "floating_ipv4"], var.connect_via)
    error_message = "connect_via must be \"fixed_ipv4\", \"fixed_ipv6\", or \"floating_ipv4\"."
  }
}

# Only consulted when connect_via = "floating_ipv4".
variable "floating_ip_pool" {
  type    = string
  default = ""
}

variable "security_groups" {
  type = list(string)
}

# Second network for dual-stack, e.g. "DHBWv4" next to a DHBWV6 primary.
# null = single-homed, which is what every existing caller gets.
variable "secondary_network_name" {
  type    = string
  default = null
}

# Required when the secondary network has more than one IPv4 subnet, as DHBWv4
# does. Leaving it null there fails the plan rather than picking one.
variable "secondary_subnet_name" {
  type    = string
  default = null
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
