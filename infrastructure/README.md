# Infrastructure

Infrastructure-as-code for OntoUI. Two layers:

- **Terraform** (`terraform/`) — provisions OpenStack VMs (one Docker host per environment).
- **Ansible** (`ansible/`) — installs Docker on the VM and deploys the application via Docker Compose.

GitHub Actions (`.github/workflows/`) chains the two together: Terraform applies the
infrastructure and exposes the VM's floating IP as the `vm_ip` output; the workflow reads that
output and writes a small `inventory.ini` that Ansible then deploys onto. The two tools are
**loosely coupled** — Ansible does not read Terraform state.

## Environments

| Environment | Terraform dir               | Ansible playbook        | Inventory                         | Trigger                          |
|-------------|-----------------------------|-------------------------|-----------------------------------|----------------------------------|
| staging     | `terraform/envs/staging`    | `deploy_staging.yml`    | generated `inventory.ini`         | push to `main`                   |
| production  | `terraform/envs/production` | `deploy_production.yml` | generated `inventory.ini`         | `workflow_dispatch` or `v*` tag  |

## Terraform

```
terraform/
├── modules/openstack_vm/             # reusable VM module (keypair + instance + floating IP)
└── envs/
    ├── staging/                      # staging-docker VM, "DHBW" network
    └── production/                   # prod-docker VM, "private" network
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
`openstack_compute_instance_v2` plus an `openstack_networking_floatingip_v2`. Only the **public**
key half ever reaches OpenStack/state.

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
machines/runners would diverge. Moving to a remote backend (e.g. an OpenStack Swift container) is
the documented next step if the team grows.

## Ansible

```
ansible/
├── ansible.cfg                       # roles path, remote_user=ubuntu, SSH tuning, no host key check
├── requirements.yml                  # geerlingguy.docker role + docker/posix collections
├── deploy_staging.yml                # configure Docker + deploy (staging)
├── deploy_production.yml             # configure Docker + deploy (production)
├── inventory.ini                     # GENERATED at deploy time by the workflow (git-ignored / cleaned up)
├── roles/docker-vm-provision/        # local provisioning role
└── roles_external/geerlingguy.docker/# vendored Docker install role
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
   `.terraform`, `frontend/dist`, etc.
4. Runs `docker compose up` via `community.docker.docker_compose_v2` with an explicit
   `files: ["docker-compose.yml"]` — so the local-dev `docker-compose.override.yml` is **never**
   applied to a server even if it were present.

> **Note:** `site.yml` (which imported `provision.yml` + `deploy.yml`) is **deprecated**. Both
> environments now run their `deploy_*.yml` playbook directly; infrastructure provisioning is
> handled separately by the Terraform step.

Run locally (after a `terraform apply`, from the env dir, gives you the IP):

```bash
cd ansible
ansible-galaxy install -r requirements.yml
printf '[docker_vm]\n%s ansible_user=ubuntu\n' "$(cd ../terraform/envs/staging && terraform output -raw vm_ip)" > inventory.ini
ansible-playbook -i inventory.ini --private-key /path/to/deploy_key deploy_staging.yml
```

## CI/CD workflows

Both workflows (`.github/workflows/staging-deploy.yml`, `production-deploy.yml`) follow the same shape:

1. **Checkout**.
2. **Setup Terraform** (`terraform_wrapper: false`).
3. **Terraform Format Check** — `terraform fmt -check -recursive` (blocking).
4. **Terraform Security Scan (Trivy)** — `trivy config` on HIGH/CRITICAL; **non-blocking**
   (`continue-on-error: true`) for now.
5. **Set up SSH key** from the `SSH_PRIVATE_KEY` secret; also derives the public key and exports
   it as `TF_VAR_ssh_public_key` (runs *before* Terraform, which needs it).
6. **Terraform Init, Validate, Plan & Apply** in the env dir (`plan -out=tfplan` → `apply tfplan`),
   then exports `VM_IP` from the `vm_ip` output.
7. **Install Ansible** + the required Galaxy collections.
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

### Deployment using act

Temporary solution while there is no remote state backend:

```bash
act -W .github/workflows/staging-deploy.yml --bind --secret-file .secrets
act -W .github/workflows/production-deploy.yml --bind --secret-file .secrets
```

With `--bind`, the container writes directly to your host directory, so `terraform.tfstate` lands
back in `infrastructure/terraform/envs/<env>/` on your machine and is reused next run. As noted
above, this is safe only for one person.
