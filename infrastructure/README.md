# Infrastructure

Infrastructure-as-code in two layers:

- **Terraform** (`terraform/`) — provisions OpenStack VMs (one Docker host).
- **Ansible** (`ansible/`) — installs Docker on the VM and deploys the application via Docker Compose.

GitHub Actions (`.github/workflows/`) chains the two together: Terraform applies the
infrastructure and exposes the VM's reachable IP as the `vm_ip` output; the workflow reads that
output and writes a small `inventory.ini` that Ansible then deploys onto. The two tools are
**loosely coupled** — Ansible does not read Terraform state.

> **Networking note:** on the current OpenStack the VM's *fixed* IP is already
> publicly routable  so **no floating IP is allocated** (`assign_floating_ip = false`).
> The OpenStack **API** (Keystone), however, is reachable **only from VPN** — so
> every `terraform` / `act` run must be on the VPN. 

## Environments

| Environment | Terraform dir               | Ansible playbook        | Inventory                         | Trigger                          |
|-------------|-----------------------------|-------------------------|-----------------------------------|----------------------------------|
| staging     | `terraform/envs/staging`    | `deploy_staging.yml`    | generated `inventory.ini`         | push to `main`                   |
| production  | `terraform/envs/production` | `deploy_production.yml` | generated `inventory.ini`         | `workflow_dispatch` or `v*` tag  |

## Terraform

```
terraform/
├── modules/openstack_vm/             # reusable VM module (keypair + instance + optional floating IP + optional Cinder data volume)
└── envs/
    ├── staging/                      # staging-docker VM (mb1.large)
    └── production/                   # prod-docker VM (m1.extra_large)
```

Each env dir has:

- `main.tf` — instantiates the `openstack_vm` module (name, image, flavor, **`public_key`**,
  network, security groups, metadata). Outputs `vm_ip`.
- `backend.tf` — `required_version` (`>= 1.5.0`), the OpenStack provider pin
  (`~> 3.4`), and a **local** state backend (`terraform.tfstate` in the env dir). See
  "Local state assumption" below.
- `providers.tf` — OpenStack provider; credentials come entirely from `OS_*` environment variables.
- `variables.tf` — `ssh_public_key`, supplied by CI via `TF_VAR_ssh_public_key`.

The shared module (`modules/openstack_vm/`) registers the supplied public key as an
`openstack_compute_keypair_v2` (so the runner's private key always matches what is injected into
the VM — no dependency on a pre-existing laptop key), then creates an
`openstack_compute_instance_v2`. Two optional pieces are toggled per environment:

- **`assign_floating_ip`** (module default `true`; both envs set `false`) — when true, allocates an
  `openstack_networking_floatingip_v2` from `floating_ip_pool`. Disabled here network already hands out publicly-routable fixed IPs. `vm_ip` returns the floating IP when one
  is assigned, otherwise the instance's fixed IP.
- **`docker_data_volume_size_gb`** (both envs: `50`) — attaches a Cinder volume that the env's
  cloud-init (`user_data`) formats and mounts at `/var/lib/docker`, because the flavor root disk

Only the **public** key half ever reaches OpenStack/state.

Run locally:

```bash
cd terraform/envs/staging   # or envs/production
export TF_VAR_ssh_public_key="$(ssh-keygen -y -f /path/to/deploy_key)"
terraform init
terraform apply
```

Requires `OS_AUTH_URL`, `OS_APPLICATION_CREDENTIAL_ID`, `OS_APPLICATION_CREDENTIAL_SECRET`,
`OS_REGION_NAME` in the environment (stored as per-environment GitHub secrets,
prefixed `STAGING_*` / `PRODUCTION_*`).

### Local state assumption

State is intentionally kept in a **local** backend (`terraform.tfstate` in each env dir) rather
than a remote backend. This is a deliberate, temporary choice: deploys are driven from a single
operator's machine via `act` (see below) with `--bind`, so the state file persists on the host
and is reused across runs. **This is only safe for one person** — concurrent runs from different
machines/runners would diverge. Moving to a remote backend  is
a possible next step .

## Ansible

```
ansible/
├── ansible.cfg                       # roles_path, remote_user=ubuntu, SSH tuning, no host key check, no default inventory
├── requirements.yml                  # geerlingguy.docker role + community.docker / ansible.posix collections
├── deploy_staging.yml                # configure Docker + deploy (staging)
├── deploy_production.yml             # configure Docker + deploy (production)
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

### Deploy playbooks

`deploy_staging.yml` and `deploy_production.yml` are currently identical. Each one, against the
`docker_vm` host:

1. Creates `/home/ubuntu/app`.
2. Applies the `geerlingguy.docker` role (installs Docker + Compose).
3. rsyncs the **repo root** (`{{ playbook_dir }}/../../` → `/home/ubuntu/app`), excluding `.git`,
   `.history`, `docker-compose.override.yml`, `node_modules`, `__pycache__`, `.venv`,
   `.terraform`, `frontend/dist`, `frontend/test-results`, `frontend/blob-report`, and
   `model_files` (the multi-GB Mistral GGUF — the compose `model-downloader` service fetches it on
   the VM instead).
4. Runs `docker compose up --build` via `community.docker.docker_compose_v2` (`build: always`) with
   an explicit `files: ["docker-compose.yml"]`. `build: always` is required because the custom
   images (`llm-model-generator-api`, `frontend`, …) have no registry and are **built on the VM**.
   The explicit `files:` keeps the local-dev `docker-compose.override.yml` from ever being applied
   to a server.

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

Both workflows (`.github/workflows/staging-deploy.yml`, `production-deploy.yml`) follow the same shape so far:

1. **Checkout**.
2. **Setup Terraform** (`terraform_wrapper: false`).
3. **Terraform Format Check** — `terraform fmt -check -recursive` (blocking).
4. **Terraform Security Scan (Trivy)** — `trivy config` on HIGH/CRITICAL; **non-blocking**
   (`continue-on-error: true`) for now.
5. **Set up SSH key** from the `SSH_PRIVATE_KEY` secret; derives the public key with
   `ssh-keygen -y -P ''` (the `-P ''` makes a passphrase-protected key fail fast instead of hanging)
   and exports it as `TF_VAR_ssh_public_key` (runs *before* Terraform, which needs it).
6. **Terraform Init, Validate, Plan & Apply** in the env dir (`plan -out=tfplan` → `apply tfplan`),
   then exports `VM_IP` from the `vm_ip` output.
7. **Install Ansible + rsync** (apt; `pip` is blocked by PEP 668 on Ubuntu 24.04 runners), then
   install the `geerlingguy.docker` role into `roles_external/` and the collections — both from the
   pinned `requirements.yml`.
8. **Generate Ansible Inventory** — writes `inventory.ini` from `VM_IP`.
9. **Run Ansible playbook** against `inventory.ini`.
10. **Cleanup** the SSH key + `inventory.ini` (production also wipes `.terraform`).

Differences:

- **Staging** runs automatically on every push to `main`.
- **Production** runs only on manual `workflow_dispatch` or a `v*` tag push, uses the protected
  `production` GitHub Environment, and serializes runs via a `production-deploy` concurrency group
  (`cancel-in-progress: false`).

### Required secrets

Per environment (`STAGING_*` / `PRODUCTION_*`): `OS_AUTH_URL`, `OS_APPLICATION_CREDENTIAL_ID`,
`OS_APPLICATION_CREDENTIAL_SECRET`, `OS_REGION_NAME`. Shared: `SSH_PRIVATE_KEY` — an
**unencrypted** private key. Terraform registers its derived public half as the OpenStack
keypair, so there is no separate "key pair" name to keep in sync.

### Notes / follow-ups

- The Trivy scan is intentionally non-blocking; review its findings and remove
  `continue-on-error` to enforce once the IaC is clean.
- State is local by design (see "Local state assumption"). A remote backend is the main
  remaining hardening item.

### Reusing this tooling in another repo

See [`EXTRACT.md`](EXTRACT.md) for a step-by-step recipe to copy the Terraform + Ansible +
workflows into another app repo: what to copy, what to recreate by hand (GitHub secrets, the
`production` environment, local state), and the Galaxy-role gotcha (the role is no longer vendored,
so the destination must install it from `requirements.yml`).

### Deployment using act

Temporary solution while there is no remote state backend using act (https://github.com/nektos/act):

```bash
act -W .github/workflows/staging-deploy.yml --bind --secret-file .secrets
act -W .github/workflows/production-deploy.yml --bind --secret-file .secrets
```

With `--bind`, the container writes directly to your host directory, so `terraform.tfstate` lands
back in `infrastructure/terraform/envs/<env>/` on your machine and is reused next run. As noted
above, this is safe only for one person.

A better way is to create a key for deployment and use it without storing it in the .secrets file:

```bash

act -W .github/workflows/staging-deploy.yml --bind --secret-file .secrets \
  -s SSH_PRIVATE_KEY="$(cat ~/.ssh/openstack-deploy)"
```
