---
title: "Getting started"
description: "From nothing to your first planesnitch alert: write config.yaml, create a Telegram bot, download plane-alert-db CSVs, and run the container."
nav_order: 2
---

# Getting started

This page takes you from nothing to a Telegram message about a real aircraft. You need Docker and a Telegram account.

## 1. Get the example config

```bash
curl -sL \
  https://raw.githubusercontent.com/psyb0t/docker-planesnitch/main/config.yaml.example \
  -o config.yaml
```

Open it and set your location. The coordinates are decimal degrees, and the radius takes a unit suffix:

```yaml
locations:
  home:
    name: "Home"
    lat: 38.8719
    lon: -77.0563
    radius: 150km
```

## 2. Create a Telegram bot

1. Message [@BotFather](https://t.me/BotFather), send `/newbot`, and copy the token it gives you.
2. For alerts to yourself: send your bot any message, then open `https://api.telegram.org/bot<TOKEN>/getUpdates` and copy `message.chat.id`.
3. For a channel: add the bot as an admin, post something in the channel, then check `getUpdates` for the channel ID. It starts with `-100`.

Put both values into the `tg_main` target:

```yaml
notifications:
  tg_main:
    type: telegram
    bot_token: "123456:ABC-DEF"
    chat_id: "-100123456789"
```

## 3. Download the watchlist CSVs

The example config watches the military, government, police, civilian, privacy and "everything" lists from [plane-alert-db](https://github.com/sdr-enthusiasts/plane-alert-db). Download them into `csv/`:

```bash
mkdir -p csv
BASE=https://raw.githubusercontent.com/sdr-enthusiasts/plane-alert-db/main
for list in mil gov pol civ pia; do
  curl -sLo "csv/plane-alert-$list.csv" "$BASE/plane-alert-$list.csv"
done
curl -sLo csv/plane-alert-db.csv "$BASE/plane-alert-db.csv"
```

Skip this and remove the `icao_csv` watchlists from the config if you only care about squawks or your own lists. A missing CSV doesn't stop planesnitch; that watchlist just stays empty and the log says `failed to load watchlist <name>`.

## 4. Run it

```bash
docker run -d --name planesnitch \
  -v ./config.yaml:/app/config.yaml:ro \
  -v ./csv:/csv:ro \
  -v ./images:/images \
  psyb0t/planesnitch
```

`/images` caches the aircraft-type photos that go with Telegram alerts, so they survive restarts.

## 5. Check it works

```bash
docker logs -f planesnitch
```

A healthy start looks like this:

```text
2026-03-07 22:25:39 [planesnitch] INFO planesnitch starting
2026-03-07 22:25:39 [planesnitch] INFO health endpoint listening on :8080
2026-03-07 22:25:40 [planesnitch] INFO loading watchlist military from /csv/plane-alert-mil.csv
2026-03-07 22:25:40 [planesnitch] INFO watchlist military: 8709 aircraft loaded
2026-03-07 22:25:40 [planesnitch] INFO fetched 14 aircraft
2026-03-07 22:25:40 [planesnitch] INFO ALERT [Military Spotter] [Home] ae07e1 TEDDY64
```

`fetched N aircraft` appears every poll (the example polls every minute). Want a test alert right away? Add an `all` watchlist to a rule, and anything in range triggers it:

```yaml
watchlists:
  everything:
    type: all

alerts:
  - name: "Everything at Home"
    watchlists: [everything]
    cooldown: 10m
    notify: [tg_main]
```

planesnitch re-reads `config.yaml` every poll, so the change applies without a restart. Remove it again once you've seen a message, or your chat fills up fast.

## Next

- [Configuration](configuration.md) for every key.
- [Watchlists](watchlists.md) to watch for exactly what you want.
- [Notifications](notifications.md) for webhooks and what the messages contain.
