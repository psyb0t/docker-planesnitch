---
title: "Deployment"
description: "Run planesnitch with Docker or Compose: image tags, the config, CSV and image-cache volumes, the health check, upgrades and what state survives a restart."
nav_order: 7
---

# Deployment

planesnitch ships as the Docker image [`psyb0t/planesnitch`](https://hub.docker.com/r/psyb0t/planesnitch) for `linux/amd64` and `linux/arm64`. It needs outbound HTTPS and nothing inbound.

## Image tags

| Tag | What it is |
| --- | --- |
| `latest` | The newest build of the `main` branch that passed lint and tests |
| `sha-<commit>` | The build of one `main` commit, by its full commit hash |
| `vX.Y.Z` | A release. Release tags reuse the image digest already built on `main` |

Pin a `vX.Y.Z` tag if you want it to hold still, and read the [changelog](https://github.com/psyb0t/docker-planesnitch/blob/main/CHANGELOG.md) before moving.

## Docker

```bash
docker run -d --name planesnitch \
  --restart unless-stopped \
  -v ./config.yaml:/app/config.yaml:ro \
  -v ./csv:/csv:ro \
  -v ./images:/images \
  -e LOG_LEVEL=INFO \
  psyb0t/planesnitch
```

| Mount | Needed | Holds |
| --- | --- | --- |
| `/app/config.yaml` | yes | Your config. Read-only is fine; planesnitch only reads it |
| `/csv` | for `icao_csv` watchlists | The CSV watchlist files |
| `/images` | no | Cached aircraft-type photos. Without it they're downloaded again after each restart |

Port `8080` is the [health endpoint](how-it-works.md#health-endpoint). Publish it only if something outside the container polls it, and keep it on loopback: `-p 127.0.0.1:8080:8080`.

## Docker Compose

```yaml
services:
  planesnitch:
    image: psyb0t/planesnitch:latest
    container_name: planesnitch
    restart: unless-stopped
    volumes:
      - ./config.yaml:/app/config.yaml:ro
      - ./csv:/csv:ro
      - ./images:/images
    environment:
      LOG_LEVEL: INFO
```

```bash
docker compose up -d
docker compose logs -f planesnitch
```

## State

planesnitch keeps almost nothing:

| What | Where | Survives a restart |
| --- | --- | --- |
| Config | Your mounted file | yes |
| CSV watchlists | Your mounted `/csv` | yes |
| Aircraft-type photo cache | `/images` | only if mounted |
| Alert cooldowns | Memory | no. Aircraft in range alert again after a restart |
| Source rate-limit pauses | Memory | no |

There's no database and nothing to back up beyond your config and CSVs.

## Changing the config

Edit the mounted `config.yaml`; the next poll picks it up, no restart needed. With a single-file bind mount, some editors replace the file instead of rewriting it, and the container keeps seeing the old one. If an edit doesn't show up in the logs as `config reloaded (changed)`, mount the containing directory instead, or restart the container.

## Upgrade

```bash
docker pull psyb0t/planesnitch:latest
docker rm -f planesnitch
# then run the same docker run command again
```

With Compose: `docker compose pull && docker compose up -d`.
