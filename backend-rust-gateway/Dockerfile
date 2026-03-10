# MediCanna AI - Rust API Gateway (Port 8080) - Multi-stage 縮小體積
FROM rust:1.75-slim-bookworm AS builder
WORKDIR /app
COPY Cargo.toml Cargo.lock ./
COPY src ./src
RUN cargo build --release

FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*
COPY --from=builder /app/target/release/backend-rust-gateway /usr/local/bin/
EXPOSE 8080
CMD ["backend-rust-gateway"]
