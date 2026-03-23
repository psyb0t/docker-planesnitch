# Docker image configuration
IMAGE_NAME := psyb0t/planesnitch
TAG := latest

.PHONY: all install-dev lint test build clean help

# Default target
all: test

install-dev:
	python -m pip install -e .[dev]

lint:
	python -m ruff check .

test:
	python -m pytest -q

# Build the main image
build:
	docker build -t $(IMAGE_NAME):$(TAG) .

# Clean up images
clean:
	docker rmi $(IMAGE_NAME):$(TAG) || true

# Show available targets
help:
	@echo "Available targets:"
	@echo "  install-dev - Install project and dev dependencies"
	@echo "  lint        - Run Ruff checks"
	@echo "  test        - Run the test suite locally"
	@echo "  build       - Build the Docker image"
	@echo "  clean       - Remove the built Docker image"
	@echo "  help        - Show this help message"
