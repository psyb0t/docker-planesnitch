---
title: "Notifications"
description: "How planesnitch sends alerts to Telegram and webhooks: message format, batching, aircraft-type photos, the webhook JSON payload and match fields."
nav_order: 5
---

# Notifications

Alerts go to named targets under `notifications`, and [alert rules](configuration.md#alerts) list the targets they notify. There are two types: `telegram` and `webhook`. One rule can notify several targets of either type.

## Telegram

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
    attach_image: false
```

[Getting started](getting-started.md#2-create-a-telegram-bot) shows how to get the token and chat ID. A target with an empty `bot_token` or `chat_id` is skipped with `telegram <name> missing bot_token or chat_id` in the log.

### What a message looks like

```text
🔔 Emergency Alert
🚨 squawk 7700 (Emergency, global)
✈️ RYR1234
🛩️ BOEING 737-800 | EI-ABC | 2015
💼 RYANAIR
📍 45.5000, 28.1000 | 3,200 ft
📏 6 nm from Home
💨 280 kts
🗺️ https://globe.adsb.fi/?icao=4ca123
```

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

Each line appears only when the data has it:

| Line | Comes from |
| --- | --- |
| 🔔 | The rule name |
| 🚨 | The matched squawk, for `squawk` watchlists, with its meaning when planesnitch knows the code |
| ✈️ | Callsign |
| 🛩️ | Type description (or type code), registration, year |
| 💼 | Owner or operator, from enriched sources |
| 🏷️ | The `Operator` and `Category` columns of a CSV watchlist match |
| 📍 | Position and altitude |
| 📏 | Distance from the matched location |
| 💨 | Ground speed |
| 📡 | The transponder squawk, for every other watchlist type |
| 🗺️ | A live link on [globe.adsb.fi](https://globe.adsb.fi) |

Known squawk meanings cover the global emergency and special codes (7700, 7600, 7500, 7400, 7777 and others) plus common EU and US codes, each labelled with its scope.

### Batching and photos

Within one poll, text-only alerts for the same target are joined into as few messages as possible, up to Telegram's 4,096-character limit. Alerts with a photo go out one by one as a photo with the alert text as its caption. A caption longer than 1,024 characters is sent as a separate text message, followed by the photo without a caption. If sending a photo fails, the text is sent on its own instead, so the alert still arrives.

## Webhook

```yaml
notifications:
  my_webhook:
    type: webhook
    url: "https://example.com/hook"
    headers:
      Authorization: "Bearer xxx"
```

Every poll that triggers alerts for a target sends one `POST` with a JSON array, one object per alert, even when there's only one. `Content-Type: application/json` is set unless your `headers` override it. planesnitch doesn't retry: a failed or `4xx`/`5xx` request is logged as `webhook send failed` or `webhook send error`, and those alerts are gone. Requests time out after 10 seconds.

```json
[
  {
    "alert": "Military Spotter",
    "location": "Home",
    "match": {
      "distance_km": 183.2,
      "reason": "icao_csv_match",
      "info": {
        "Registration": "94-0067",
        "Operator": "USAF",
        "Type": "BOEING C-17A Globemaster III",
        "ICAO Type": "C17",
        "CMPG": "Mil",
        "Tag 1": "Cargo",
        "Category": "US Military",
        "Link": "https://w.wiki/..."
      },
      "watchlist": "military"
    },
    "units": {
      "altitude": "ft",
      "distance": "nm",
      "speed": "kts"
    },
    "image_base64": "/9j/4AAQSkZJRgABAQ...",
    "aircraft": {
      "hex": "ae07e1",
      "flight": "TEDDY64",
      "registration": "94-0067",
      "type": "C17",
      "description": "BOEING C-17A Globemaster III",
      "owner_operator": "USAF",
      "year": "1994",
      "squawk": "1613",
      "squawk_meaning": null,
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

- `location` is the location's `name`, or its key when it has none.
- `units` says which units `altitude`, `distance` and `speed` use; see [display units](configuration.md#display-units). `match.distance_km` is always kilometres.
- `image_base64` is the aircraft-type JPEG, or `null` when there's none or the target sets `attach_image: false`.
- `squawk_meaning` is `{"meaning": ..., "scope": ...}` for a known code, else `null`.
- Fields the sources didn't report are `null`, except `flight`, which is an empty string. `altitude` is `null` for aircraft on the ground.

The `match` object depends on the watchlist type:

| Watchlist type | `reason` | Extra fields |
| --- | --- | --- |
| `squawk` | `squawk` | `squawk` |
| `icao` | `icao_match` | none |
| `icao_type` | `icao_type_match` | `type` |
| `icao_csv` | `icao_csv_match` | `info`: the CSV row, without the hex column |
| `all` | `all` | none |
| `proximity` | `proximity` | none |

Every `match` also has `watchlist` and `distance_km`.

## Aircraft-type photos

When an aircraft reports its ICAO type, planesnitch fetches that type's photo from [doc8643.com](https://doc8643.com) and caches it in the images directory (`/images`, or `PLANESNITCH_IMAGES_DIR`). Types with no photo get a `.notfound` marker, so they aren't fetched again. Nothing expires the cache; delete the directory to refresh it. Mount it as a volume to keep it across restarts.

Set `attach_image: false` on a target to leave the photo out. If none of a rule's targets want photos, planesnitch doesn't fetch one at all.
