# Changelog

## [1.6.0] - 2026-05-12

- `icao_type` watchlist: match aircraft by ICAO doc 8643 type designator
  (`C17`, `B738`, `RFAL`, `AJET`, ...) against an inline list.
- doc8643 aircraft photos auto-attached to alerts. Telegram alerts arrive
  as `sendPhoto`; webhook payloads embed the JPEG as base64 in
  `image_base64`. Cached on disk under `PLANESNITCH_IMAGES_DIR`
  (default `/images`), 404s remembered. Per-target `attach_image: false`
  opt-out for chats / webhooks that don't want photos; if every target
  on a rule opts out, the doc8643 fetch is skipped entirely.

## [1.5.2] - 2026-03-10

- Per-source rate-limit cooldowns instead of a fixed delay between API
  groups. A source that 429s only backs itself off; others keep polling.

## [1.5.1] - 2026-03-10

- Bumped delay between API group requests to 5s.

## [1.5.0] - 2026-03-10

- Auto-group nearby locations into a single API query to cut request
  volume against ADS-B providers.

## [1.4.0] - 2026-03-10

- Squawk-code identification: alerts now include the meaning and scope
  of recognised squawk codes (`7700`, `7600`, `7500`, ...).

## [1.3.2] - 2026-03-08

- Stopped hammering providers on transient upstream errors.

## [1.3.0] - 2026-03-08

- Live config reload: `config.yaml` is re-read between polls, no restart
  needed to pick up new locations / watchlists / alerts.

## [1.2.2] - 2026-03-08

- `proximity` watchlist type: match any aircraft within radius / altitude
  bounds, regardless of identity.

## [1.1.0] - 2026-03-08

- Configurable display units: aviation / metric / imperial.

## [1.0.0] - 2026-03-08

- Initial release. ADS-B polling against adsb.lol, adsb.fi,
  airplanes.live, adsb.one. Watchlist types `squawk`, `icao`, `icao_csv`,
  `all`. Telegram + webhook notifications. Per-aircraft per-rule
  cooldowns. Docker image with health check.
