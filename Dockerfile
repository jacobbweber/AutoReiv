# ==============================================================================
# AutoReiv Production Dockerfile [REQ-DEPLOY-005]
# Multi-stage minimal image with security hardening and non-root user
# ==============================================================================

# Stage 1: Build & Dependencies
FROM python:3.12-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
COPY src/ ./src/
RUN pip install --no-cache-dir --prefix=/install setuptools wheel .

# Stage 2: Final Minimal Runtime Image
FROM python:3.12-slim AS runner

WORKDIR /app

# git and TLS certificates for in-app software updates [CARD-722] and project clones [CARD-731].
# make and g++ build native npm and pip modules in projects (no full build-essential) [CARD-731].
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    ca-certificates \
    make \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Project dev toolchain [CARD-731 / ADR-0067]: project commands run where the serve runs, so the image carries them.
# Node.js 22 LTS with npm, npx and corepack, copied from the official image (works on amd64 and arm64).
COPY --from=node:22-bookworm-slim /usr/local/bin/node /usr/local/bin/node
COPY --from=node:22-bookworm-slim /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -s ../lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm && \
    ln -s ../lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx && \
    ln -s ../lib/node_modules/corepack/dist/corepack.js /usr/local/bin/corepack
# uv and uvx for Python projects.
COPY --from=ghcr.io/astral-sh/uv:0.13.1 /uv /uvx /usr/local/bin/
# Docker CLI for building and launching sibling MCP containers via /var/run/docker.sock [CARD-745].
COPY --from=docker:27-cli /usr/local/bin/docker /usr/local/bin/docker

# Godot headless for game projects (export, tests, scripts). Build with --build-arg INSTALL_GODOT=0 to leave it out.
ARG INSTALL_GODOT=1
ARG GODOT_VERSION=4.7.2
ARG TARGETARCH
RUN set -e; \
    if [ "$INSTALL_GODOT" = "1" ]; then \
      arch="${TARGETARCH:-$(uname -m)}"; \
      case "$arch" in \
        amd64|x86_64) godot_arch=x86_64 ;; \
        arm64|aarch64) godot_arch=arm64 ;; \
        *) echo "No Godot Linux build for architecture $arch" >&2; exit 1 ;; \
      esac; \
      name="Godot_v${GODOT_VERSION}-stable_linux.${godot_arch}"; \
      apt-get update && apt-get install -y --no-install-recommends libfontconfig1 && rm -rf /var/lib/apt/lists/*; \
      python -c "import io, sys, urllib.request, zipfile; data = urllib.request.urlopen(sys.argv[1]).read(); open('/usr/local/bin/godot', 'wb').write(zipfile.ZipFile(io.BytesIO(data)).read(sys.argv[2]))" \
        "https://github.com/godotengine/godot/releases/download/${GODOT_VERSION}-stable/${name}.zip" "$name"; \
      chmod 0755 /usr/local/bin/godot; \
      godot --headless --version; \
    fi

# Create unprivileged system user
RUN groupadd -g 1000 autoreiv && \
    useradd -u 1000 -g autoreiv -s /bin/bash -m autoreiv

# Copy installed dependencies from builder
COPY --from=builder /install /usr/local

# Copy application source, platform agents/skills and git metadata [CARD-669, CARD-722]
COPY --chown=autoreiv:autoreiv .git/ ./.git/
COPY --chown=autoreiv:autoreiv src/ ./src/
COPY --chown=autoreiv:autoreiv platform/ ./platform/
COPY --chown=autoreiv:autoreiv pyproject.toml ./
COPY --chown=autoreiv:autoreiv README.md ./

# Persistent data mount points. Do NOT mkdir /data/wiki here [ADR-0056 / CARD-414]:
# Docker/daemon hard-fail requires a missing configured wiki path to stay missing until the operator mounts it.
# /data/projects is the projects folder [ADR-0067]; repos bind-mounted there are owned by host uids, so git trusts
# every directory for the app user (safe.directory '*') [CARD-731].
RUN mkdir -p /data/database /data/skills /data/projects && \
    chown -R autoreiv:autoreiv /data /app && \
    su autoreiv -c "git config --global --add safe.directory /app && git config --global --add safe.directory '*' && git sparse-checkout set --no-cone '/src/**' '/platform/**' '/pyproject.toml' '/README.md' && git checkout -- ."

# Default environment configuration
ENV PYTHONUNBUFFERED=1 \
    AUTOREIV_DATA_DIR=/data \
    AUTOREIV_DEPLOY_MODE=docker \
    AUTOREIV_WIKI_PATH=/data/wiki \
    AUTOREIV_PROJECTS_DIR=/data/projects \
    AUTOREIV_SERVE_HOST=0.0.0.0 \
    AUTOREIV_SERVE_PORT=8000 \
    OLLAMA_HOST=http://host.docker.internal:11434 \
    OLLAMA_MODEL=qwen2.5:7b \
    PORT=8000 \
    HOST=0.0.0.0

USER autoreiv

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health')" || exit 1

# Entry point
CMD ["python", "-m", "src.cli.main", "serve", "--host", "0.0.0.0", "--port", "8000"]
