# Copyright (c) 2025 Harrold Holdings GmbH
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license information.

# Media Intelligence Pipeline - Containerfile (Podman/OCI)
# Multi-stage build for optimized image size
# Build: podman build -t media-intelligence:latest .
# Run:   podman run --rm media-intelligence:latest --help

# =============================================================================
# Stage 1: Builder - Install dependencies and download models
# =============================================================================
FROM python:3.11-slim-bookworm AS builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install build dependencies and uv
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    libffi-dev \
    libsndfile1 \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
ENV UV_INSTALL_DIR="/usr/local/bin"
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment with uv
RUN uv venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" \
    VIRTUAL_ENV="/opt/venv"

# Install Python dependencies with uv
COPY pyproject.toml uv.lock* /tmp/
WORKDIR /tmp
RUN uv sync --frozen 2>/dev/null || uv sync

# Pre-download models to cache (optional - makes first run faster)
# Note: HuggingFace models will be cached in /root/.cache/huggingface
RUN python -c "from faster_whisper import WhisperModel; WhisperModel('base.en', device='cpu', compute_type='int8')" || true
RUN python -c "from transformers import AutoFeatureExtractor, ASTForAudioClassification; \
    AutoFeatureExtractor.from_pretrained('MIT/ast-finetuned-audioset-10-10-0.4593'); \
    ASTForAudioClassification.from_pretrained('MIT/ast-finetuned-audioset-10-10-0.4593')" || true

# =============================================================================
# Stage 2: Runtime - Minimal image for production
# =============================================================================
FROM python:3.11-slim-bookworm AS runtime

# Labels
LABEL org.opencontainers.image.title="Media Intelligence Pipeline" \
      org.opencontainers.image.description="Audio transcription, diarization, and situation detection" \
      org.opencontainers.image.version="1.0.0" \
      org.opencontainers.image.vendor="Harrold Holdings GmbH" \
      org.opencontainers.image.licenses="Apache-2.0"

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    OMP_NUM_THREADS=4 \
    MKL_NUM_THREADS=4 \
    TRANSFORMERS_CACHE=/root/.cache/huggingface \
    HF_HOME=/root/.cache/huggingface

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libsndfile1 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy model cache from builder
COPY --from=builder /root/.cache /root/.cache

# Create application directory
WORKDIR /app

# Copy application code
COPY src/ /app/src/

# Create data directories
RUN mkdir -p /data/input /data/output

# Set up entrypoint
ENTRYPOINT ["python", "-m", "src.process_audio"]
CMD ["--help"]

# Default volumes
VOLUME ["/data/input", "/data/output", "/root/.cache"]

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import src.utils; print('OK')" || exit 1
