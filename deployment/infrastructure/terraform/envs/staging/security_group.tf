# Security group for the staging VM.
#
# Managed here rather than referencing pre-existing groups by name (the old
# setup used hand-made "ssh" / "http-https" groups, an undocumented
# prerequisite that made a fresh apply on a new cluster fail). Creating the
# group in Terraform makes the environment self-contained and portable.
#
# WHAT IS DELIBERATELY NOT OPENED
# The compose stack publishes internal services on the host (backend API 8000,
# frontend dev port, Postgres 5432, Redis, Ollama 11434, adminer). The VM's
# addresses are publicly routable, so this security group is the ONLY thing
# keeping those services off the internet. Do not add rules for them - the
# public entry point is the reverse proxy on 80/443; use an SSH tunnel for
# anything else.

# The tenant's pre-existing default group; looked up for its ID because the
# secondary port takes IDs, not names.
data "openstack_networking_secgroup_v2" "default" {
  name = "default"
}

resource "openstack_networking_secgroup_v2" "ontoapp_vm" {
  name        = "staging-onto-app-sg"
  description = "Staging Docker host: SSH for Ansible, HTTP/HTTPS for the app"

  # delete_default_rules stays false, so the group keeps OpenStack's default
  # allow-all egress. The VM needs outbound access for apt, image pulls,
  # Galaxy, the GGUF model download and ACME.
}

resource "openstack_networking_secgroup_rule_v2" "ssh" {
  security_group_id = openstack_networking_secgroup_v2.ontoapp_vm.id
  direction         = "ingress"
  ethertype         = "IPv4"
  protocol          = "tcp"
  port_range_min    = 22
  port_range_max    = 22
  remote_ip_prefix  = var.ssh_source_cidr_ipv4
  description       = "SSH for the Ansible deploy step (campus IPv4)"
}

# OpenStack security-group rules are per-ethertype: the IPv4 rules in this
# file do not filter IPv6 traffic at all. Without this rule, an
# IPv6-reachable VM would have port 22 governed by nothing here.
resource "openstack_networking_secgroup_rule_v2" "ssh_v6" {
  security_group_id = openstack_networking_secgroup_v2.ontoapp_vm.id
  direction         = "ingress"
  ethertype         = "IPv6"
  protocol          = "tcp"
  port_range_min    = 22
  port_range_max    = 22
  remote_ip_prefix  = var.ssh_source_cidr_ipv6
  description       = "SSH for the Ansible deploy step (campus IPv6)"
}

# Port 80 stays fully open on both families: besides the HTTPS redirect it
# answers the ACME http-01 challenge (the planned stock-Caddy TLS setup).
resource "openstack_networking_secgroup_rule_v2" "http" {
  security_group_id = openstack_networking_secgroup_v2.ontoapp_vm.id
  direction         = "ingress"
  ethertype         = "IPv4"
  protocol          = "tcp"
  port_range_min    = 80
  port_range_max    = 80
  remote_ip_prefix  = "0.0.0.0/0"
  description       = "HTTP - redirected to HTTPS, and the ACME http-01 challenge"
}

resource "openstack_networking_secgroup_rule_v2" "http_v6" {
  security_group_id = openstack_networking_secgroup_v2.ontoapp_vm.id
  direction         = "ingress"
  ethertype         = "IPv6"
  protocol          = "tcp"
  port_range_min    = 80
  port_range_max    = 80
  remote_ip_prefix  = "::/0"
  description       = "HTTP - redirected to HTTPS, and the ACME http-01 challenge (IPv6)"
}

resource "openstack_networking_secgroup_rule_v2" "https" {
  security_group_id = openstack_networking_secgroup_v2.ontoapp_vm.id
  direction         = "ingress"
  ethertype         = "IPv4"
  protocol          = "tcp"
  port_range_min    = 443
  port_range_max    = 443
  remote_ip_prefix  = "0.0.0.0/0"
  description       = "HTTPS - the application"
}

resource "openstack_networking_secgroup_rule_v2" "https_v6" {
  security_group_id = openstack_networking_secgroup_v2.ontoapp_vm.id
  direction         = "ingress"
  ethertype         = "IPv6"
  protocol          = "tcp"
  port_range_min    = 443
  port_range_max    = 443
  remote_ip_prefix  = "::/0"
  description       = "HTTPS - the application (IPv6)"
}

# ICMPv6 is not optional the way ICMP is on IPv4: Path MTU Discovery relies on
# "Packet Too Big" messages, and blocking them creates MTU black holes where a
# connection establishes but larger transfers hang - a TLS handshake that
# succeeds while the response never arrives. RFC 4890 advises against
# filtering ICMPv6 wholesale. It also makes the host pingable, which is worth
# something when the primary way in is IPv6.
resource "openstack_networking_secgroup_rule_v2" "icmpv6" {
  security_group_id = openstack_networking_secgroup_v2.ontoapp_vm.id
  direction         = "ingress"
  ethertype         = "IPv6"
  protocol          = "ipv6-icmp"
  remote_ip_prefix  = "::/0"
  description       = "ICMPv6 - required for Path MTU Discovery (RFC 4890)"
}
