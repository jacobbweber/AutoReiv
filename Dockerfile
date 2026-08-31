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
RUN pip install --no-cache-dir --prefix=/install .

# Stage 2: Final Minimal Runtime Image
FROM python:3.12-slim AS runner

WORKDIR /app

# Create unprivileged system user
RUN groupadd -g 1000 autoreiv && \
    useradd -u 1000 -g autoreiv -s /bin/bash -m autoreiv

# Copy installed dependencies from builder
COPY --from=builder /install /usr/local

# Copy application source code, packs, and metadata
COPY --chown=autoreiv:autoreiv src/ ./src/
COPY --chown=autoreiv:autoreiv platform-packs/ ./platform-packs/
COPY --chown=autoreiv:autoreiv agent-packs/ ./agent-packs/
COPY --chown=autoreiv:autoreiv pyproject.toml ./
COPY --chown=autoreiv:autoreiv README.md ./

# Create persistent data and wiki mount directories
RUN mkdir -p /data/wiki && \
    chown -R autoreiv:autoreiv /data

# Default environment configuration
ENV PYTHONUNBUFFERED=1 \
    AUTOREIV_DATA_DIR=/data \
    OLLAMA_HOST=http://host.docker.internal:11434 \
    OLLAMA_MODEL=qwen2.5:7b \
    PORT=8000 \
    HOST=0.0.0.0

USER autoreiv

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/agents')" || exit 1

# Entry point
CMD ["python", "-m", "src.cli.main", "serve", "--host", "0.0.0.0", "--port", "8000"]
