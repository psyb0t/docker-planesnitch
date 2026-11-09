---
title: "Development"
description: "How planesnitch is laid out and built: module map, Make targets for tests, lint and formatting, and the main-branch and tag release pipeline."
nav_order: 11
---

# Development

planesnitch is plain Python 3.12 with two runtime dependencies, `aiohttp` and `PyYAML`, listed in [`requirements.txt`](https://github.com/psyb0t/docker-planesnitch/blob/main/requirements.txt). Everything runs in Docker, so the host needs only Docker and Make.

## Layout

| Path | Job |
| --- | --- |
| [`planesnitch/__main__.py`](https://github.com/psyb0t/docker-planesnitch/blob/main/planesnitch/__main__.py) | Entry point, poll loop, config reload, health endpoint, dispatch to targets |
| `planesnitch/config.py` | Config loading and validation, units, durations, squawk meanings |
| `planesnitch/sources.py` | ADS-B API and ultrafeeder fetching, location grouping, rate limits, dedup |
| `planesnitch/geo.py` | Distances and bounding circles |
| `planesnitch/watchlists.py` | Watchlist loading and matching, CSV parsing |
| `planesnitch/alerts.py` | Rule matching and cooldowns |
| `planesnitch/notify.py` | Telegram and webhook formatting and sending |
| `planesnitch/images.py` | doc8643.com aircraft-type photo cache |
| `planesnitch/*_test.py` | pytest tests next to each module |
| [`config.yaml.example`](https://github.com/psyb0t/docker-planesnitch/blob/main/config.yaml.example) | The starting config |

## Make targets

```bash
make build    # build psyb0t/planesnitch:latest
make test     # pytest in the test image
make lint     # ruff check, ruff format --check, mypy in the test image
make format   # ruff --fix and ruff format
make clean    # remove the built images
make help     # list the targets
```

`test`, `lint` and `format` build `psyb0t/planesnitch:latest-test`, mount the checkout into it as your own user, and install the pinned tools from [`requirements-dev.txt`](https://github.com/psyb0t/docker-planesnitch/blob/main/requirements-dev.txt). Tests need no network and no credentials.

Run it from a checkout with a local config:

```bash
make build
docker run --rm \
  -v ./config.yaml:/app/config.yaml:ro \
  -v ./csv:/csv:ro \
  psyb0t/planesnitch
```

## Release pipeline

The [pipeline](https://github.com/psyb0t/docker-planesnitch/blob/main/.github/workflows/pipeline.yml) runs on pushes to any branch and on `v*` tags:

- Every branch push runs `make lint` and `make test`. On `main` it then builds the image for `linux/amd64` and `linux/arm64`, scans it, and pushes `:latest` and `:sha-<commit>`.
- A tag waits for that commit's `main` run to succeed, then points `:vX.Y.Z` at the already-built `:sha-<commit>` image without rebuilding. It fails if the `main` run failed, never appeared or timed out.
- After the image is promoted, a separate job creates the GitHub release from the annotated tag notes, and then the skill is published to ClawHub.

Push release commits to `main` before tagging them, or the tag has nothing to promote. Image scan findings go to the Security tab without failing the run.

## Documentation

This site is built by GitHub Pages from [`docs/`](https://github.com/psyb0t/docker-planesnitch/tree/main/docs) on `main` with Jekyll and the Just the Docs theme. Every page needs front matter with a `title`, a `description` of 50 to 170 characters and a `nav_order`. Link between pages with relative `.md` paths and to files outside `docs/` with full GitHub URLs. Keep each prose paragraph on one line.
