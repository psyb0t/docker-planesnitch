# Changelog

## [1.8.6] - 2026-08-01

CI plumbing only. No code in this repo changed — every commit in this release
touches `.github/workflows/`.

- **Pipeline split.** Building and publishing stay in `pipeline.yml`;
  everything that leaves the host now lives beside it in
  `mirror-and-archive.yml`.
- **Codeberg mirror.** The repo is mirrored to Codeberg as well as GitLab.
- **Archiving.** It is archived to the Wayback Machine, Software Heritage and
  archive.org.
- **Mirror issues pulled back.** Issues opened on either mirror are copied back
  to GitHub every six hours, and closed here when the original closes.
- **Mirror pull requests disabled.** The mirrors are force-pushed from GitHub,
  so anything merged there would be destroyed by the next sync. Issues and
  forking stay enabled.

## [1.8.5] - 2026-07-27

- **Codex install command in README.** The Codex subsection of "Agent
  integrations" was missing the actual install step after the marketplace
  add — it now includes `codex plugin add planesnitch@psyb0t`.
- **Invocation forms clarified.** The skill invokes as
  `$planesnitch:planesnitch` when installed via the marketplace, and as
  plain `$planesnitch` when Codex picks it up automatically from a repo's
  own `.agents/skills/` directory — these are two different paths and the
  README now documents both.

## [1.8.4] - 2026-07-27

- **Claude Code + Codex plugin manifests.** Added
  `.agents/.claude-plugin/plugin.json` and `.agents/.codex-plugin/plugin.json`
  so the existing `.agents/skills/planesnitch/` skill installs natively as a
  plugin in both clients, rooted at `.agents/` with zero extra config.
- **README "Agent integrations" section.** Documents the
  `claude plugin marketplace add` / `claude plugin install` and
  `codex plugin marketplace add` commands, plus the OpenClaw ClawHub skill
  install line, with a matching Table of Contents entry.

## [1.8.3] - 2026-07-27

- **CI status badge.** Added a GitHub Actions CI status badge to the README.

## [1.8.2] - 2026-07-27

- **README badges.** Added self-hosted version and license badges (rendered as
  SVGs on the `badges` branch by the `create-badges` CI job, no third-party
  render service) plus a Docker Hub pulls badge. A `badges` job was wired into
  `pipeline.yml`.

## [1.8.1] - 2026-07-26

- **Agent skill docs hardened.** Extended the Security & safety section and
  the notifications config docs in `.agents/skills/planesnitch/` with
  explicit warnings that alert delivery (Telegram + webhook) transmits
  location coordinates and aircraft tracking data off-host to whatever
  bot/chat or webhook URL you configure. No behavior change — docs only.

## [1.8.0] - 2026-07-25

- **Agent skill + ClawHub publish.** Added `.agents/skills/planesnitch/`
  (SKILL.md + references/setup.md) documenting the config schema, watchlist
  filters, and Telegram/webhook alert sinks. The pipeline now publishes the
  skill to ClawHub on tag pushes.

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
