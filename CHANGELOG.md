# Changelog

All notable changes to this project are documented here.

This project follows [Semantic Versioning](https://semver.org/).

## [1.6.0] - 2026-05-12

### Added

- **`icao_type` watchlist type** — match aircraft by their ICAO doc 8643 type
  designator (e.g. `C17`, `B738`, `RFAL`, `AJET`) against an inline list. Case
  insensitive. Distance / radius rules apply like every other watchlist type.
- **doc8643 aircraft type images** — on each alert, planesnitch fetches the
  matching photo from `doc8643.com`, caches it locally under
  `PLANESNITCH_IMAGES_DIR` (default `/images`), sends it as a Telegram photo
  attachment and embeds it in webhook payloads as a base64 `image_base64`
  field. 404s are cached as `.notfound` markers to avoid refetch.
- New `images/` directory tracked via `.gitkeep`; downloaded image files are
  gitignored.

### Changed

- Webhook payloads now always include an `image_base64` field (`null` when no
  cached image is available).
- Telegram delivery: alerts that have a cached image use `sendPhoto`. Captions
  longer than Telegram's 1024-char limit are sent as a separate text message
  first, then the photo follows without a caption. Photo-send failures fall
  back to plain `sendMessage` so the alert text is never lost.

### Security

- Aircraft type designators coming back from third-party ADS-B APIs are now
  validated against a strict `^[A-Z0-9]{1,8}$` whitelist before any filesystem
  operation, eliminating path-traversal vectors in the image cache.
- The doc8643 fetcher rejects non-`image/*` responses (e.g. Cloudflare HTML
  challenge pages returned with `200 OK`) so the cache can never be poisoned
  with garbage that later gets shipped to Telegram.

## [1.5.2] - 2026-03-10

### Changed

- Per-source rate-limit cooldowns replace the previous fixed delay between API
  group requests. A source that returns 429 only backs itself off; others keep
  polling at full speed.

## [1.5.1] - 2026-03-10

### Changed

- Increased delay between API group requests to 5 seconds to be a better
  citizen against the free ADS-B endpoints.

## [1.5.0] - 2026-03-10

### Added

- Auto-grouping of nearby configured locations into a single API query to
  reduce request volume against ADS-B providers.

## [1.4.0] - 2026-03-10

### Added

- Squawk-code identification — alerts now include the meaning and scope
  (global / regional) of recognised squawk codes (e.g. `7700`, `7600`, `7500`).

## [1.3.2] - 2026-03-08

### Fixed

- API-call bombs: tighter handling of upstream errors and retries to stop
  hammering providers on transient failures.

## [1.3.1] - 2026-03-08

### Fixed

- Misc stability fixes following the live-reload work in 1.3.0.

## [1.3.0] - 2026-03-08

### Added

- Live config reload — `config.yaml` is re-read between polls; restart no
  longer required to pick up new locations / watchlists / alerts.

## [1.2.3] - 2026-03-08

### Fixed

- Wei beta cleanups around alert dispatch.

## [1.2.2] - 2026-03-08

### Added

- `proximity` watchlist type — match any aircraft within radius / altitude
  bounds, regardless of identity.

## [1.2.1] - 2026-03-08

### Fixed

- Radius handling internally normalised to a single unit before distance
  comparisons.

## [1.2.0] - 2026-03-08

### Added

- Initial proximity work and broader watchlist plumbing.

## [1.1.1] - 2026-03-08

### Changed

- Location radius config simplified.

## [1.1.0] - 2026-03-08

### Added

- Configurable display units (aviation / metric / imperial) for Telegram and
  webhook output.

## [1.0.0] - 2026-03-08

### Added

- Initial release: ADS-B polling against adsb.lol, adsb.fi, airplanes.live,
  adsb.one; configurable locations with radius; watchlist types `squawk`,
  `icao`, `icao_csv`, `all`; Telegram and webhook notifications;
  per-aircraft per-rule cooldowns; Docker image with health check.
