---
title: "Security"
description: "What planesnitch sends where, what it stores, which secrets the config holds, and what to lock down before running it: outbound calls, health port, container user."
nav_order: 8
---

# Security

planesnitch is a poll-and-push loop. It doesn't accept commands from anywhere, but it does send your locations and alert data to third parties on every poll and every alert. Know where it all goes.

## What leaves your machine

| To | What | When |
| --- | --- | --- |
| Each configured public ADS-B API | The center point and radius of each location group | Every poll |
| Your `ultrafeeder` URL | A plain GET | Every poll |
| `api.telegram.org` | Alert text with aircraft position, callsign, registration, the location name and distance; the photo when attached; your bot token in the URL | Every alert to a Telegram target |
| Your webhook URLs | The full [webhook payload](notifications.md#webhook) and your configured headers | Every poll with alerts for that target |
| `doc8643.com` | The aircraft type designator | First time a type needs a photo |

Location groups merge nearby locations into one circle, so a request reveals roughly where you watch, not each exact point. Run your own receiver and use only the `ultrafeeder` source if your locations shouldn't reach a public API at all.

Point `notify` only at Telegram chats and webhook URLs you run or trust. A webhook gets every matched aircraft and the name of the location it was near.

## Secrets

`config.yaml` holds your Telegram bot token and any webhook auth headers in plaintext. Keep it out of Git, `chmod 600` it, and mount it read-only. planesnitch doesn't log the token or the headers. At `LOG_LEVEL=DEBUG` it logs the whole loaded config, which includes them, so keep debug logs private.

## What it stores

Only the aircraft-type photo cache in `/images`: JPEGs named by type designator, plus `.notfound` markers. Type designators from the APIs must be 1 to 8 letters or digits before they're used in a file name or URL, so a bad API response can't write outside the cache. Downloads that aren't images are refused.

## Inbound

The only listener is the health endpoint on port `8080`. It needs no authentication and returns the last poll time, the aircraft count and the uptime. It doesn't show the config or your locations. It's reachable only if you publish the port; keep it on loopback if you do.

## Container

The image runs as root inside the container and doesn't drop capabilities. Nothing in it needs root, so you can run it as any user that can read the config and CSVs and write `/images`:

```bash
docker run -d --name planesnitch \
  --user 1000:1000 \
  --read-only \
  --cap-drop=ALL \
  --security-opt no-new-privileges:true \
  -v ./config.yaml:/app/config.yaml:ro \
  -v ./csv:/csv:ro \
  -v ./images:/images \
  psyb0t/planesnitch
```
