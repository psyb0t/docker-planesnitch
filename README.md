# 🛩️ planesnitch

[![CI](https://github.com/psyb0t/docker-planesnitch/actions/workflows/pipeline.yml/badge.svg?branch=main)](https://github.com/psyb0t/docker-planesnitch/actions/workflows/pipeline.yml)
[![version](https://raw.githubusercontent.com/psyb0t/docker-planesnitch/badges/version.svg)](https://github.com/psyb0t/docker-planesnitch/releases)
[![license](https://raw.githubusercontent.com/psyb0t/docker-planesnitch/badges/license.svg)](LICENSE)
[![Docker Pulls](https://img.shields.io/docker/pulls/psyb0t/planesnitch?style=flat-square)](https://hub.docker.com/r/psyb0t/planesnitch)

Snitches on every interesting aircraft that dares fly near your locations: military jets, government spooks, emergency squawks, sketchy low-flyers, or whatever the fuck you tell it to watch for. Monitor multiple locations at once: your house, your office, grandma's house, Area 51, whatever. Rats them out straight to your Telegram or webhook like a paranoid neighbor with radar.

No SDR required. No antenna. No hardware. Just an internet connection and a config file. Works anywhere on the fuckin planet, for as many places as you want.

## Contents

- [🚀 Quick start](#-quick-start)
- [⚙️ How you configure it](#️-how-you-configure-it)
- [🔔 What the alerts look like](#-what-the-alerts-look-like)
- [📚 Documentation](#-documentation)
- [🤖 Agent integrations](#-agent-integrations)
- [🛠️ Development](#️-development)
- [☕ Sponsor](#-sponsor)
- [📝 License](#-license)

## 🚀 Quick start

Grab the example config and put in your location and Telegram bot:

```bash
curl -sL \
  https://raw.githubusercontent.com/psyb0t/docker-planesnitch/main/config.yaml.example \
  -o config.yaml
```

The example also watches military, government and police aircraft from [plane-alert-db](https://github.com/sdr-enthusiasts/plane-alert-db). Grab those lists:

```bash
mkdir -p csv
BASE=https://raw.githubusercontent.com/sdr-enthusiasts/plane-alert-db/main
for list in mil gov pol civ pia; do
  curl -sLo "csv/plane-alert-$list.csv" "$BASE/plane-alert-$list.csv"
done
curl -sLo csv/plane-alert-db.csv "$BASE/plane-alert-db.csv"
```

Let it rip:

```bash
docker run -d --name planesnitch \
  --restart unless-stopped \
  -v ./config.yaml:/app/config.yaml:ro \
  -v ./csv:/csv:ro \
  -v ./images:/images \
  psyb0t/planesnitch
```

```text
2026-03-07 22:25:39 [planesnitch] INFO planesnitch starting
2026-03-07 22:25:39 [planesnitch] INFO health endpoint listening on :8080
2026-03-07 22:25:40 [planesnitch] INFO watchlist military: 8709 aircraft loaded
2026-03-07 22:25:40 [planesnitch] INFO fetched 14 aircraft
2026-03-07 22:25:40 [planesnitch] INFO ALERT [Military Spotter] [Home] ae07e1 TEDDY64
```

The [getting started guide](https://psyb0t.github.io/docker-planesnitch/getting-started/) walks through the Telegram bot setup and your first test alert.

## ⚙️ How you configure it

One YAML file. Define where to watch, where the data comes from, what to snitch on, when to lose your shit, and where to scream about it:

```yaml
locations:
  home:
    name: "Home"
    lat: 38.8719
    lon: -77.0563
    radius: 150km

sources:
  - type: adsb_fi
  - type: airplanes_live

watchlists:
  emergencies:
    type: squawk
    values: ["7500", "7600", "7700"]
  military:
    type: icao_csv
    source: plane-alert-mil.csv

alerts:
  - name: "Military Spotter"
    watchlists: [emergencies, military]
    cooldown: 5m
    notify: [tg_main]

notifications:
  tg_main:
    type: telegram
    bot_token: "123456:ABC-DEF"
    chat_id: "-100123456789"
```

Six watchlist types: `all`, `squawk`, `icao`, `icao_type`, `icao_csv` and `proximity` (the "what just buzzed my house" altitude filter). Alerts go to Telegram, with an aircraft-type photo, or to webhooks as JSON. Edit the file while it runs; the next poll picks it up. Every key is in the [configuration reference](https://psyb0t.github.io/docker-planesnitch/configuration/).

## 🔔 What the alerts look like

```text
🔔 Military Spotter
✈️ TEDDY64
🛩️ BOEING C-17A Globemaster III | 94-0067 | 1994
💼 USAF
🏷️ USAF — US Military
📍 37.9306, -78.7019 | 12,350 ft
📏 99 nm from Home
💨 413 kts
📡 squawk 1613
🗺️ https://globe.adsb.fi/?icao=ae07e1
```

Click the link, watch the bastard in real time on [globe.adsb.fi](https://globe.adsb.fi). The webhook payload is documented in [notifications](https://psyb0t.github.io/docker-planesnitch/notifications/#webhook).

## 📚 Documentation

The whole manual lives at **[psyb0t.github.io/docker-planesnitch](https://psyb0t.github.io/docker-planesnitch/)**.

| Page | What's in it |
| --- | --- |
| [Getting started](https://psyb0t.github.io/docker-planesnitch/getting-started/) | Config, Telegram bot, CSVs, first alert |
| [Configuration](https://psyb0t.github.io/docker-planesnitch/configuration/) | Every key, unit and default, plus env variables |
| [Watchlists](https://psyb0t.github.io/docker-planesnitch/watchlists/) | The six types and the plane-alert-db lists |
| [Notifications](https://psyb0t.github.io/docker-planesnitch/notifications/) | Telegram format, photos, the webhook payload |
| [How it works](https://psyb0t.github.io/docker-planesnitch/how-it-works/) | Polling, sources, rate limits, dedup, cooldowns, health endpoint |
| [Deployment](https://psyb0t.github.io/docker-planesnitch/deployment/) | Docker, Compose, volumes, image tags, upgrades |
| [Security](https://psyb0t.github.io/docker-planesnitch/security/) | What leaves your machine and how to lock it down |
| [Troubleshooting](https://psyb0t.github.io/docker-planesnitch/troubleshooting/) | Every error message and what to do about it |

## 🤖 Agent integrations

The [skill](.agents/skills/planesnitch) works in any agent that reads `.agents/skills/` (such as [peen](https://github.com/psyb0t/peen)), and installs natively in Claude Code, Codex and OpenClaw:

```bash
claude plugin marketplace add psyb0t/agents
claude plugin install planesnitch@psyb0t
```

Codex and OpenClaw commands are on the [agent integrations page](https://psyb0t.github.io/docker-planesnitch/integrations/).

## 🛠️ Development

```bash
make test   # pytest in Docker
make lint   # ruff + mypy in Docker
make help   # everything else
```

Not 47 microservices. It watches planes and sends messages. That's it. Layout and the release pipeline are in [development](https://psyb0t.github.io/docker-planesnitch/development/).

## ☕ Sponsor

<a href="https://www.buymeacoffee.com/psyb0t"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-blue.png" alt="Buy Me a Coffee" height="60" width="217"></a>

## 📝 License

[WTFPL](LICENSE). Do What The Fuck You Want To. See [CHANGELOG.md](CHANGELOG.md) for release notes.
