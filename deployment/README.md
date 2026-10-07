# Deployment

Everything needed to run OntoUI on a server lives here: the staging compose
stack, the Caddy reverse proxy, the Terraform and Ansible definitions of the
infrastructure, and the (optional) Forgejo forge host that automates deploys.

The application itself lives in the repository root (`llm-model-generator/`,
`frontend/`); local development keeps using the root `docker-compose.yml` and
is not affected by anything in this directory.

The deployed app is reachable **only from the campus network or the VPN** —
the perimeter firewall blocks public-internet traffic to the VM. TLS still
works because the certificate is obtained via ACME dns-01 (no inbound
validation; see `infrastructure/README.md`, "TLS").

## The two ways to deploy

Both ways execute the **same** workflow (`.forgejo/workflows/staging.yml`) and
the same Ansible playbook — they differ only in *who runs it*. There is no
second copy to drift.

| Way | Who runs it | When to use |
|---|---|---|
| 1. `act` from an operator's machine | you, on the VPN | first install, bootstrap, emergencies — see [docs/deploy-act.md](docs/deploy-act.md) |
| 2. Forgejo Actions (dispatched from the forge's UI) | a runner inside the network | routine staging deploys — see [docs/deploy-forgejo.md](docs/deploy-forgejo.md) |

Way 1 is the **simple installation**: clone, fill in secrets, run one command.
Way 2 exists because the repo is public on GitHub and the OpenStack API is
VPN-only: GitHub-hosted runners cannot reach it, and a self-hosted GitHub
runner on a public repository is a security risk (any fork's pull request can
reach the runner and its secrets). The code therefore stays public on GitHub
while the runner and the deploy secrets live in a Forgejo instance whose
access we control.

## Layout

```text
deployment/
├── README.md                  # this file
├── Makefile                   # one-liner entry points (make deploy-staging)
├── docker-compose.staging.yml # the staging stack (app + Caddy TLS)
├── caddy/                     # reverse proxy: one hostname, path routing, ACME dns-01 (built image, rfc2136)
├── .env.staging.example       # documents the STAGING_ENV_FILE secret's keys
├── .secrets.template          # template for the act secrets file
├── docs/                      # the two deploy guides
├── forgejo/                   # the forge host (way 2): compose stack + setup
└── infrastructure/            # Terraform (modules, envs) + Ansible playbooks
```

- [`infrastructure/README.md`](infrastructure/README.md) — the Terraform
  module, the staging environment, addressing on the DHBW cluster, state,
  the playbook and the workflow in detail.
- [`infrastructure/EXTRACT.md`](infrastructure/EXTRACT.md) — recipe for
  reusing this tooling in another repository.
