# Builds HydraDB (open-source, self-hosted) from the local checkout.
# A trimmed copy of the upstream Dockerfile: graph-node + graph-indexer only.
# Build context is the HydraDB checkout:
#   docker build -f bearings/docker/hydradb.Dockerfile -t bearings-hydradb ../hydradb
FROM ubuntu:24.04 AS chef
ARG RUST_VERSION=1.99.0
ENV DEBIAN_FRONTEND=noninteractive CARGO_HOME=/usr/local/cargo RUSTUP_HOME=/usr/local/rustup \
    RUSTUP_TOOLCHAIN=${RUST_VERSION} PATH=/usr/local/cargo/bin:${PATH}
RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential ca-certificates clang cmake curl git libclang-dev \
      libcypher-parser-dev libffi-dev libgraphblas-dev pkg-config && \
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | \
      sh -s -- -y --profile minimal --default-toolchain "${RUST_VERSION}" && \
    rm -rf /var/lib/apt/lists/*
WORKDIR /workspace

FROM chef AS builder
COPY scripts/install_lagraph.sh /tmp/install_lagraph.sh
RUN bash /tmp/install_lagraph.sh /opt/lagraph
ENV LAGRAPH_LIB_DIR=/opt/lagraph/lib CARGO_BUILD_JOBS=8
COPY . .
RUN cargo build --locked --release --features server-runtime,indexer-runtime \
      --bin graph-node --bin graph-indexer && \
    mkdir -p /out && cp target/release/graph-node target/release/graph-indexer /out/ && \
    strip --strip-debug /out/graph-node && strip /out/graph-indexer

FROM ubuntu:24.04 AS runtime
ENV DEBIAN_FRONTEND=noninteractive RUST_LOG=info
RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates libcypher-parser-dev libgraphblas-dev curl && \
    rm -rf /var/lib/apt/lists/*
COPY --from=builder /out/graph-node /out/graph-indexer /usr/local/bin/
EXPOSE 7687 8443 9090
ENTRYPOINT ["/usr/local/bin/graph-node"]
