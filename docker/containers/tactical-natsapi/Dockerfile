# Build nats-api from source. Identical build stage to tactical-nats/Dockerfile.
# Build context is the repo root. CI invokes this as:
#   docker buildx build -f docker/containers/tactical-natsapi/Dockerfile .
FROM --platform=$BUILDPLATFORM golang:1.26-alpine AS build

ARG TARGETOS
ARG TARGETARCH

WORKDIR /src

# Module files first so `go mod download` is cached independently of source.
COPY natsapi/go.mod natsapi/go.sum ./
RUN go mod download

# Copy the rest of the natsapi module (library .go files + cmd/nats-api/).
COPY natsapi/ ./

RUN CGO_ENABLED=0 GOOS=${TARGETOS} GOARCH=${TARGETARCH} \
    go build -trimpath -ldflags "-s -w" -o /out/nats-api ./cmd/nats-api

# Minimal runtime: no nats-server, no supervisord, no bash.
# ca-certificates needed for TLS connections (e.g. Postgres with SSL).
FROM alpine:3.21
RUN apk add --no-cache ca-certificates
COPY --from=build /out/nats-api /usr/local/bin/nats-api

USER 1000

# Prometheus metrics endpoint (gated on METRICS_LISTEN env var).
EXPOSE 9189

ENTRYPOINT ["/usr/local/bin/nats-api"]
