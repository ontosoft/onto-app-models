variable "name" {}
variable "image" {}
variable "flavor" {}

# SSH public key material. Terraform registers this as an OpenStack keypair
# so the runner's private key always matches what is injected into the VM.
variable "public_key" {
  type = string
}

variable "network_name" {}
variable "floating_ip_pool" {}

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