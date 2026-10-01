# Security group for the Forgejo host.
#
# Nothing here is open to the internet. Unlike staging, which serves a public
# application, this host is internal infrastructure: only the maintainers and
# the runner ever need to reach it, and all of them arrive from the campus
# network or over VPN.
#
# THE ONE THING THIS COSTS
# Caddy cannot use the ACME http-01 or tls-alpn-01 challenge on this host —
# both require the CA to open a connection from the public internet to 80 or
# 443. Certificates must be obtained over dns-01: a TXT record written over
# RFC 2136, read by the CA from DNS, no inbound connection at all. See
# forgejo/caddy/Caddyfile and forgejo/caddy/Dockerfile.
#
# WHAT IS DELIBERATELY NOT OPENED AT ALL
# Forgejo listens on 3000 and Postgres on 5432, but neither belongs in this
# group. Caddy terminates TLS on 443 and proxies to Forgejo over the compose
# network, so 3000 is bound to 127.0.0.1 and never needs to be reachable from
# outside. Postgres holds the forgejo database — use an SSH tunnel if you need
# a psql session.
#
# Git over SSH (Forgejo's own sshd, published on 2222 because the host's sshd
# owns 22) is also not opened. Pushing over HTTPS works without it. Add a rule
# restricted to the campus ranges if the team wants key-based pushes.

resource "openstack_networking_secgroup_v2" "forgejo_vm" {
  name        = "ci-onto-app-sg"
  description = "CI host: SSH for Ansible, HTTP/HTTPS for the web UI, campus-only"

  # delete_default_rules stays false, so the group keeps OpenStack's default
  # allow-all egress. The host needs outbound access for apt, container
  # registries, and the runner's own jobs — which reach the staging VM and,
  # during a deploy, the OpenStack API.
}

resource "openstack_networking_secgroup_rule_v2" "ssh" {
  security_group_id = openstack_networking_secgroup_v2.forgejo_vm.id
  direction         = "ingress"
  ethertype         = "IPv4"
  protocol          = "tcp"
  port_range_min    = 22
  port_range_max    = 22
  remote_ip_prefix  = var.ssh_source_cidr_ipv4
  description       = "SSH for the Ansible setup step (campus IPv4)"
}

# OpenStack security-group rules are per-ethertype: the IPv4 rules in this file
# do not filter IPv6 traffic at all. Without this rule, an IPv6-reachable host
# would have port 22 governed by nothing here.
resource "openstack_networking_secgroup_rule_v2" "ssh_v6" {
  security_group_id = openstack_networking_secgroup_v2.forgejo_vm.id
  direction         = "ingress"
  ethertype         = "IPv6"
  protocol          = "tcp"
  port_range_min    = 22
  port_range_max    = 22
  remote_ip_prefix  = var.ssh_source_cidr_ipv6
  description       = "SSH for the Ansible setup step (campus IPv6)"
}

# 80 is kept open to the campus only for Caddy's redirect to HTTPS. It is not
# an ACME path here — see the note at the top of this file.
resource "openstack_networking_secgroup_rule_v2" "http" {
  security_group_id = openstack_networking_secgroup_v2.forgejo_vm.id
  direction         = "ingress"
  ethertype         = "IPv4"
  protocol          = "tcp"
  port_range_min    = 80
  port_range_max    = 80
  remote_ip_prefix  = var.web_source_cidr_ipv4
  description       = "HTTP - redirect to HTTPS (campus IPv4)"
}

resource "openstack_networking_secgroup_rule_v2" "https" {
  security_group_id = openstack_networking_secgroup_v2.forgejo_vm.id
  direction         = "ingress"
  ethertype         = "IPv4"
  protocol          = "tcp"
  port_range_min    = 443
  port_range_max    = 443
  remote_ip_prefix  = var.web_source_cidr_ipv4
  description       = "HTTPS - the Forgejo web UI (campus IPv4)"
}

resource "openstack_networking_secgroup_rule_v2" "http_v6" {
  security_group_id = openstack_networking_secgroup_v2.forgejo_vm.id
  direction         = "ingress"
  ethertype         = "IPv6"
  protocol          = "tcp"
  port_range_min    = 80
  port_range_max    = 80
  remote_ip_prefix  = var.web_source_cidr_ipv6
  description       = "HTTP - redirect to HTTPS (campus IPv6)"
}

resource "openstack_networking_secgroup_rule_v2" "https_v6" {
  security_group_id = openstack_networking_secgroup_v2.forgejo_vm.id
  direction         = "ingress"
  ethertype         = "IPv6"
  protocol          = "tcp"
  port_range_min    = 443
  port_range_max    = 443
  remote_ip_prefix  = var.web_source_cidr_ipv6
  description       = "HTTPS - the Forgejo web UI (campus IPv6)"
}

# ICMPv6 is not optional the way ICMP is on IPv4: Path MTU Discovery relies on
# "Packet Too Big" messages, and blocking them creates MTU black holes where a
# connection establishes but larger transfers hang. That failure mode is worse
# here than on staging — a git clone or a container pull is exactly the kind of
# large transfer that stalls. RFC 4890 advises against filtering ICMPv6
# wholesale.
#
# Left open to ::/0 rather than the campus range: PMTUD messages originate from
# routers along the path, not from the client, so restricting the source would
# defeat the purpose.
resource "openstack_networking_secgroup_rule_v2" "icmpv6" {
  security_group_id = openstack_networking_secgroup_v2.forgejo_vm.id
  direction         = "ingress"
  ethertype         = "IPv6"
  protocol          = "ipv6-icmp"
  remote_ip_prefix  = "::/0"
  description       = "ICMPv6 - required for Path MTU Discovery (RFC 4890)"
}
