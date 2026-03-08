"""planesnitch — aircraft watchlist alerter."""

import argparse
import asyncio
import json
import logging
import os
import time
from typing import Any

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

_last_poll: float = 0
_last_aircraft_count: int = 0


async def _health_handler(
    reader: asyncio.StreamReader, writer: asyncio.StreamWriter
) -> None:
    try:
        await reader.read(4096)
        body = json.dumps(
            {
                "status": "ok",
                "last_poll": _last_poll,
                "last_aircraft_count": _last_aircraft_count,
                "uptime_seconds": round(time.time() - _start_time, 1),
            }
        )
        response = (
            f"HTTP/1.1 200 OK\r\n"
            f"Content-Type: application/json\r\n"
            f"Content-Length: {len(body)}\r\n"
            f"\r\n{body}"
        )
        writer.write(response.encode())
        await writer.drain()
    finally:
        writer.close()


_start_time: float = time.time()


async def run(config_path: str, config: dict[str, Any]) -> None:
    global _last_poll, _last_aircraft_count
    cooldowns: dict[tuple[str, str], float] = {}

    csv_refresh_interval = 86400
    last_csv_refresh = 0.0

    await asyncio.start_server(_health_handler, "0.0.0.0", HEALTH_PORT)
    log.info("health endpoint listening on :%d", HEALTH_PORT)

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
            locations = config["locations"]
            notifications = config.get("notifications", {})
            display_units = config.get("display_units", "aviation")

            if now - last_csv_refresh > csv_refresh_interval:
                log.debug(
                    "refreshing watchlist CSVs (last refresh %.0fs ago)",
                    now - last_csv_refresh,
                )
                watchlists = load_watchlists(config["watchlists"])
                last_csv_refresh = now

            log.debug("starting poll cycle")
            aircraft_list = await fetch_aircraft(config["sources"], locations, session)
            _last_poll = time.time()
            _last_aircraft_count = len(aircraft_list)
            log.info("fetched %d aircraft", len(aircraft_list))

            triggered = check_alerts(
                aircraft_list,
                config["alerts"],
                watchlists,
                locations,
                cooldowns,
            )

            tg_queues: dict[str, list[str]] = {}
            wh_queues: dict[str, list[dict[str, Any]]] = {}

            for ac, rule, match_info, loc_key, loc in triggered:
                display_name = loc.get("name", loc_key)
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
                if not token or not chat_id:
                    log.warning(
                        "telegram %s missing bot_token or chat_id",
                        notif_name,
                    )
                    continue
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
