# Docker image configuration
IMAGE_NAME := psyb0t/planesnitch
TAG := latest
TEST_TAG := $(TAG)-test

.PHONY: build build-test test lint format clean docs docs-build docs-lock help

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

# The documentation site in website/ builds the pages in docs/ with Docusaurus
# inside a pinned Node image. The install step downloads the locked packages
# through pnpm's age gate; the build itself runs with no network. The packages
# live in .testing/docs-cache/node_modules so the image build context, which
# copies the whole checkout, never receives them.
DOCS_NODE_IMAGE := node:24.21.0-bookworm-slim@sha256:d6aa754f16b3197301076f047b5def2f02ea1dbbc2ca920407d46d7ec7f87b20
DOCS_CACHE := .testing/docs-cache
DOCS_RUN := docker run --rm --init --cap-drop ALL --security-opt no-new-privileges:true \
	--user $(shell id -u):$(shell id -g) -e HOME=/tmp -e COREPACK_HOME=/cache/corepack \
	-v "$(CURDIR)/$(DOCS_CACHE):/cache" \
	-v "$(CURDIR)/docs:/work/docs:ro" -v "$(CURDIR)/website:/work/website" \
	-v "$(CURDIR)/$(DOCS_CACHE)/node_modules:/work/website/node_modules" -w /work/website

# Build the documentation site and check its links
docs: docs-build

# Build the documentation site into website/build
docs-build:
	mkdir -p "$(DOCS_CACHE)/node_modules" website/node_modules
	$(DOCS_RUN) $(DOCS_NODE_IMAGE) corepack pnpm install --frozen-lockfile --ignore-scripts --store-dir /cache/pnpm
	$(DOCS_RUN) --network none $(DOCS_NODE_IMAGE) corepack pnpm run build

# Refresh the documentation lockfile under the dependency age gate
docs-lock:
	mkdir -p "$(DOCS_CACHE)/node_modules" website/node_modules
	$(DOCS_RUN) $(DOCS_NODE_IMAGE) corepack pnpm install --lockfile-only --ignore-scripts --store-dir /cache/pnpm

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
	@echo "  docs       - Build the documentation site and check its links"
	@echo "  docs-lock  - Refresh the documentation lockfile"
	@echo "  clean      - Remove built images"
	@echo "  help       - Show this help message"
