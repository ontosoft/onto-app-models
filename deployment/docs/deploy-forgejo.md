# Way 2: deploy via Forgejo Actions

Automated staging deploys: a Forgejo instance inside the DHBW network runs the
workflow (`.forgejo/workflows/staging.yml`) through an Actions runner that can
reach both the OpenStack API and the VM — no VPN, no operator machine. The
workflow is started by hand from Forgejo's Actions tab (`mode: plan` or
`apply`); Forgejo does not reliably fire Actions on mirror sync, so there is
no push trigger.

## Why an own Forgejo (and not a self-hosted GitHub runner)

This repository is public on GitHub. GitHub's own guidance: self-hosted
runners should almost never be used on public repositories, because any user
can open a pull request from a fork and compromise the runner's environment —
including the OpenStack credentials and the SSH deploy key it holds. The
split therefore is: the code stays public on GitHub; the runner and the
deploy secrets live in a Forgejo whose accounts we control.

## A. Using an existing Forgejo instance (recommended)

Any Forgejo whose runner can reach your OpenStack API works — you need an
account there with rights to create a repository and its Actions secrets, not
VM admin rights. Steps:

1. **Mirror the repository**: in Forgejo, create a new *pull mirror* of
   `https://github.com/ontosoft/onto-app-models.git` (or push to both
   remotes). The workflow file arrives through the mirror — Forgejo mirrors
   are read-only, so everything it runs stays publicly reviewable on GitHub.
2. **Set the Actions secrets** on the mirrored repo (Settings → Actions →
   Secrets): `STAGING_OS_AUTH_URL`, `STAGING_OS_APPLICATION_CREDENTIAL_ID`,
   `STAGING_OS_APPLICATION_CREDENTIAL_SECRET`, `STAGING_OS_REGION_NAME`
   (*your* OpenStack project's application credentials), `SSH_PRIVATE_KEY`
   (unencrypted), and `STAGING_ENV_FILE` (the whole runtime `.env`, see
   `../.env.staging.example`).
3. **Check the runner label**: the workflow's `runs-on: deploy` must match a
   runner on that instance. The job image the runner uses should bake the
   deploy tools (see `../forgejo/job-image/`); on a bare image, the
   workflow's guarded install steps fetch them instead.
4. **Run it**: Actions tab → "CD - Staging Deployment" → Run workflow →
   `mode: plan` first, then `apply`.

### Terraform state on a Forgejo runner

`envs/staging/backend.tf` currently declares a **local** backend — right for
way 1, where `act --bind` keeps the state file on the operator's machine. On
a Forgejo runner, job containers are destroyed after every run, so a local
state file dies with them. Before way-2 `apply` runs become routine, the
state must move to a remote backend; the established pattern on the DHBW
forge is Terraform's `pg` backend against the Postgres the CI host runs:

1. Get a database — or just a schema; one Postgres holds many projects'
   states side by side (`schema_name` in the backend block) — on the forge's
   Postgres, with its own credentials.
2. Set the connection string as the `PG_CONN_STR` Actions secret (the
   workflow already passes it through to Terraform).
3. Flip `envs/staging/backend.tf` from `backend "local"` to `backend "pg"`
   and migrate: `terraform init -migrate-state`.

After the flip, way-1 `apply` runs also need to reach that Postgres (an SSH
tunnel to the forge host, since its database is deliberately not exposed).
Until the flip is done, use way 2 for `plan` only.

## B. Self-hosting the forge (optional)

For a team with no existing Forgejo anywhere. Everything needed is in the
repository, so the chain is reproducible from zero:

1. `infrastructure/terraform/envs/forgejo` — the forge VM (`ci-onto-app`,
   gp1.medium, campus-restricted 80/443, dual-stack). Applied **by hand from
   a workstation** on the VPN (way-1 style), because the runner it hosts
   cannot deploy itself. Its Terraform state stays local — back it up.
2. `../forgejo/` — the forge's compose stack: Forgejo 11 + Postgres, the
   Actions runner (label `deploy`, capacity 1), the baked job image, and a
   Caddy built with the `rfc2136` module (dns-01 is the only ACME challenge
   that works behind campus-restricted ports; needs the zone's TSIG key).
3. Bring-up order:
   ```bash
   cd deployment/infrastructure/terraform/envs/forgejo
   export TF_VAR_ssh_public_key="$(ssh-keygen -y -f ~/.ssh/openstack-deploy)"
   terraform init && terraform apply
   # DNS: A record on `terraform output vm_ipv4`, AAAA on `vm_ip`,
   # TSIG key for the zone -> forgejo .env (see ../forgejo/.env.example)
   cd ../../../ansible
   ./inventory-forgejo.sh <forge-dns-name>
   FORGEJO_ENV_FILE="$(cat /path/to/forgejo.env)" \
     ansible-playbook -i inventory.forgejo.ini \
     --private-key ~/.ssh/openstack-deploy forgejo.yml
   ```
4. First-start loose end (the playbook prints this too): the runner token is
   instance-bound, so after the first boot create one in the web UI (Site
   Admin → Actions → Runners), add it to the forge's `.env` as
   `FORGEJO_RUNNER_TOKEN`, and `docker compose up -d runner` on the VM.
5. Then continue with section A against your own instance.

The stack can also be tried **locally without any VM** (`cd deployment/forgejo
&& cp .env.example .env`, fill the top block, `docker compose up -d`) — Caddy
sits behind a compose profile and stays out of local runs.

## Follow-ups this enables

- Terraform state to the `pg` backend (see above).
- Narrow `ssh_source_cidr_*` in `envs/staging` from campus-wide to the
  runner's address.
