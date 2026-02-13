FROM rust:1.75-slim AS builder
WORKDIR /app
COPY engines/rust/ .
RUN cargo build --release

FROM debian:bookworm-slim
COPY --from=builder /app/target/release/ /usr/local/bin/
CMD ["echo", "Rust engines built — use as library via FFI"]
