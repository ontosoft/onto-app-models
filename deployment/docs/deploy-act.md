# Way 1: deploy with act (the simple installation)

Deploys staging from your own machine. No Forgejo, no runner — only
[act](https://github.com/nektos/act), Docker, and VPN access to the OpenStack
API. This runs the exact same workflow that Forgejo runs in way 2.

## Prerequisites

1. **VPN**: the OpenStack API (Keystone) is reachable only from the DHBW VPN.
   `connect: connection refused` from Terraform almost always means the VPN is
   off.
2. **OpenStack application credentials** for the target project (Horizon →
   Identity → Application Credentials).
3. **An unencrypted SSH key pair** for the deploy, e.g.
   `ssh-keygen -t ed25519 -N '' -f ~/.ssh/openstack-deploy`. Terraform
   registers the public half as the OpenStack keypair automatically.
4. **The runtime .env** for the stack: copy
   [`../.env.staging.example`](../.env.staging.example) somewhere outside the
   repo, fill it in, keep it safe. `APP_HOSTNAME` needs DNS records (see
   below).

## Setup (once)

```bash
cp deployment/.secrets.template deployment/.secrets   # git-ignored
# Fill in the STAGING_OS_* values. Leave SSH_PRIVATE_KEY and
# STAGING_ENV_FILE empty - both are passed on the CLI below so they
# never sit in a file inside the repo.
```

## Deploy

With the paths wired up in the Makefile:

```bash
cd deployment
make plan-staging   DEPLOY_KEY=~/.ssh/openstack-deploy STAGING_ENV=/path/to/staging.env
make deploy-staging DEPLOY_KEY=~/.ssh/openstack-deploy STAGING_ENV=/path/to/staging.env
```

`plan-staging` runs the same workflow but stops after `terraform plan` — use
it first; it exercises the credentials, the plan and every secret without
changing anything. The raw command behind the Makefile, from the repository
root:

```bash
act workflow_dispatch -W .forgejo/workflows/staging.yml --bind \
  -P deploy=catthehacker/ubuntu:act-latest \
  --input mode=apply \
  --secret-file deployment/.secrets \
  -s SSH_PRIVATE_KEY="$(cat ~/.ssh/openstack-deploy)" \
  -s STAGING_ENV_FILE="$(cat /path/to/your/staging.env)"
```

(`-P` maps the workflow's `runs-on: deploy` — the Forgejo runner's label — to
a generic act image; the workflow's tool-install steps fill in what that image
lacks.)

`--bind` makes the container write into your working directory, so the
Terraform state (`deployment/infrastructure/terraform/envs/staging/terraform.tfstate`)
persists on your machine and is reused by the next run. **This is only safe
for a single operator** — the state file is the only record of the VM.

## After the first apply

1. Read the addresses: `terraform output vm_ip` (IPv6) and
   `terraform output vm_ipv4` (IPv4) in the staging env dir.
2. Create DNS records for `APP_HOSTNAME`: an AAAA record on `vm_ip`, an A
   record on `vm_ipv4`. Keep the hostname a **shallow** subdomain.
3. Caddy then obtains the certificate on its own (ACME http-01). If the CA's
   validators are blocked by the firewall, set `ACME_CA_URL` in the env file
   to the HARICA directory and redeploy.
4. The first boot downloads the multi-GB GGUF model and imports it into
   Ollama — expect several minutes before the API container reports healthy.
