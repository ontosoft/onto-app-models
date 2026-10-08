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
   `../.env.staging.example` — TLS needs `DNS_TSIG_KEY_NAME`/`DNS_TSIG_KEY`
   in it, the zone's TSIG key from the DNS self-service "TLS Certificates"
   page).
3. **Check the runner label**: the workflow's `runs-on: deploy` must match a
   runner on that instance. The job image the runner uses should bake the
   deploy tools (see `../forgejo/job-image/`); on a bare image, the
   workflow's guarded install steps fetch them instead.
4. **Run it**: Actions tab → "CD - Staging Deployment" → Run workflow →
   `mode: plan` first, then `apply`. Backend and frontend images are pulled
   from GHCR, so check that the "Build images" workflow for the commit you
   deploy has finished on GitHub (with `TAG` unset, `latest` simply takes
   the newest finished build). Remember to **sync the mirror first**
   (Repository → Mirror settings → "Synchronize now") — pull mirrors only
   refresh on their schedule, and a run on a stale mirror checks out the
   previous commit without complaining.
5. **After the first apply**: create the A record (no AAAA) and expect ~10
   minutes for the first certificate — see "After the first apply" in
   [deploy-act.md](deploy-act.md), which applies to both ways.

### Terraform state

`envs/staging/backend.tf` declares the **`pg` backend**: state lives in the
`terraform_state` database on the forge stack's Postgres, in this project's
own schema (`onto_app_staging`, created automatically on the first init,
next to the sibling project's `staging` schema). Job containers stay
disposable — on a Forgejo runner a local state file would die with the
container after every run.

The seventh Actions secret supplies the connection:

```
PG_CONN_STR = postgres://<user>:<password>@db:5432/terraform_state?sslmode=disable
```

`db` resolves inside the forge's compose network, which is exactly where
job containers run — the database is reachable from deploys and from
nowhere else. The pg backend takes an advisory lock per operation, so
concurrent runs cannot corrupt the state.

Consequence for way 1: `act` runs now also need `PG_CONN_STR`, and a
laptop cannot resolve `db` — see the state note in
[deploy-act.md](deploy-act.md).

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

- Narrow `ssh_source_cidr_*` in `envs/staging` from campus-wide to the
  runner's address.
