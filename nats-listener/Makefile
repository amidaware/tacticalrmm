.PHONY: test test-integration build vet tidy

# Default: run unit tests only. Integration tests require the embedded
# nats-server to boot, which adds ~500ms to the run — gated on a build tag.
test:
	go test -race ./...

test-integration:
	go test -race -tags=integration -count=1 ./...

build:
	go build ./...

vet:
	go vet ./...

tidy:
	go mod tidy
