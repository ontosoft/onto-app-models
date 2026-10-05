# Infrastructure

Infrastructure-as-code in two layers:

- **Terraform** (`terraform/`) — provisions OpenStack VMs (one Docker host).
- **Ansible** (`ansible/`) — installs Docker on the VM and deploys the application via Docker Compose.

The workflow (`.forgejo/workflows/staging.yml` — run by Forgejo Actions or locally via `act`) chains the two together: Terraform applies the
infrastructure and exposes the VM's reachable IP as the `vm_ip` output; the workflow reads that
output and writes a small `inventory.ini` that Ansible then deploys onto. The two tools are
**loosely coupled** — Ansible does not read Terraform state.

> **Networking note:** on the target OpenStack the VM's primary network
> (`DHBWV6`) hands out a **public IPv6** fixed address; a second interface on
> `DHBWv4` adds a **public IPv4** (no floating IP involved — see
> `connect_via` in the module). The OpenStack **API** (Keystone), however, is
> reachable **only from VPN** — so every `terraform` / `act` run must be on
> the VPN.

## Environments

| Environment | Terraform dir            | Ansible playbook     | Inventory                 | Trigger        |
|-------------|--------------------------|----------------------|---------------------------|----------------|
| staging     | `terraform/envs/staging` | `deploy_staging.yml` | generated `inventory.ini` | manual dispatch (act or Forgejo) |
| forgejo     | `terraform/envs/forgejo` | `forgejo.yml`        | `inventory-forgejo.sh`    | by hand from a workstation (optional — only when self-hosting the forge) |

(A production environment existed for a decommissioned cluster and was
removed; the module is environment-agnostic, so adding `envs/production/`
plus a playbook is the obvious extension point when needed.)

## Terraform

```
terraform/
├── modules/openstack_vm/             # reusable VM module (keypair + instance + optional floating IP,
│                                     # optional Cinder data volume, optional second interface)
└── envs/
    └── staging/                      # the application stack
```

Each env dir has:

- `main.tf` — instantiates the `openstack_vm` module (name, image, flavor, **`public_key`**,
  network, security groups, metadata). Outputs `vm_ip`.
- `backend.tf` — `required_version` (`>= 1.5.0`), the OpenStack provider pin
  (`~> 3.4`), and the state backend. See "Terraform state" below.
- `providers.tf` — OpenStack provider; credentials come entirely from `OS_*` environment variables.
- `variables.tf` — `ssh_public_key` (supplied by CI via `TF_VAR_ssh_public_key`) plus the
  **cluster parameters** (image, flavor, networks, `connect_via`, SSH source CIDRs). Defaults
  target the current cluster; another cluster is a tfvars file, not a code edit.
- `security_group.tf` — the VM's security group and rules, managed in Terraform so a fresh
  cluster needs no hand-made groups.

The shared module (`modules/openstack_vm/`) registers the supplied public key as an
`openstack_compute_keypair_v2` (so the runner's private key always matches what is injected into
the VM — no dependency on a pre-existing laptop key), then creates an
`openstack_compute_instance_v2`. Optional pieces are toggled per environment:

- **`connect_via`** (`fixed_ipv4` | `fixed_ipv6` | `floating_ipv4`) — which address `vm_ip`
  returns, i.e. the address Ansible connects to. Staging uses `fixed_ipv6` (public IPv6 on
  `DHBWV6`); `floating_ipv4` allocates from `floating_ip_pool` for clusters whose fixed IPv4
  is private.
- **`secondary_network_name`** / **`secondary_subnet_name`** — optional second interface for
  dual-stack (public IPv4 next to the IPv6 primary; this is what the A record points at).
  The port is pinned to the named subnet and gets the same security groups explicitly, and the
  interface is attached to the running instance so it never forces a VM replacement.
- **`docker_data_volume_size_gb`** (staging: `50`) — attaches a Cinder volume for the container
  data, because the flavor root disk is small. The **playbook** formats and mounts it (bind
  mounts for `/var/lib/docker` and `/var/lib/containerd`); cloud-init cannot, since the module
  attaches the volume only after the instance is ACTIVE — a race cloud-init lost on this
  cluster. The playbook also places swap and `model_files` (the GGUF) on the
  volume - the 10 GB root disk cannot hold them; the env passes no
  `user_data` at all.

Only the **public** key half ever reaches OpenStack/state.

Run locally:

```bash
cd terraform/envs/staging
export TF_VAR_ssh_public_key="$(ssh-keygen -y -f /path/to/deploy_key)"
terraform init
terraform apply
```

Requires `OS_AUTH_URL`, `OS_APPLICATION_CREDENTIAL_ID`, `OS_APPLICATION_CREDENTIAL_SECRET`,
`OS_REGION_NAME` in the environment (stored as GitHub secrets prefixed `STAGING_*`).

### Terraform state

`envs/staging` uses the **`pg` backend**: state lives in the `terraform_state` database on the
forge's Postgres, in this project's own schema (`onto_app_staging`), locked per operation. The
connection string comes from the `PG_CONN_STR` environment variable / secret — never from a
`.tf` file, since it carries the database password. On a Forgejo runner this is what makes job
containers disposable without losing the state; for `act` runs see the tunnel note in
[`../docs/deploy-act.md`](../docs/deploy-act.md).

`envs/forgejo` (the optional self-hosted forge) deliberately stays on a **local** backend: it is
the bootstrap environment — storing its state in the database it hosts would be circular. That
state file exists only where the last apply ran; back it up.

## Ansible

```
ansible/
├── ansible.cfg                       # roles_path, remote_user=ubuntu, SSH tuning, no host key check, no default inventory
├── requirements.yml                  # geerlingguy.docker role + community.docker / ansible.posix collections
├── deploy_staging.yml                # configure Docker + deploy (staging)
├── .gitignore                        # ignores inventory.ini and roles_external/
├── inventory.ini                     # GENERATED at deploy time by the workflow (git-ignored / cleaned up)
└── roles_external/                   # geerlingguy.docker, INSTALLED from Galaxy at deploy time (not vendored, git-ignored)
```

### Inventory hand-off

There is no dynamic inventory plugin. The workflow runs `terraform output -raw vm_ip` and writes:

```ini
[docker_vm]
<floating-ip> ansible_user=ubuntu
```

into `ansible/inventory.ini`. The deploy playbooks target `hosts: docker_vm`, so no IP is
hard-coded in source — it comes straight from the Terraform run that just executed. The file is
created per-run and removed in the workflow's cleanup step.

### Deploy playbook

`deploy_staging.yml`, against the `docker_vm` host:

1. **Secondary interface** (only when the workflow passes `secondary_mac` from the Terraform
   outputs): writes a netplan file matching the port's MAC with a dedicated routing table for
   the IPv4 address, plus a connmark script + systemd unit so replies from DNATed container
   ports leave through the right gateway (without it SSH works but every published port times
   out — Neutron's port security silently drops the misrouted replies).
2. **Data volume**: checks the Cinder device exists (failing with the list of present devices if
   not), formats it (`force: no` — a second run never reformats), mounts it by UUID at
   `/mnt/docker-data` and bind-mounts `/var/lib/docker` and `/var/lib/containerd` onto it —
   all **before** the `geerlingguy.docker` role installs Docker + Compose.
3. rsyncs the **repo root** (`{{ playbook_dir }}/../../` → `/home/ubuntu/app`), excluding `.git`,
   caches, build outputs, `model_files/*.gguf` (the multi-GB Mistral GGUF — the compose
   `model-downloader` service fetches it on the VM instead) and **`.env`**.
4. Writes `/home/ubuntu/app/.env` **verbatim from the `STAGING_ENV_FILE` secret** — runtime
   configuration is a deploy input, not repository content, so deploys work from any runner.
   See `.env.staging.example` for the required keys.
5. Validates the interpolated config (`docker compose -f docker-compose.staging.yml config -q`,
   which names any missing `${VAR?…}` on stderr), pulls registry images
   (`pull --ignore-buildable`), then `up -d --build` — an explicit command rather than
   `community.docker.docker_compose_v2`, which hides compose's stderr on failure. The custom
   images (`llm-model-generator-api`, `frontend`, …) have no registry and are **built on the VM**.
6. Reloads Caddy (`caddy reload`) so changes to the bind-mounted `caddy/Caddyfile` take effect —
   compose does not notice content changes to bind mounts.

### TLS

Staging runs behind a Caddy **built with the rfc2136 module** (`docker-compose.staging.yml` +
`caddy/Dockerfile` + `caddy/Caddyfile`). Caddy obtains and renews the certificate itself via
ACME **dns-01**: it writes the `_acme-challenge` TXT record over RFC 2136 with the zone's TSIG
key (`DNS_TSIG_*` in the `.env`, from the DNS self-service "TLS Certificates" page). The
inbound challenge types do not work here — the public CAs are blocked by the campus firewall,
and the internal CA's validators cannot reach the VM on 80/443 either, although campus hosts
can. One hostname (`APP_HOSTNAME`) serves everything — Caddy routes `/api/*` and the FastAPI
doc endpoints to the backend and the rest to the frontend — so only one certificate is needed.
The hostname needs an A record on `terraform output vm_ipv4`; do **not** add an AAAA record
(the IPv6 address changes with every VM replacement).

Run locally (after a `terraform apply`, from the env dir, gives you the IP):

```bash
cd ansible
# The role isn't vendored — install it into ./roles_external (where ansible.cfg's
# roles_path looks); collections go to the default path.
ansible-galaxy role install -r requirements.yml -p roles_external
ansible-galaxy collection install -r requirements.yml
printf '[docker_vm]\n%s ansible_user=ubuntu\n' "$(cd ../terraform/envs/staging && terraform output -raw vm_ip)" > inventory.ini
ansible-playbook -i inventory.ini --private-key /path/to/deploy_key deploy_staging.yml
```

## CI/CD workflows

The staging workflow (`.forgejo/workflows/staging.yml`) is dispatched manually — from Forgejo’s Actions tab (way 2) or via `act workflow_dispatch` (way 1), with a `mode` input defaulting to `plan` — and
follows this shape:

1. **Checkout**.
2. **Setup Terraform** (`terraform_wrapper: false`).
3. **Terraform Format Check** — `terraform fmt -check -recursive` (blocking).
4. **Terraform Security Scan (Trivy)** — `trivy config` on HIGH/CRITICAL; **non-blocking**
   (`continue-on-error: true`) for now.
5. **Set up SSH key** from the `SSH_PRIVATE_KEY` secret; derives the public key with
   `ssh-keygen -y -P ''` (the `-P ''` makes a passphrase-protected key fail fast instead of hanging)
   and exports it as `TF_VAR_ssh_public_key` (runs *before* Terraform, which needs it).
6. **Terraform Init, Validate, Plan & Apply** in the env dir (`plan -out=tfplan` → `apply tfplan`),
   then exports `VM_IP` from the `vm_ip` output, plus `VM_IPV4` / `VM_IPV4_GW` / `VM_IPV4_MAC`
   from the secondary-interface outputs (empty on a single-homed VM).
7. **Install Ansible + rsync** (apt; `pip` is blocked by PEP 668 on Ubuntu 24.04 runners), then
   install the `geerlingguy.docker` role into `roles_external/` and the collections — both from the
   pinned `requirements.yml`.
8. **Generate Ansible Inventory** — writes `inventory.ini` from `VM_IP`.
9. **Run Ansible playbook** against `inventory.ini`, passing the secondary-interface values as
   `-e` vars and `STAGING_ENV_FILE` through the environment.
10. **Cleanup** the SSH key + `inventory.ini`.

### Required secrets

`STAGING_*`-prefixed: `OS_AUTH_URL`, `OS_APPLICATION_CREDENTIAL_ID`,
`OS_APPLICATION_CREDENTIAL_SECRET`, `OS_REGION_NAME`. Shared: `SSH_PRIVATE_KEY` — an
**unencrypted** private key. Terraform registers its derived public half as the OpenStack
keypair, so there is no separate "key pair" name to keep in sync.

`STAGING_ENV_FILE` holds the stack's entire `.env` as one (multi-line) secret. Ansible writes
it to the VM verbatim, so it is runtime configuration rather than CI configuration. Fields
written as `${VAR?…}` in `docker-compose.staging.yml` abort `compose up` when unset, so the
stack refuses to start half-configured; `.env.staging.example` documents them. Do not define a
key twice — compose takes the last occurrence.

### Notes / follow-ups

- The Trivy scan is intentionally non-blocking; review its findings and remove
  `continue-on-error` to enforce once the IaC is clean.
- State is local by design (see "Local state assumption"). A remote backend is the main
  remaining hardening item.

### Reusing this tooling in another repo

See [`EXTRACT.md`](EXTRACT.md) for a step-by-step recipe to copy the Terraform + Ansible +
workflows into another app repo: what to copy, what to recreate by hand (GitHub secrets,
local state), and the Galaxy-role gotcha (the role is no longer vendored,
so the destination must install it from `requirements.yml`).

### Deployment using act

Temporary solution while there is no remote state backend using act (https://github.com/nektos/act):

```bash
act -W .forgejo/workflows/staging.yml --bind --secret-file .secrets
```

With `--bind`, the container writes directly to your host directory, so `terraform.tfstate` lands
back in `infrastructure/terraform/envs/<env>/` on your machine and is reused next run. As noted
above, this is safe only for one person.

A better way is to create a key for deployment and use it without storing it in the .secrets file:

```bash

act -W .forgejo/workflows/staging.yml --bind --secret-file .secrets \
  -s SSH_PRIVATE_KEY="$(cat ~/.ssh/openstack-deploy)"
```
