variable "ssh_public_key" {
  description = "SSH public key for the production deploy keypair. Supplied by CI via TF_VAR_ssh_public_key (derived from the SSH_PRIVATE_KEY secret)."
  type        = string
}
