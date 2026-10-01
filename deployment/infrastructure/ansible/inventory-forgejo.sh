#!/usr/bin/env bash
# Generates inventory.forgejo.ini from the envs/forgejo Terraform output.
#
# envs/staging gets its inventory from the deploy workflow, which runs
# `terraform output -raw vm_ip` after apply. envs/forgejo has no workflow — it
# is the bootstrap environment and is applied from an operator's machine — so
# the same step lives here as a script rather than being typed from memory.
#
# Usage, from this directory:
#
#   ./inventory-forgejo.sh [dns-name]
#   ansible-playbook -i inventory.forgejo.ini \
#     --private-key ~/.ssh/<key> forgejo.yml
set -euo pipefail

here=$(cd "$(dirname "$0")" && pwd)
env_dir="$here/../terraform/envs/forgejo"
out="$here/inventory.forgejo.ini"

if [ ! -f "$env_dir/terraform.tfstate" ]; then
  echo "No state in $env_dir - run terraform apply there first." >&2
  exit 1
fi

# An optional argument overrides the address with a DNS name. Prefer it once a
# record exists: ansible.posix.synchronize builds the rsync destination from a
# bare IPv6 literal with the bracket around the whole user@host, which macOS's
# openrsync hands to ssh mangled. A DNS name has no brackets to misplace.
if [ $# -gt 0 ] && [ -n "$1" ]; then
  address=$1
else
  address=$(terraform -chdir="$env_dir" output -raw vm_ip)
fi

# Empty means terraform produced no output. Without this check ansible-playbook
# would still exit 0 with "no hosts matched" - a green run that configured
# nothing.
if [ -z "$address" ]; then
  echo "vm_ip is empty - terraform output produced nothing." >&2
  exit 1
fi

# The address goes in ansible_host behind an alias rather than being the host
# name itself. Brackets around an IPv6 literal do not work: the ini plugin
# reads [...] as a host range pattern and fails with "host range must be
# begin:end". An alias sidesteps the question and is identical for IPv4, IPv6
# and a DNS name — all three are possible here.
cat > "$out" <<EOF
[forgejo_vm]
forgejo ansible_host=${address} ansible_user=ubuntu
EOF

# 0600 rather than the default: the file names a reachable host whose SSH port
# is open to the campus range.
chmod 600 "$out"

echo "Wrote $out:"
cat "$out"
