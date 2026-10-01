variable "ssh_public_key" {
  description = "SSH public key for the Forgejo host's deploy keypair. Supplied via TF_VAR_ssh_public_key."
  type        = string
}

# Ranges allowed to reach SSH. Same reasoning as envs/staging: the
# defaults are committed so a reviewer can see from security_group.tf alone
# whether port 22 is campus-only, and widening it stays an auditable change.
variable "ssh_source_cidr_ipv4" {
  description = "IPv4 range allowed to reach port 22 (DHBW campus)."
  type        = string
  default     = "141.72.0.0/16"

  validation {
    condition     = can(cidrhost(var.ssh_source_cidr_ipv4, 0))
    error_message = "ssh_source_cidr_ipv4 must be a valid IPv4 CIDR, e.g. 141.72.0.0/16."
  }
}

variable "ssh_source_cidr_ipv6" {
  description = "IPv6 range allowed to reach port 22 (DHBW campus)."
  type        = string
  default     = "2001:7c0:1b20::/48"

  validation {
    condition     = can(cidrhost(var.ssh_source_cidr_ipv6, 0))
    error_message = "ssh_source_cidr_ipv6 must be a valid IPv6 CIDR, e.g. 2001:7c0:1b20::/48."
  }
}

# Ranges allowed to reach the web UI. Separate from the SSH variables above
# even though the defaults match: the two are independent controls, and sharing
# one variable would make "widen SSH for a moment" silently expose the UI too.
#
# Restricting these means the ACME http-01 and tls-alpn-01 challenges can no
# longer work — the CA has to reach 80/443 from the public internet for either.
# Caddy must use dns-01 on this host (see forgejo/caddy/).
variable "web_source_cidr_ipv4" {
  description = "IPv4 range allowed to reach ports 80/443 (DHBW campus / VPN)."
  type        = string
  default     = "141.72.0.0/16"

  validation {
    condition     = can(cidrhost(var.web_source_cidr_ipv4, 0))
    error_message = "web_source_cidr_ipv4 must be a valid IPv4 CIDR, e.g. 141.72.0.0/16."
  }
}

variable "web_source_cidr_ipv6" {
  description = "IPv6 range allowed to reach ports 80/443 (DHBW campus / VPN)."
  type        = string
  default     = "2001:7c0:1b20::/48"

  validation {
    condition     = can(cidrhost(var.web_source_cidr_ipv6, 0))
    error_message = "web_source_cidr_ipv6 must be a valid IPv6 CIDR, e.g. 2001:7c0:1b20::/48."
  }
}

# NETWORK
#
# connect_via selects one of three ways to reach the host — IPv4 or IPv6, with
# a fixed address or a floating one:
#
#   fixed_ipv4     the instance's fixed IPv4, for networks whose IPv4 range is
#                  publicly routable
#   fixed_ipv6     the instance's fixed IPv6
#   floating_ipv4  a floating IP drawn from floating_ip_pool, for networks
#                  whose fixed IPv4 is private
#
# IPv6 is selected here, matching envs/staging. Anyone deploying this on their
# own OpenStack chooses the network and address family that suit their tenant;
# the variables below are the only place that changes.
#
# Whatever is chosen, the host must be able to reach the staging VM — the
# runner's job containers connect to it over SSH from here.
variable "network_name" {
  description = "OpenStack network the Forgejo host attaches to."
  type        = string
  default     = "DHBWV6"
}

variable "secondary_network_name" {
  description = "Second network for dual-stack. null = single-homed."
  type        = string
  default     = "DHBWv4"
}

# DHBWv4 has two IPv4 subnets; the -188 one is where the staging VM lands, so
# the forge keeps it company.
variable "secondary_subnet_name" {
  description = "IPv4 subnet within secondary_network_name."
  type        = string
  default     = "DHBWv4-188"
}

variable "connect_via" {
  description = "Which address Ansible connects to. See modules/openstack_vm/variables.tf."
  type        = string
  default     = "fixed_ipv6"

  validation {
    condition     = contains(["fixed_ipv4", "fixed_ipv6", "floating_ipv4"], var.connect_via)
    error_message = "connect_via must be \"fixed_ipv4\", \"fixed_ipv6\", or \"floating_ipv4\"."
  }
}

variable "floating_ip_pool" {
  description = "External network to allocate a floating IP from. Only used when connect_via = \"floating_ipv4\"."
  type        = string
  default     = ""
}

# Sized for what actually accumulates on this host: the Forgejo git
# repositories, its Postgres, and the deploy job image — node plus Terraform,
# Ansible and Trivy runs to several hundred MB on its own, and a new layer set
# is written every time job-image/Dockerfile changes.
variable "docker_data_volume_size_gb" {
  description = "Cinder volume for /var/lib/docker. 0 disables it."
  type        = number
  default     = 50
}
