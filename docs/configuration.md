---
title: "Configuration"
description: "Every planesnitch config.yaml key with its default: poll interval, display units, locations, sources, alert rules, notification targets and env variables."
nav_order: 3
---

# Configuration

Everything lives in one YAML file: `/app/config.yaml` in the container, or the path in `--config` or `PLANESNITCH_CONFIG`. The repository's [`config.yaml.example`](https://github.com/psyb0t/docker-planesnitch/blob/main/config.yaml.example) is a working starting point.

planesnitch re-reads the file at the start of every poll. A valid change applies on the next poll without a restart, and a change also reloads the CSV watchlists. Every value is checked when the file loads. If an edited file is broken, planesnitch logs `config reload failed, keeping current: <reason>` and keeps running with the last good config. A broken file at startup stops it instead; see [Troubleshooting](troubleshooting.md#startup-errors).

## Top level

| Key | Default | Meaning |
| --- | --- | --- |
| `locations` | required | Named places to watch |
| `sources` | required | Where aircraft data comes from |
| `watchlists` | required | What to look for, see [Watchlists](watchlists.md) |
| `alerts` | required | Rules that connect watchlists to notification targets |
| `notifications` | required | Telegram and webhook targets, see [Notifications](notifications.md) |
| `poll_interval` | `15` (seconds) | Time between polls. A [duration](#durations) |
| `display_units` | `aviation` | Units in alert text and webhook payloads |

All five required keys must be present, even if `watchlists` or `notifications` is empty.

## Units

Any distance or altitude takes a unit suffix: `km`, `mi`, `nm`, `ft` or `m`, with or without a space. `radius: 100mi` and `max_altitude: 1km` both work. A plain number means km for distances and ft for altitudes.

Instead of a suffix you can use a suffixed key: `radius_km`, `radius_mi` or `radius_nm` for distances, and `max_altitude_ft` or `max_altitude_m` for altitudes. Set only one form per value. An unparseable value fails with `invalid value for ...`, and two forms of the same value fail with `conflicting keys`.

### Durations

`poll_interval` and alert `cooldown` take plain seconds (`90`) or hours, minutes and seconds in that order: `90s`, `5m`, `2h`, `1h30m`.

### Display units

| `display_units` | Altitude | Distance | Speed |
| --- | --- | --- | --- |
| `aviation` | ft | nm | kts |
| `metric` | m | km | km/h |
| `imperial` | ft | mi | mph |

Any other value stops startup.

## Locations

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

| Key | Default | Meaning |
| --- | --- | --- |
| `lat`, `lon` | required | Decimal degrees |
| `radius` | `150km` | Watch radius. Aircraft farther away never match, whatever the watchlist |
| `name` | the key | Shown in alerts and webhook payloads |

At least one location is required. Locations close together are fetched with one request; see [How it works](how-it-works.md#fetching).

## Sources

```yaml
sources:
  - type: adsb_lol
  - type: adsb_fi
  - type: airplanes_live
  - type: adsb_one
  - type: ultrafeeder
    url: http://ultrafeeder:80/data/aircraft.json
```

| `type` | Data | Notes |
| --- | --- | --- |
| `adsb_lol` | Raw ADS-B fields | [adsb.lol](https://adsb.lol) public API |
| `adsb_fi` | Adds type name, owner/operator, year | [adsb.fi](https://adsb.fi) open data API |
| `airplanes_live` | Adds type name, owner/operator, year | [airplanes.live](https://airplanes.live) API |
| `adsb_one` | Adds type name, owner/operator, year | [adsb.one](https://adsb.one) API |
| `ultrafeeder` | Raw fields from your own receiver | Needs `url`, a readsb/tar1090 `aircraft.json` |

Use several. Every source is queried each poll and the results are merged per aircraft, keeping the entry with the most filled-in fields. An unknown `type` is skipped.

## Alerts

```yaml
alerts:
  - name: "Military Spotter"
    watchlists: [military, government]
    locations: [home]
    cooldown: 5m
    notify: [tg_main, my_webhook]
```

| Key | Default | Meaning |
| --- | --- | --- |
| `name` | required | Rule name, shown in the alert. Must be unique: cooldowns are tracked by name |
| `watchlists` | `[]` | Watchlist names to check, in order |
| `locations` | all locations | Only check these location keys |
| `cooldown` | `5m` | After a rule fires for an aircraft, the same rule ignores that aircraft for this long |
| `notify` | `[]` | Notification target names |

Each rule fires at most once per aircraft per poll: the first watchlist and location that match win. Different rules are independent, so one aircraft can trigger several rules. Cooldowns live in memory and reset on restart.

## Notifications

Targets are named, and rules refer to them by name. Full details and the payload format are on [Notifications](notifications.md).

```yaml
notifications:
  tg_main:
    type: telegram
    bot_token: "123456:ABC-DEF"
    chat_id: "-100123456789"
    attach_image: true

  my_webhook:
    type: webhook
    url: "https://example.com/hook"
    headers:
      Authorization: "Bearer xxx"
    attach_image: false
```

| Key | Type | Default | Meaning |
| --- | --- | --- | --- |
| `type` | both | required | `telegram` or `webhook` |
| `bot_token`, `chat_id` | telegram | required | Bot token and target chat. If either is empty, alerts for this target are skipped with a warning |
| `url` | webhook | required | Where to POST |
| `headers` | webhook | none | Extra request headers |
| `attach_image` | both | `true` | Include the aircraft-type photo |

## Environment variables

| Variable | Default | Meaning |
| --- | --- | --- |
| `PLANESNITCH_CONFIG` | `config.yaml` | Config file path when `--config` is not given. The image's command passes `--config /app/config.yaml`, so in Docker mount your file there or override the command |
| `PLANESNITCH_CSV_DIR` | `/csv` | Directory `icao_csv` watchlists read from |
| `PLANESNITCH_IMAGES_DIR` | `/images` | Aircraft-type photo cache |
| `LOG_LEVEL` | `INFO` | `DEBUG` logs every request, aircraft and match decision |
