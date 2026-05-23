# Extracting the deploy tooling into another app repo

This moves the **Terraform + Ansible + GitHub Actions** deploy machinery into a
different application repository. It assumes that the destination repo
is an app repo that has a `docker-compose.yml` at its root (same layout as this
one). The playbooks rsync the repo root and run `docker compose up`, so no
playbook changes are needed — only the steps below.

## 1. Copy the necessary files

```bash
DEST=/path/to/destination-repo
mkdir -p "$DEST/.github/workflows"

# Infra tree. Excludes:
#  - roles_external/      (geerlingguy.docker is fetched from Galaxy at deploy
#                          time via requirements.yml; not vendored)
#  - .terraform/          (provider cache; `terraform init` rebuilds it)
#  - terraform.tfstate*   (local backend state — see step 5)
#  - inventory.ini        (generated per-deploy)
# KEEPS .terraform.lock.hcl (committed; reproducible provider versions).
rsync -a \
  --exclude='ansible/roles_external/' \
  --exclude='.terraform/' \
  --exclude='terraform.tfstate' \
  --exclude='terraform.tfstate.backup' \
  --exclude='ansible/inventory.ini' \
  infrastructure/ "$DEST/infrastructure/"

# Workflows
cp .github/workflows/staging-deploy.yml \
   .github/workflows/production-deploy.yml \
   "$DEST/.github/workflows/"

# act template (tracked). Do NOT copy the real .secrets blindly.
cp .secrets.template "$DEST/"
```

The `.gitignore` files inside `infrastructure/` and `infrastructure/ansible/`
travel automatically. Add a root-level rule for the act secrets file:

```bash
printf '\n.secrets\n' >> "$DEST/.gitignore"
```

## 2. Things git does NOT carry — recreate by hand in the destination repo

| Item | Action |
|---|---|
| Repo secrets `STAGING_OS_*`, `PRODUCTION_OS_*`, `SSH_PRIVATE_KEY` | Recreate in the new repo's Settings → Secrets. |
| `production` Environment + protection rules | Recreate (the prod workflow references `environment: production`). |
| Local `.secrets` (for `act`) | Rebuild from `.secrets.template`; it is git-ignored by design. |
| `.terraform/` cache | Don't copy — `terraform init` rebuilds. |

## 3. SSH key

`SSH_PRIVATE_KEY` must be an **unencrypted** private key. Terraform registers
its derived public half as the OpenStack keypair (`<name>-key`), so there's no
separate keypair name to keep in sync. For local `act` runs, pass it on the CLI:

```bash
act -W .github/workflows/staging-deploy.yml --bind --secret-file .secrets \
  -s SSH_PRIVATE_KEY="$(cat ~/.ssh/your-unencrypted-key)"
```

## 4. The Galaxy role (already wired)

`geerlingguy.docker` is no longer vendored. Both workflows install it from the
pinned `infrastructure/ansible/requirements.yml` into `roles_external/` (which
`ansible.cfg`'s `roles_path` searches). For local runs:

```bash
cd infrastructure/ansible
ansible-galaxy role install -r requirements.yml -p roles_external
ansible-galaxy collection install -r requirements.yml
```

## 5. Terraform state decision

This repo uses a **local** backend; state lives in
`infrastructure/terraform/envs/<env>/terraform.tfstate` (git-ignored). It is the
only record of the live VMs.

- **Take over the existing VMs from the new repo** → also copy the state file:
  ```bash
  cp infrastructure/terraform/envs/staging/terraform.tfstate \
     "$DEST/infrastructure/terraform/envs/staging/terraform.tfstate"
  ```
- **Start fresh** → don't copy it, but `terraform destroy` the current VM from
  *this* repo first, or you'll orphan it and hit a keypair-name collision
  (`<name>-key` already exists) on the next apply.

## 6. Post-move checklist (in the destination repo)

1. [ ] `terraform init` in each `envs/<env>` (picks up the copied lock file).
2. [ ] Recreate GitHub secrets + the `production` environment.
3. [ ] Root `.gitignore` has `.secrets`; create local `.secrets` from template.
4. [ ] Decide the state file (copy vs. fresh — step 5).
5. [ ] `git status` shows **no** `tfstate`, `.terraform/`, `.secrets`,
       `inventory.ini`, or `roles_external/` staged.
6. [ ] Dry run: `act -W .github/workflows/staging-deploy.yml --bind --secret-file .secrets -s SSH_PRIVATE_KEY="$(cat ~/.ssh/key)"`
