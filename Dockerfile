# Stage 1: Lean 4 + Mathlib cache
FROM ubuntu:22.04 AS lean-base

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y \
    curl git cmake gcc g++ make libgmp-dev \
    && rm -rf /var/lib/apt/lists/*

# Install elan (Lean version manager)
RUN curl -sSf https://raw.githubusercontent.com/leanprover/elan/master/elan-init.sh | bash -s -- -y --default-toolchain none
ENV PATH="/root/.elan/bin:${PATH}"

# Install Lean 4 v4.18.0 via elan
RUN elan toolchain install leanprover/lean4:v4.18.0 && \
    elan default leanprover/lean4:v4.18.0

WORKDIR /app/verina

# Copy verina lake project files for dependency caching
COPY verina/lakefile.lean verina/lean-toolchain verina/lake-manifest.json ./
# Note: verina/ is a git submodule inside this repo
RUN mkdir -p lean-playground && touch lean-playground/.gitkeep

# Fetch dependencies and download pre-built Mathlib oleans
RUN lake update && lake exe cache get || true

# Stage 2: Python environment
FROM lean-base AS python-base

RUN apt-get update && apt-get install -y \
    python3.11 python3.11-venv python3.11-dev python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}"

WORKDIR /app

# Copy verina source for library import
COPY verina/pyproject.toml /app/verina/pyproject.toml
COPY verina/src /app/verina/src
RUN touch /app/verina/README.md

# Copy pipeline project
COPY pyproject.toml /app/mbpp_lean_pipeline/pyproject.toml

# Install all Python deps
RUN cd /app/mbpp_lean_pipeline && uv sync

# Stage 3: Final image
FROM python-base AS runtime

WORKDIR /app/mbpp_lean_pipeline

# Copy pipeline source code
COPY src /app/mbpp_lean_pipeline/src
COPY configs /app/mbpp_lean_pipeline/configs

ENV PYTHONPATH="/app/verina/src:/app/mbpp_lean_pipeline/src:${PYTHONPATH}"
ENV LEAN_WORKING_DIR="/app/verina"

ENTRYPOINT ["uv", "run"]
CMD ["mbpp-pipeline", "--help"]
