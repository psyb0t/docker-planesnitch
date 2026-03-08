# 🛩️ planesnitch

Snitches on every interesting aircraft that dares fly near your locations — military jets, government spooks, emergency squawks, sketchy low-flyers, or whatever the fuck you tell it to watch for. Monitor multiple locations at once — your house, your office, grandma's house, Area 51, whatever. Rats them out straight to your Telegram or webhook like a paranoid neighbor with radar.

No SDR required. No antenna. No hardware. Just an internet connection and a config file. Alerts via Telegram and/or webhooks. Works anywhere on the fuckin planet — and for as many places as you want.

## Table of Contents

- [🚀 Quick Start](#-quick-start)
- [⚙️ Configuration](#️-configuration)
  - [Display Units](#display-units)
  - [Locations](#locations)
  - [Sources](#sources)
  - [Watchlists](#watchlists)
  - [Alerts](#alerts)
  - [Notifications](#notifications)
  - [What the alerts look like](#what-the-alerts-look-like)
- [🤖 Telegram Setup](#-telegram-setup)
- [🗃️ Plane-Alert-DB Lists](#️-plane-alert-db-lists)
- [📁 Project Structure](#-project-structure)
- [📝 License](#-license)

## 🚀 Quick Start

```bash
# grab the example config and edit it with your location + notification settings
curl -sL https://raw.githubusercontent.com/psyb0t/docker-planesnitch/main/config.yaml.example -o config.yaml

# optional: download CSV watchlists for military/gov/police tracking (see Plane-Alert-DB section below)

# let it rip — without CSV watchlists
docker run \
  -v ./config.yaml:/app/config.yaml:ro \
  psyb0t/planesnitch

# or with CSV watchlists — mount your csv/ dir
docker run \
  -v ./config.yaml:/app/config.yaml:ro \
  -v ./csv:/csv:ro \
  psyb0t/planesnitch
```

```
2026-03-07 22:25:39 [planesnitch] INFO planesnitch starting
2026-03-07 22:25:39 [planesnitch] INFO health endpoint listening on :8080
2026-03-07 22:25:40 [planesnitch] INFO watchlist military: 8709 aircraft loaded
2026-03-07 22:25:40 [planesnitch] INFO watchlist government: 1743 aircraft loaded
2026-03-07 22:25:40 [planesnitch] INFO fetched 14 aircraft
2026-03-07 22:25:40 [planesnitch] INFO ALERT [Military Spotter] [home] ae07e1 TEDDY64
```

## ⚙️ Configuration

Single YAML file. Define watchlists (what to snitch on), alert rules (when to lose your shit), and notification targets (where to scream about it).

### Display Units

Control how altitude, distance, and speed show up in alerts and webhook payloads:

```yaml
display_units: aviation  # default
```

| Preset     | Altitude | Distance | Speed |
| ---------- | -------- | -------- | ----- |
| `aviation` | ft       | nm       | kts   |
| `metric`   | m        | km       | km/h  |
| `imperial` | ft       | mi       | mph   |

### Locations

Define one or more named locations. Each location has coordinates and a search radius.

> **Units:** Any distance or altitude value in the config accepts a unit suffix: `km`, `mi`, `nm`, `ft`, `m`. They all convert internally — use whatever makes sense. `radius: 100mi` and `max_altitude: 1km` both work. Plain numbers without a suffix default to km for distances and ft for altitudes.

```yaml
locations:
  home:
    name: "Home"
    lat: 38.8719
    lon: -77.0563
    radius: 150km
  area51:
    name: "Area 51"
    lat: 37.2350
    lon: -115.8111
    radius: 50nm
```

Each location can have an optional `name` for pretty display in alerts. Falls back to the key if not set.

### Sources

Where to get the goods. Use multiple sources — they fetch in parallel for each location and deduplicate by ICAO hex, keeping the entry with the most data.

> **Note:** `adsb_fi`, `airplanes_live`, and `adsb_one` return enriched data (full aircraft name, owner/operator, year). `adsb_lol` and `ultrafeeder` only return raw ADS-B fields. When using multiple sources, planesnitch automatically keeps the richest entry for each aircraft.

```yaml
sources:
  # Public APIs — no hardware, no bullshit
  - type: adsb_lol
  - type: adsb_fi
  - type: airplanes_live
  - type: adsb_one

  # Local ultrafeeder — if you're running your own receiver
  - type: ultrafeeder
    url: http://ultrafeeder:80/tar1090/data/aircraft.json
```

### Watchlists

Tell the snitch what to look for:

| Type        | Matches On              | Source                                                                                                |
| ----------- | ----------------------- | ----------------------------------------------------------------------------------------------------- |
| `all`       | Every aircraft          | Matches anything in the location's radius                                                             |
| `squawk`    | Transponder squawk code | Inline list                                                                                           |
| `icao`      | ICAO hex address        | Inline list                                                                                           |
| `icao_csv`  | ICAO hex from CSV       | Local file in `csv/` dir ([plane-alert-db](https://github.com/sdr-enthusiasts/plane-alert-db) format) |
| `proximity` | Altitude filter         | Uses location radius + altitude limits                                                                |

```yaml
watchlists:
  # The panic buttons
  emergencies:
    type: squawk
    values: ["7500", "7600", "7700"]

  # 8,709 military aircraft — the big boys
  military:
    type: icao_csv
    source: plane-alert-mil.csv

  # Government aircraft
  government:
    type: icao_csv
    source: plane-alert-gov.csv

  # Police / law enforcement
  police:
    type: icao_csv
    source: plane-alert-pol.csv

  # Stalk specific aircraft by hex
  my_planes:
    type: icao
    values: ["4ca123", "a12345"]

  # Every single aircraft in range
  everything:
    type: all

  # WTF just buzzed my house
  low_flyers:
    type: proximity
    min_altitude: 0ft
    max_altitude: 3000ft
```

### Alerts

Connect watchlists to notifications. Optionally filter by `locations` — if omitted, all locations are checked. Cooldown so it doesn't spam the shit out of you about the same C-17 doing laps for 3 hours. Durations support `s`, `m`, `h` — e.g. `5m`, `1h30m`, `90s`, or plain seconds:

```yaml
alerts:
  - name: "Emergency Alert"
    watchlists: [emergencies]
    cooldown: 1m
    notify: [tg_emergencies, my_webhook]

  - name: "Military Spotter"
    watchlists: [military, government]
    cooldown: 5m
    notify: [tg_spotting]

  # Only alert for this watchlist at specific locations
  - name: "Everything at Home"
    locations: [home]
    watchlists: [everything]
    cooldown: 1m
    notify: [tg_main]
```

### Notifications

**Telegram** — different alerts to different channels:

```yaml
notifications:
  tg_emergencies:
    type: telegram
    bot_token: "123456:ABC-DEF"
    chat_id: "-100123456789"

  tg_spotting:
    type: telegram
    bot_token: "123456:ABC-DEF"
    chat_id: "-100987654321"
```

**Webhook** — POSTs a JSON array of alert objects per poll cycle:

```yaml
notifications:
  my_webhook:
    type: webhook
    url: "https://example.com/hook"
    headers:
      Authorization: "Bearer xxx"
```

Webhook payload schema — always a JSON array, even for a single alert:

```json
[
  {
    "alert": "Military Spotter",
    "location": "Home",
    "match": {
      "reason": "icao_csv_match",
      "watchlist": "military",
      "info": {
        "Registration": "94-0067",
        "Operator": "USAF",
        "Type": "BOEING C-17A Globemaster III",
        "ICAO Type": "C17",
        "CMPG": "Mil",
        "Tag 1": "Cargo",
        "Tag 2": "Strategic Airlift",
        "Tag 3": "Freedom Delivery",
        "Category": "US Military",
        "Link": "https://w.wiki/..."
      }
    },
    "units": {
      "altitude": "ft",
      "distance": "nm",
      "speed": "kts"
    },
    "aircraft": {
      "hex": "ae07e1",
      "flight": "TEDDY64",
      "registration": "94-0067",
      "type": "C17",
      "description": "BOEING C-17A Globemaster III",
      "owner_operator": "USAF",
      "year": "1994",
      "squawk": "1613",
      "emergency": "none",
      "altitude": 12350,
      "lat": 37.9306,
      "lon": -78.7019,
      "speed": 413,
      "track": 245.3,
      "distance": 98.9
    }
  }
]
```

The `match` object varies by watchlist type:

| Watchlist Type | Match Fields |
| -------------- | ------------ |
| `squawk` | `{"reason": "squawk", "watchlist": "...", "squawk": "7700"}` |
| `icao` | `{"reason": "icao_match", "watchlist": "..."}` |
| `icao_csv` | `{"reason": "icao_csv_match", "watchlist": "...", "info": {"Operator": "...", ...}}` |
| `all` | `{"reason": "all", "watchlist": "..."}` |
| `proximity` | `{"reason": "proximity", "watchlist": "...", "distance_km": 12.3}` |

### What the alerts look like

```
🔔 Emergency Alert
🚨 squawk 7700 (EMERGENCY)
✈️ RYR1234
🛩️ BOEING 737-800 | EI-ABC | 2015
💼 RYANAIR
📍 45.5000, 28.1000 | 3,200 ft
📏 6 nm from home
💨 280 kts
🗺️ https://globe.adsb.fi/?icao=4ca123
```

```
🔔 Military Spotter
✈️ TEDDY64
🛩️ BOEING C-17A Globemaster III | 94-0067 | 1994
💼 USAF
🏷️ USAF — USAF
📍 37.9306, -78.7019 | 12,350 ft
📏 99 nm from home
💨 413 kts
📡 squawk 1613
🗺️ https://globe.adsb.fi/?icao=ae07e1
```

Click the link, watch the bastard in real time on [globe.adsb.fi](https://globe.adsb.fi).

## 🤖 Telegram Setup

1. Message [@BotFather](https://t.me/BotFather), send `/newbot`, get a token
2. For personal alerts: message your bot, then check `https://api.telegram.org/bot<TOKEN>/getUpdates` for your chat ID
3. For channel alerts: add bot as admin, post something, check `getUpdates` for the channel ID (starts with `-100`)

## 🗃️ Plane-Alert-DB Lists

Uses the community-curated lists from [sdr-enthusiasts/plane-alert-db](https://github.com/sdr-enthusiasts/plane-alert-db) — 15,000+ aircraft catalogued by the fine degenerates of the plane spotting community:

| List             | Count  | File                  |
| ---------------- | ------ | --------------------- |
| 🎖️ Military      | 8,709  | [`plane-alert-mil.csv`](https://github.com/sdr-enthusiasts/plane-alert-db/blob/main/plane-alert-mil.csv) |
| 🏛️ Government    | 1,743  | [`plane-alert-gov.csv`](https://github.com/sdr-enthusiasts/plane-alert-db/blob/main/plane-alert-gov.csv) |
| 🚔 Police        | 932    | [`plane-alert-pol.csv`](https://github.com/sdr-enthusiasts/plane-alert-db/blob/main/plane-alert-pol.csv) |
| ✈️ Civilian      | 4,530  | [`plane-alert-civ.csv`](https://github.com/sdr-enthusiasts/plane-alert-db/blob/main/plane-alert-civ.csv) |
| 🔒 Privacy (PIA) | 94     | [`plane-alert-pia.csv`](https://github.com/sdr-enthusiasts/plane-alert-db/blob/main/plane-alert-pia.csv) |
| 📋 Everything    | 15,914 | [`plane-alert-db.csv`](https://github.com/sdr-enthusiasts/plane-alert-db/blob/main/plane-alert-db.csv)   |

Download what you need into your `csv/` directory:

```bash
mkdir -p csv
BASE=https://raw.githubusercontent.com/sdr-enthusiasts/plane-alert-db/main
curl -sLo csv/plane-alert-mil.csv $BASE/plane-alert-mil.csv
curl -sLo csv/plane-alert-gov.csv $BASE/plane-alert-gov.csv
curl -sLo csv/plane-alert-pol.csv $BASE/plane-alert-pol.csv
curl -sLo csv/plane-alert-civ.csv $BASE/plane-alert-civ.csv
curl -sLo csv/plane-alert-pia.csv $BASE/plane-alert-pia.csv
curl -sLo csv/plane-alert-db.csv  $BASE/plane-alert-db.csv
```

`plane-alert-db.csv` contains everything (mil + gov + pol + civ + pia) in one file. If you just want to watch all 15,000+ aircraft, use that one and skip the rest.

Re-download whenever you want fresh data. Or write your own CSV — just needs an ICAO hex column first.

## 📁 Project Structure

```
├── planesnitch/
│   ├── __init__.py
│   ├── __main__.py       # entry point + main loop
│   ├── config.py         # config loading, unit conversion, constants
│   ├── sources.py        # ADS-B API fetching + dedup
│   ├── geo.py            # distance calculations
│   ├── watchlists.py     # watchlist loading + matching
│   ├── alerts.py         # alert checking + cooldowns
│   └── notify.py         # telegram + webhook formatting + sending
├── config.yaml.example   # example config — copy to config.yaml and fill in your shit
├── csv/                  # CSV watchlists go here, mounted to /csv
├── run.sh                # build + run in docker
├── requirements.txt
├── Dockerfile
└── README.md
```

Not 47 microservices. It watches planes and sends messages. That's it.

Set `LOG_LEVEL` environment variable to `DEBUG` for verbose output (default: `INFO`). Other noisy libraries stay at `WARNING` so you only see planesnitch logs.

A health endpoint runs on port `8080`. The Docker image includes a built-in healthcheck against it.

## 📝 License

[WTFPL](LICENSE) — Do What The Fuck You Want To.
