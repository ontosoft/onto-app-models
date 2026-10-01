# Job image for the Forgejo deploy runner.
#
# Everything the staging workflow needs is baked in: no apt-get, no curl | sh,
# no ansible-galaxy at deploy time. That pins every tool version and stops a
# deploy failing because GitHub Releases or Ansible Galaxy is briefly down.
# The workflow's install steps are guarded with `command -v`, so on this image
# they all no-op.
#
# node is the base rather than an add-on because Forgejo Actions — like act —
# executes JavaScript actions such as actions/checkout *inside* this container.
# A plain debian base makes actions/checkout fail with a confusing error.
FROM node:20-bookworm-slim

ARG TARGETARCH=amd64
ARG TERRAFORM_VERSION=1.9.8
ARG TRIVY_VERSION=0.73.0
ARG ANSIBLE_VERSION=10.5.0

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      ca-certificates curl git unzip jq rsync openssh-client \
      python3 python3-venv \
 && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL "https://releases.hashicorp.com/terraform/${TERRAFORM_VERSION}/terraform_${TERRAFORM_VERSION}_linux_${TARGETARCH}.zip" -o /tmp/tf.zip \
 && unzip -d /usr/local/bin /tmp/tf.zip \
 && rm /tmp/tf.zip \
 && terraform version

RUN set -eu; \
    case "${TARGETARCH}" in \
      amd64) TRIVY_ARCH=Linux-64bit ;; \
      arm64) TRIVY_ARCH=Linux-ARM64 ;; \
      *) echo "unsupported TARGETARCH ${TARGETARCH}" >&2; exit 1 ;; \
    esac; \
    curl -fsSL "https://github.com/aquasecurity/trivy/releases/download/v${TRIVY_VERSION}/trivy_${TRIVY_VERSION}_${TRIVY_ARCH}.tar.gz" \
      | tar -xz -C /usr/local/bin trivy; \
    trivy --version

# bookworm enforces PEP 668, so ansible gets its own venv rather than fighting
# pip --break-system-packages.
RUN python3 -m venv /opt/ansible \
 && /opt/ansible/bin/pip install --no-cache-dir --upgrade pip \
 && /opt/ansible/bin/pip install --no-cache-dir "ansible==${ANSIBLE_VERSION}" \
 && ln -s /opt/ansible/bin/ansible \
          /opt/ansible/bin/ansible-playbook \
          /opt/ansible/bin/ansible-galaxy \
          /opt/ansible/bin/ansible-config \
          /opt/ansible/bin/ansible-inventory \
          /usr/local/bin/

# Galaxy dependencies baked in.
#
# The collection install is a no-op today: the `ansible` distribution (as
# opposed to bare ansible-core) already bundles community.docker, ansible.posix
# and community.general under site-packages. It is kept so that adding a
# collection to requirements.yml later Just Works instead of failing at deploy
# time.
#
# Roles are different — they must go somewhere explicit, because
# infrastructure/ansible/ansible.cfg pins roles_path and would otherwise hide
# them. ANSIBLE_ROLES_PATH below overrides that: environment beats config file
# in ansible's precedence order.
COPY requirements.yml /tmp/requirements.yml
RUN ansible-galaxy role install -r /tmp/requirements.yml -p /opt/ansible-roles \
 && ansible-galaxy collection install -r /tmp/requirements.yml -p /usr/share/ansible/collections \
 && rm /tmp/requirements.yml

ENV ANSIBLE_ROLES_PATH=/opt/ansible-roles
