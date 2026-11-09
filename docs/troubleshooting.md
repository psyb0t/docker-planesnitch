---
title: "Troubleshooting"
description: "planesnitch startup errors and runtime warnings with their exact messages, plus fixes for no aircraft, no alerts, missing photos and webhook failures."
nav_order: 9
---

# Troubleshooting

Turn on `LOG_LEVEL=DEBUG` first. It logs every request, every aircraft and every cooldown decision, so most questions answer themselves. Debug logs include your whole config, bot token included, so don't paste them anywhere public.

## Startup errors

These stop the container at startup. While it's running, the same problems in an edited config log `config reload failed, keeping current: <message>` and planesnitch keeps the last good config.

| Message | Fix |
| --- | --- |
| `config must be a YAML mapping` | The file is empty or isn't key-value YAML |
| `missing required config key: <key>` | Add the key. `locations`, `sources`, `watchlists`, `alerts` and `notifications` are all required |
| `locations must be a non-empty dict of named locations` | Give `locations` at least one named entry |
| `location '<name>' needs lat and lon` | Add both coordinates to that location |
| `invalid value for radius: ...` | Use a number or a suffixed value like `30km`, `50nm`, `100mi` |
| `invalid value for min_altitude: ...` or `max_altitude` | Use a number or a suffixed value like `3000ft`, `1km` |
| `conflicting keys: radius_km, radius_nm — pick one` | Keep one form of the value |
| `invalid display_units: ...` | Use `aviation`, `metric` or `imperial` |
| `invalid poll_interval: ...` or `invalid cooldown in alert '<name>': ...` | Use seconds or a duration like `90s`, `5m`, `1h30m` |
| A Python traceback ending in `FileNotFoundError` | The config isn't at `/app/config.yaml`. Check the `-v` mount path |

## Runtime warnings

| Message | Cause and fix |
| --- | --- |
| `failed to load watchlist <name>` | The CSV isn't in the CSV directory. Mount `-v ./csv:/csv:ro` and check the `source` file name |
| `unknown watchlist type <type> for <name>` | Typo in `type`; see [Watchlists](watchlists.md#types) |
| `notification target <name> not found` | A rule's `notify` names a target that isn't under `notifications` |
| `telegram <name> missing bot_token or chat_id` | Fill in both for that target |
| `telegram send failed: 401 ...` | Wrong bot token |
| `telegram send failed: 400 ... chat not found` | Wrong chat ID, or the bot isn't in that chat or channel |
| `unknown notification type: <type>` | Use `telegram` or `webhook` |
| `webhook notification missing url` | Add `url` to the target |
| `webhook send failed: <status> ...` or `webhook send error` | The endpoint refused it or didn't answer in 10 seconds. Those alerts are dropped |
| `<source>@<group> returned <status>: ...` or `failed to fetch <source>@<group>` | That API is down or unreachable. The other sources still count |
| `doc8643 returned <status> for <type>` | The photo site had a problem. The alert goes out as text |

## No aircraft

`fetched 0 aircraft` every poll:

- Check outbound HTTPS from the container: `docker exec planesnitch python -c "import urllib.request; print(urllib.request.urlopen('https://api.adsb.lol').status)"`.
- Make the radius bigger. A small radius over open water or empty land can honestly contain nothing.
- Use more than one source. A source that rate-limits you pauses for a while; see [rate limits](how-it-works.md#rate-limits-and-failures).

## Aircraft, but no alerts

- The aircraft must be inside the location's radius and report a position. Watchlist type doesn't change that.
- `icao_csv` matches only listed hex codes. Check the CSV loaded (`watchlist <name>: N aircraft loaded`).
- `icao_type` needs the type field, which `adsb_lol` and `ultrafeeder` don't provide. Add an enriched source.
- Squawk codes with leading zeros must be quoted in YAML (`"0000"`).
- The aircraft may be in its cooldown. Debug logs show `cooldown active for [<rule>] <hex>`.
- A rule with `locations` only checks those location keys.

## No photos in Telegram

- The aircraft didn't report a type, or doc8643.com has no photo for it (a `.notfound` marker in the cache).
- The target sets `attach_image: false`.
- The cache directory isn't writable. With `--user`, make sure that user can write the `/images` mount.
