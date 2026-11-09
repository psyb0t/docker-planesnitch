# Docker image configuration
IMAGE_NAME := psyb0t/planesnitch
TAG := latest
TEST_TAG := $(TAG)-test

.PHONY: build build-test test lint format clean help

# Default target
all: build

# Build the main image
build:
	docker build -t $(IMAGE_NAME):$(TAG) .

# Build the test image with -test suffix
build-test:
	docker build -t $(IMAGE_NAME):$(TEST_TAG) .

DEV_RUN := docker run --rm --user $(shell id -u):$(shell id -g) -e HOME=/tmp -e RUFF_CACHE_DIR=/tmp/ruff \
	-v $(CURDIR):/src -w /src $(IMAGE_NAME):$(TEST_TAG) sh -c

# Run tests inside a docker container
test: build-test
	$(DEV_RUN) "pip install --no-cache-dir -q --user -r requirements-dev.txt && python -m pytest -p no:cacheprovider planesnitch/ -v"

# Lint and type-check inside a docker container
lint: build-test
	$(DEV_RUN) "pip install --no-cache-dir -q --user -r requirements-dev.txt && python -m ruff check planesnitch && python -m ruff format --check planesnitch && python -m mypy --ignore-missing-imports --cache-dir /tmp/mypy planesnitch"

# Apply ruff formatting and safe fixes
format: build-test
	$(DEV_RUN) "pip install --no-cache-dir -q --user -r requirements-dev.txt && python -m ruff check --fix planesnitch && python -m ruff format planesnitch"

# Clean up images
clean:
	docker rmi $(IMAGE_NAME):$(TAG) || true
	docker rmi $(IMAGE_NAME):$(TEST_TAG) || true

# Show available targets
help:
	@echo "Available targets:"
	@echo "  build      - Build the main Docker image"
	@echo "  build-test - Build the test Docker image with -test suffix"
	@echo "  test       - Run tests in a Docker container"
	@echo "  lint       - Run ruff and mypy in a Docker container"
	@echo "  format     - Apply ruff formatting and safe fixes"
	@echo "  clean      - Remove built images"
	@echo "  help       - Show this help message"
