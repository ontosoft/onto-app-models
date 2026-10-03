variable "ssh_public_key" {
  description = "SSH public key for the staging deploy keypair. Supplied by CI via TF_VAR_ssh_public_key (derived from the SSH_PRIVATE_KEY secret)."
  type        = string
}

# ---------------------------------------------------------------------------
# Cluster parameters.
#
# Defaults describe the current target: the DHBW cluster (IPv6-only primary
# network, public IPv4 via a second interface). Deploying
# to another cluster means overriding these with a tfvars file, not editing
# code: terraform apply -var-file=clusters/<cluster>.tfvars
# ---------------------------------------------------------------------------

# 22.04 deliberately: with the 24.04 image the guest never configured its
# DHBWV6 IPv6 address (unreachable even for neighbor ping from the same
# /64), while 22.04 is proven on this cluster. Revisit newer images with a
# throwaway VM, not with staging.
variable "image" {
  description = "Glance image name for the VM."
  type        = string
  default     = "Ubuntu 22.04"
}

# The app stack is heavy (Ollama serves a local GGUF model). Override in
# tfvars if the model needs more RAM than the flavor provides.
variable "flavor" {
  description = "Nova flavor name for the VM."
  type        = string
  default     = "gp1.large"
}

variable "network_name" {
  description = "Primary network the VM boots on."
  type        = string
  default     = "DHBWV6"
}

# See the module's connect_via docs. On DHBWV6 the VM's public address is
# IPv6, so Ansible connects over IPv6.
variable "connect_via" {
  description = "Which address vm_ip returns (fixed_ipv4 | fixed_ipv6 | floating_ipv4)."
  type        = string
  default     = "fixed_ipv6"
}

# Second interface for public IPv4 (A record + ACME http-01 reachability).
# null = single-homed.
variable "secondary_network_name" {
  description = "Optional second network for dual-stack."
  type        = string
  default     = "DHBWv4"
}

# DHBWv4 has two IPv4 subnets; the port must draw its address from the one
# whose gateway the reply route uses.
variable "secondary_subnet_name" {
  description = "IPv4 subnet of the secondary network to pin the port to."
  type        = string
  default     = "DHBWv4-188"
}

# Root disks on this cluster are small (10 GB on gp1.*); container images and
# volumes live on a Cinder volume mounted at /var/lib/docker. 0 = no volume
# (container data on the root disk), for clusters with large root disks.
variable "docker_data_volume_size_gb" {
  description = "Size of the Cinder volume for /var/lib/docker; 0 disables it."
  type        = number
  default     = 50
}

# ---------------------------------------------------------------------------
# SSH ingress ranges.
#
# The defaults are committed on purpose. These are a security control, and a
# reviewer reading security_group.tf needs to be able to tell whether port 22
# is campus-only or open to the world. Committing them also gives the range a
# git history, so widening it is an auditable change rather than an invisible
# one. Both remain overridable per cluster via tfvars / TF_VAR_*.
# ---------------------------------------------------------------------------

variable "ssh_source_cidr_ipv4" {
  description = "IPv4 range allowed to reach port 22 (DHBW campus)."
  type        = string
  default     = "141.72.0.0/16"

  validation {
    condition     = can(cidrhost(var.ssh_source_cidr_ipv4, 0))
    error_message = "ssh_source_cidr_ipv4 must be a valid IPv4 CIDR, e.g. 141.72.0.0/16."
  }
}

# 2001:7c0:1b20::/48 is the campus allocation (registered to DHBW Mannheim in
# RIPE) - the range an operator connects in from, not the VM allocation pool.
variable "ssh_source_cidr_ipv6" {
  description = "IPv6 range allowed to reach port 22 (DHBW campus)."
  type        = string
  default     = "2001:7c0:1b20::/48"

  validation {
    condition     = can(cidrhost(var.ssh_source_cidr_ipv6, 0))
    error_message = "ssh_source_cidr_ipv6 must be a valid IPv6 CIDR, e.g. 2001:7c0:1b20::/48."
  }
}