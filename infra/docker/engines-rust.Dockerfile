# ── Stage 1: Builder ─────────────────────────────────
FROM rust:1.83-slim AS builder

WORKDIR /app

# Install build tools needed by pyo3, openssl, and other C-linked Rust crates
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    pkg-config \
    libssl-dev \
    libffi-dev \
    python3-dev \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Copy workspace manifest first (Cargo workspace uses members, not a single Cargo.toml)
COPY engines/rust/Cargo.toml engines/rust/Cargo.lock ./
COPY engines/rust/crates ./crates

# Build all workspace members in release mode
RUN cargo build --release

# ── Stage 2: Runtime ─────────────────────────────────
FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libssl3 \
    python3 \
    && rm -rf /var/lib/apt/lists/*

# Copy all compiled binaries and shared libraries
COPY --from=builder /app/target/release/ /usr/local/bin/

# This container exposes the pre-built .so wheels via a volume in docker-compose
# or can be used as a base for the Python services that do FFI calls.
CMD ["echo", "Rust engines built — binaries at /usr/local/bin/"]
