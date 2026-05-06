"""planesnitch — aircraft watchlist alerter."""

import argparse
import asyncio
import json
import logging
import os
import time
from typing import Any
from urllib.parse import urlsplit

import aiohttp

from .alerts import check_alerts
from .config import load_config
from .notify import (TG_MAX_LEN, TG_SEPARATOR, cluster_messages,
                     format_message, format_webhook_payload, send_telegram,
                     send_webhook)
from .sources import fetch_aircraft
from .watchlists import load_watchlists

log = logging.getLogger("planesnitch")

HEALTH_PORT = 8080
MAX_UI_ALERTS = 100

_last_poll: float = 0
_last_successful_poll: float = 0
_last_aircraft_count: int = 0
_last_triggered_count: int = 0
_last_error: str = ""
_poll_interval_seconds: int = 15
_recent_alerts: list[dict[str, Any]] = []

_UI_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>planesnitch</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #0f1720;
      --panel: #17212b;
      --panel-2: #1f2d3a;
      --text: #ecf2f8;
      --muted: #95a6b8;
      --accent: #ffb44c;
      --danger: #ff6b6b;
      --ok: #4dd4ac;
      --border: rgba(255, 255, 255, 0.08);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "SFMono-Regular", "Menlo", "Consolas", monospace;
      background:
        radial-gradient(circle at top, rgba(255, 180, 76, 0.16), transparent 30%),
        linear-gradient(180deg, #0b1219, var(--bg));
      color: var(--text);
    }
    main {
      max-width: 1100px;
      margin: 0 auto;
      padding: 24px;
    }
    h1, h2, p { margin: 0; }
    .hero, .panel {
      background: rgba(23, 33, 43, 0.9);
      border: 1px solid var(--border);
      border-radius: 18px;
      backdrop-filter: blur(10px);
      box-shadow: 0 18px 40px rgba(0, 0, 0, 0.2);
    }
    .hero {
      padding: 24px;
      margin-bottom: 20px;
    }
    .hero p {
      color: var(--muted);
      margin-top: 8px;
    }
    .grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 12px;
      margin: 20px 0;
    }
    .stat {
      background: var(--panel-2);
      border-radius: 14px;
      padding: 14px;
      border: 1px solid var(--border);
    }
    .label {
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      margin-bottom: 6px;
    }
    .value {
      font-size: 24px;
      font-weight: 700;
    }
    .panels {
      display: grid;
      grid-template-columns: 1.1fr 1.9fr;
      gap: 20px;
    }
    .panel {
      padding: 18px;
    }
    .meta {
      display: grid;
      gap: 10px;
      margin-top: 14px;
    }
    .meta div {
      display: flex;
      justify-content: space-between;
      gap: 16px;
      color: var(--muted);
      border-bottom: 1px solid var(--border);
      padding-bottom: 10px;
    }
    .meta strong {
      color: var(--text);
      font-weight: 600;
    }
    .status {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 8px 12px;
      border-radius: 999px;
      background: rgba(255, 255, 255, 0.06);
      margin-top: 14px;
    }
    .status-dot {
      width: 10px;
      height: 10px;
      border-radius: 50%;
      background: var(--muted);
    }
    .status-ok .status-dot { background: var(--ok); }
    .status-degraded .status-dot { background: var(--danger); }
    .status-starting .status-dot { background: var(--accent); }
    .alerts {
      display: grid;
      gap: 12px;
      margin-top: 14px;
    }
    .alert {
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 14px;
      background: rgba(255, 255, 255, 0.03);
    }
    .alert-top {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      flex-wrap: wrap;
      margin-bottom: 8px;
    }
    .alert small, .empty, .error {
      color: var(--muted);
    }
    .pill {
      display: inline-block;
      padding: 4px 8px;
      border-radius: 999px;
      background: rgba(255, 180, 76, 0.14);
      color: var(--accent);
      font-size: 12px;
      margin-right: 8px;
    }
    code {
      color: var(--text);
      background: rgba(255, 255, 255, 0.06);
      padding: 2px 6px;
      border-radius: 6px;
    }
    @media (max-width: 860px) {
      .panels { grid-template-columns: 1fr; }
      main { padding: 16px; }
    }
  </style>
</head>
<body>
  <main>
    <section class="hero">
      <h1>planesnitch control room</h1>
      <p>Still snitching to Telegram and webhooks. Now it also rats everything out in your browser.</p>
      <div class="grid" id="stats"></div>
    </section>
    <section class="panels">
      <div class="panel">
        <h2>Service State</h2>
        <div id="status" class="status status-starting"><span class="status-dot"></span><span>starting</span></div>
        <div class="meta" id="meta"></div>
        <p class="error" id="error"></p>
      </div>
      <div class="panel">
        <h2>Recent Alerts</h2>
        <div class="alerts" id="alerts"></div>
      </div>
    </section>
  </main>
  <script>
    const statsEl = document.getElementById("stats");
    const metaEl = document.getElementById("meta");
    const alertsEl = document.getElementById("alerts");
    const errorEl = document.getElementById("error");
    const statusEl = document.getElementById("status");

    function fmtTime(ts) {
      if (!ts) return "never";
      return new Date(ts * 1000).toLocaleString();
    }

    function fmtAgo(ts) {
      if (!ts) return "never";
      const diff = Math.max(0, Math.round(Date.now() / 1000 - ts));
      if (diff < 60) return `${diff}s ago`;
      if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
      return `${Math.floor(diff / 3600)}h ago`;
    }

    function stat(label, value) {
      return `<div class="stat"><div class="label">${label}</div><div class="value">${value}</div></div>`;
    }

    function metaRow(label, value) {
      return `<div><span>${label}</span><strong>${value}</strong></div>`;
    }

    function renderAlert(alert) {
      const flight = alert.flight || "no callsign";
      const hex = alert.hex || "unknown";
      const reason = alert.reason || "unknown";
      return `
        <article class="alert">
          <div class="alert-top">
            <strong>${alert.alert_name}</strong>
            <small>${fmtTime(alert.timestamp)}</small>
          </div>
          <div><span class="pill">${alert.location_name}</span><span class="pill">${reason}</span></div>
          <p><code>${hex}</code> ${flight}</p>
          <small>${alert.notification_targets.join(", ") || "ui only"}</small>
        </article>
      `;
    }

    async function refresh() {
      try {
        const response = await fetch("/api/state", { cache: "no-store" });
        const state = await response.json();
        statusEl.className = `status status-${state.status}`;
        statusEl.lastElementChild.textContent = state.status;
        statsEl.innerHTML = [
          stat("Aircraft", state.last_aircraft_count),
          stat("Alerts", state.last_triggered_count),
          stat("Poll Every", `${state.poll_interval_seconds}s`),
          stat("Uptime", `${Math.round(state.uptime_seconds)}s`)
        ].join("");
        metaEl.innerHTML = [
          metaRow("Last poll", `${fmtTime(state.last_poll)} (${fmtAgo(state.last_poll)})`),
          metaRow("Last success", `${fmtTime(state.last_successful_poll)} (${fmtAgo(state.last_successful_poll)})`),
          metaRow("Recent alerts kept", state.recent_alerts.length),
          metaRow("Source count", state.source_count),
          metaRow("Location count", state.location_count),
          metaRow("Notification count", state.notification_count)
        ].join("");
        errorEl.textContent = state.last_error ? `Last error: ${state.last_error}` : "";
        alertsEl.innerHTML = state.recent_alerts.length
          ? state.recent_alerts.map(renderAlert).join("")
          : '<p class="empty">No alerts yet. Either the sky is boring or your config has standards.</p>';
      } catch (error) {
        errorEl.textContent = `Dashboard refresh failed: ${error}`;
      }
    }

    refresh();
    setInterval(refresh, 5000);
  </script>
</body>
</html>
"""


def _health_snapshot() -> tuple[int, dict[str, Any]]:
    now = time.time()
    stale_seconds = max(60.0, _poll_interval_seconds * 3.0)

    status = "starting"
    status_code = 200

    if _last_poll == 0:
        status = "starting"
    elif _last_successful_poll == 0 or now - _last_successful_poll > stale_seconds:
        status = "degraded"
        status_code = 503
    else:
        status = "ok"

    return status_code, {
        "status": status,
        "last_poll": _last_poll,
        "last_successful_poll": _last_successful_poll,
        "last_aircraft_count": _last_aircraft_count,
        "last_triggered_count": _last_triggered_count,
        "last_error": _last_error or None,
        "poll_interval_seconds": _poll_interval_seconds,
        "recent_alerts": _recent_alerts,
        "source_count": _last_config_snapshot.get("source_count", 0),
        "location_count": _last_config_snapshot.get("location_count", 0),
        "notification_count": _last_config_snapshot.get("notification_count", 0),
        "uptime_seconds": round(now - _start_time, 1),
    }


_last_config_snapshot: dict[str, int] = {
    "source_count": 0,
    "location_count": 0,
    "notification_count": 0,
}


def _record_alert(
    aircraft: dict[str, Any],
    rule: dict[str, Any],
    match_info: dict[str, Any],
    location_name: str,
) -> None:
    _recent_alerts.insert(
        0,
        {
            "timestamp": time.time(),
            "alert_name": rule["name"],
            "location_name": location_name,
            "hex": aircraft.get("hex"),
            "flight": (aircraft.get("flight") or "").strip(),
            "reason": match_info.get("reason"),
            "notification_targets": list(rule.get("notify", [])),
        },
    )
    del _recent_alerts[MAX_UI_ALERTS:]


def _http_response(
    status_code: int,
    reason: str,
    content_type: str,
    body: str,
) -> bytes:
    encoded = body.encode()
    response = (
        f"HTTP/1.1 {status_code} {reason}\r\n"
        f"Content-Type: {content_type}; charset=utf-8\r\n"
        f"Content-Length: {len(encoded)}\r\n"
        f"Cache-Control: no-store\r\n"
        f"\r\n"
    ).encode()
    return response + encoded


async def _http_handler(
    reader: asyncio.StreamReader, writer: asyncio.StreamWriter
) -> None:
    try:
        request = await reader.read(4096)
        request_line = request.decode(errors="ignore").splitlines()[0] if request else ""
        parts = request_line.split()
        path = urlsplit(parts[1]).path if len(parts) >= 2 else "/"

        if path == "/health":
            status_code, payload = _health_snapshot()
            reason = "OK" if status_code == 200 else "Service Unavailable"
            writer.write(
                _http_response(status_code, reason, "application/json", json.dumps(payload))
            )
        elif path == "/api/state":
            _, payload = _health_snapshot()
            writer.write(_http_response(200, "OK", "application/json", json.dumps(payload)))
        elif path == "/":
            writer.write(_http_response(200, "OK", "text/html", _UI_HTML))
        else:
            writer.write(
                _http_response(
                    404,
                    "Not Found",
                    "application/json",
                    json.dumps({"error": "not found"}),
                )
            )
        await writer.drain()
    finally:
        writer.close()


_start_time: float = time.time()


async def run(config_path: str, config: dict[str, Any]) -> None:
    global _last_aircraft_count, _last_config_snapshot, _last_error
    global _last_poll, _last_successful_poll, _last_triggered_count
    global _poll_interval_seconds
    cooldowns: dict[tuple[str, str], float] = {}

    csv_refresh_interval = 86400
    last_csv_refresh = 0.0

    server = await asyncio.start_server(_http_handler, "0.0.0.0", HEALTH_PORT)
    log.info("health endpoint listening on :%d", HEALTH_PORT)

    async with server:
        async with aiohttp.ClientSession() as session:
            watchlists: dict[str, dict[str, Any]] = {}

            while True:
                now = time.time()

                try:
                    new_config = load_config(config_path)
                    if new_config != config:
                        log.info("config reloaded (changed)")
                        config = new_config
                        last_csv_refresh = 0.0
                except Exception:
                    log.warning("config reload failed, keeping current", exc_info=True)

                poll_interval = config.get("poll_interval", 15)
                _poll_interval_seconds = poll_interval
                locations = config["locations"]
                notifications = config.get("notifications", {})
                display_units = config.get("display_units", "aviation")
                _last_config_snapshot = {
                    "source_count": len(config.get("sources", [])),
                    "location_count": len(locations),
                    "notification_count": len(notifications),
                }

                try:
                    if now - last_csv_refresh > csv_refresh_interval:
                        log.debug(
                            "refreshing watchlist CSVs (last refresh %.0fs ago)",
                            now - last_csv_refresh,
                        )
                        watchlists = load_watchlists(config["watchlists"])
                        last_csv_refresh = now

                    log.debug("starting poll cycle")
                    aircraft_list = await fetch_aircraft(
                        config["sources"], locations, session
                    )
                    _last_poll = time.time()
                    _last_successful_poll = _last_poll
                    _last_aircraft_count = len(aircraft_list)
                    _last_error = ""
                    log.info("fetched %d aircraft", len(aircraft_list))

                    triggered = check_alerts(
                        aircraft_list,
                        config["alerts"],
                        watchlists,
                        locations,
                        cooldowns,
                    )
                    _last_triggered_count = len(triggered)

                    tg_queues: dict[str, list[str]] = {}
                    wh_queues: dict[str, list[dict[str, Any]]] = {}

                    for ac, rule, match_info, loc_key, loc in triggered:
                        display_name = loc.get("name", loc_key)
                        _record_alert(ac, rule, match_info, display_name)
                        log.info(
                            "ALERT [%s] [%s] %s %s",
                            rule["name"],
                            display_name,
                            ac.get("hex"),
                            (ac.get("flight") or "").strip(),
                        )

                        for notif_name in rule.get("notify", []):
                            notif = notifications.get(notif_name)
                            if not notif:
                                log.warning("notification target %s not found", notif_name)
                                continue

                            if notif.get("type") == "telegram":
                                msg = format_message(
                                    ac,
                                    rule["name"],
                                    match_info,
                                    loc,
                                    display_name,
                                    display_units,
                                )
                                tg_queues.setdefault(notif_name, []).append(msg)
                                continue

                            if notif.get("type") == "webhook":
                                payload = format_webhook_payload(
                                    ac,
                                    rule["name"],
                                    match_info,
                                    loc,
                                    display_name,
                                    display_units,
                                )
                                wh_queues.setdefault(notif_name, []).append(payload)
                                continue

                            log.warning("unknown notification type: %s", notif.get("type"))

                    for notif_name, messages in tg_queues.items():
                        notif = notifications[notif_name]
                        token = notif.get("bot_token", "")
                        chat_id = notif.get("chat_id", "")
                        batches = cluster_messages(messages, TG_MAX_LEN, TG_SEPARATOR)
                        log.debug(
                            "telegram %s: %d alerts clustered into %d messages",
                            notif_name,
                            len(messages),
                            len(batches),
                        )
                        for batch in batches:
                            await send_telegram(token, chat_id, batch, session)

                    for notif_name, payloads in wh_queues.items():
                        notif = notifications[notif_name]
                        log.debug(
                            "webhook %s: sending %d alerts",
                            notif_name,
                            len(payloads),
                        )
                        await send_webhook(notif, payloads, session)
                except Exception as exc:
                    _last_poll = time.time()
                    _last_triggered_count = 0
                    _last_error = str(exc)
                    log.exception("poll cycle failed")

                log.debug("sleeping %ds until next poll", poll_interval)
                await asyncio.sleep(poll_interval)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="planesnitch - aircraft watchlist alerter"
    )
    parser.add_argument(
        "--config",
        default=os.environ.get("PLANESNITCH_CONFIG", "config.yaml"),
        help="path to config file",
    )
    args = parser.parse_args()

    level = getattr(logging, os.environ.get("LOG_LEVEL", "INFO").upper(), logging.INFO)

    logging.basicConfig(
        level=logging.WARNING,
        format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    log.setLevel(level)

    log.debug("log level set to %s", logging.getLevelName(level))

    config = load_config(args.config)
    log.info("planesnitch starting")

    try:
        asyncio.run(run(args.config, config))
    except KeyboardInterrupt:
        log.info("shutting down")


if __name__ == "__main__":
    main()
