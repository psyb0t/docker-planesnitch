---
title: "Home"
description: "planesnitch watches your locations for military, government, police and emergency aircraft and alerts you on Telegram or a webhook. No SDR needed."
nav_order: 1
permalink: /
seo:
  type: WebSite
---

# planesnitch

planesnitch snitches on every interesting aircraft that flies near your locations: military jets, government spooks, emergency squawks, sketchy low-flyers, or whatever you tell it to watch for. It polls free public ADS-B APIs (or your own receiver), matches what it sees against your watchlists, and rats the aircraft out to Telegram or a webhook.

No SDR. No antenna. No hardware. One Docker container and one config file, for as many locations as you want.

```text
public ADS-B APIs, or your own ultrafeeder
  │  one request per location group, merged by ICAO hex
  ▼
aircraft in range
  │  matched against watchlists and alert rules from config.yaml
  │  one cooldown per rule and aircraft
  ▼
Telegram (text, or photo with caption)  and/or  webhook (JSON array per poll)
```

## Quick start

Grab the example config and fill in your location and Telegram bot:

```bash
curl -sL \
  https://raw.githubusercontent.com/psyb0t/docker-planesnitch/main/config.yaml.example \
  -o config.yaml
```

Run it:

```bash
docker run -d --name planesnitch \
  -v ./config.yaml:/app/config.yaml:ro \
  psyb0t/planesnitch
```

The example config also watches the military, government and police lists from plane-alert-db. Those need CSV files mounted at `/csv`; [Getting started](getting-started.md) has the full walkthrough.

## Where to go next

| You want to | Read |
| --- | --- |
| Go from nothing to your first alert | [Getting started](getting-started.md) |
| Know every config key and its default | [Configuration](configuration.md) |
| Pick what to watch for | [Watchlists](watchlists.md) |
| Set up Telegram or a webhook, or parse the payload | [Notifications](notifications.md) |
| Understand polling, sources, rate limits and cooldowns | [How it works](how-it-works.md) |
| Run it for real: volumes, health check, image tags | [Deployment](deployment.md) |
| Know what leaves your machine | [Security](security.md) |
| Fix something | [Troubleshooting](troubleshooting.md) |
| Drive it from an AI agent | [Agent integrations](integrations.md) |
| Hack on the code | [Development](development.md) |
