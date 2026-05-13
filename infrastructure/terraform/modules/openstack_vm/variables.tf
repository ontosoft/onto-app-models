variable "name" {}
variable "image" {}
variable "flavor" {}
variable "key_pair" {}
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