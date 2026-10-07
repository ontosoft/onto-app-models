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

**Terraform state** does not live on your machine: `envs/staging` uses the
`pg` backend against the forge's Postgres (see
[deploy-forgejo.md](deploy-forgejo.md)), so way 1 and way 2 share one
locked state. That means act runs need `PG_CONN_STR` too — and a laptop
cannot resolve the in-network host `db`. For a plan/apply from outside,
tunnel through the forge host (requires its Postgres to be published on
the forge's loopback) and point the connection at the tunnel:

```bash
ssh -i ~/.ssh/openstack-deploy -L 15432:127.0.0.1:5432 ubuntu@<forge-host> -N &
# in deployment/.secrets:
# PG_CONN_STR=postgres://<user>:<pw>@host.docker.internal:15432/terraform_state?sslmode=disable
```

In day-to-day use, prefer running deploys from Forgejo (way 2) and keep
act for bootstrap and emergencies.

## After the first apply

1. Read the address: `terraform output vm_ipv4` in the staging env dir.
2. Create an A record for `APP_HOSTNAME` on `vm_ipv4`. Do **not** add an
   AAAA record — the IPv6 address changes with every VM replacement.
3. Caddy then obtains the certificate on its own via ACME dns-01, using the
   `DNS_TSIG_*` credentials from the env file (see
   `deployment/.env.staging.example`). No CA reaches this VM inbound, so the
   DNS route is the only one that works. The first issuance takes **~10
   minutes**: validation is done in seconds, then the caddy log sits at
   "finalizing order" while the CA's pipeline runs — that is normal.
4. The first boot downloads the multi-GB GGUF model and imports it into
   Ollama — expect several minutes before the API container reports healthy.
