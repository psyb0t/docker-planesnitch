---
title: "How it works"
description: "What planesnitch does each poll: grouping locations into requests, querying ADS-B sources, rate-limit backoff, deduplication, matching and cooldowns."
nav_order: 6
---

# How it works

planesnitch is one asyncio loop. Every `poll_interval` it re-reads the config, fetches aircraft, checks them against the alert rules, and sends what fired. Not 47 microservices. It watches planes and sends messages.

## Each poll

1. Re-read `config.yaml`. A changed, valid file replaces the current one; a broken one is ignored with a warning. See [Configuration](configuration.md).
2. Reload the CSV watchlists if the config changed or 24 hours have passed.
3. Fetch aircraft from every source for every location group.
4. Merge the results per aircraft.
5. Check every aircraft against every alert rule, honoring cooldowns.
6. Send the alerts, grouped per notification target.
7. Sleep `poll_interval`.

A slow source or notification target makes the poll longer; the sleep starts after the work is done.

## Fetching

The public APIs take a center point and a radius in nautical miles. planesnitch groups nearby locations into one request: a location joins an existing group when the smallest circle covering the whole group stays within 200 nm, otherwise it starts a new group. A single location's radius is capped at 200 nm too.

Each group is one request per source, with all sources in parallel. Groups go out one second apart, to be polite to the free APIs. With an `ultrafeeder` source, planesnitch reads the whole `aircraft.json` once per poll, without grouping.

| Source | Request |
| --- | --- |
| `adsb_lol` | `https://api.adsb.lol/v2/lat/{lat}/lon/{lon}/dist/{nm}` |
| `adsb_fi` | `https://opendata.adsb.fi/api/v3/lat/{lat}/lon/{lon}/dist/{nm}` |
| `airplanes_live` | `https://api.airplanes.live/v2/point/{lat}/{lon}/{nm}` |
| `adsb_one` | `https://api.adsb.one/v2/point/{lat}/{lon}/{nm}` |
| `ultrafeeder` | Your `url` |

### Rate limits and failures

- On `429 Too Many Requests`, that source pauses for the `Retry-After` time, or 10 seconds without one. Data that came with the `429` is still used.
- Any other error, a timeout (15 seconds for the APIs, 10 for ultrafeeder) or a non-JSON body counts as an empty result for that request and logs a warning. The other sources still count.
- If every source fails, the poll finds no aircraft and sends nothing.

## Deduplication

Several sources often report the same aircraft. planesnitch keys them by ICAO hex and keeps the entry with the most non-empty fields, so the enriched sources (with type name, operator and year) usually win over raw ones.

## Matching and cooldowns

For each aircraft and each rule:

1. Skip the rule if it fired for this aircraft within its `cooldown` (default 5 minutes).
2. Try the rule's watchlists in order, and for each one the rule's locations in order.
3. The first watchlist and location that match fire the rule and start its cooldown for this aircraft.

So a rule sends at most one alert per aircraft per poll, and each rule has its own cooldown. Cooldowns are kept in memory, so a restart clears them and anything in range alerts again.

Distances are great-circle distances from the location to the aircraft's reported position. See [Watchlists](watchlists.md) for what each type matches.

## Health endpoint

planesnitch listens on port `8080` and answers any request with:

```json
{
  "status": "ok",
  "last_poll": 1762684800.12,
  "last_aircraft_count": 14,
  "uptime_seconds": 3600.5
}
```

`last_poll` is the Unix time of the last finished fetch, `0` before the first one. The image's Docker healthcheck calls it every 30 seconds. It only proves the loop is alive; check `last_poll` to see that polls are still happening.
