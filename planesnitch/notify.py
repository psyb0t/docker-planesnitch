"""Notification formatting and sending."""

import logging
from typing import Any

import aiohttp

from .config import (
    convert_altitude,
    convert_distance,
    convert_speed,
    format_altitude,
    format_distance,
    format_speed,
    squawk_meaning,
    unit_labels,
)
from .geo import get_distance_km

log = logging.getLogger("planesnitch")

TG_MAX_LEN = 4096
TG_SEPARATOR = "\n\n"


def cluster_messages(messages: list[str], max_len: int, separator: str) -> list[str]:
    if not messages:
        return []

    batches: list[str] = []
    current = messages[0]

    for msg in messages[1:]:
        candidate = current + separator + msg
        if len(candidate) <= max_len:
            current = candidate
            continue
        batches.append(current)
        current = msg

    batches.append(current)
    return batches


def format_message(
    aircraft: dict[str, Any],
    alert_name: str,
    match_info: dict[str, Any],
    location: dict[str, Any],
    location_name: str,
    display_units: str = "aviation",
) -> str:
    hex_code = aircraft.get("hex", "unknown")
    flight = (aircraft.get("flight") or "").strip()
    reg = aircraft.get("r", "")
    ac_type = aircraft.get("t", "")
    desc = aircraft.get("desc", "")
    owner = aircraft.get("ownOp", "")
    year = aircraft.get("year", "")
    alt = aircraft.get("alt_baro")
    lat = aircraft.get("lat")
    lon = aircraft.get("lon")
    squawk = aircraft.get("squawk", "")
    gs = aircraft.get("gs")

    reason = match_info.get("reason", "")

    lines: list[str] = []

    lines.append(f"\U0001f514 {alert_name}")

    if reason == "squawk":
        sq = match_info.get("squawk", "")
        sq_info = squawk_meaning(sq)
        if sq_info:
            lines.append(
                f"\U0001f6a8 squawk {sq}" f" ({sq_info['meaning']}, {sq_info['scope']})"
            )
        else:
            lines.append(f"\U0001f6a8 squawk {sq}")

    if flight:
        lines.append(f"\u2708\ufe0f {flight}")

    type_parts = []
    if desc:
        type_parts.append(desc)
    elif ac_type:
        type_parts.append(ac_type)
    if reg:
        type_parts.append(reg)
    if year:
        type_parts.append(year)
    if type_parts:
        lines.append(f"\U0001f6e9\ufe0f {' | '.join(type_parts)}")

    if owner:
        lines.append(f"\U0001f4bc {owner}")

    csv_info = match_info.get("info")
    if csv_info:
        operator = csv_info.get("Operator", "")
        category = csv_info.get("Category", "")
        parts = [p for p in (operator, category) if p]
        if parts:
            lines.append(f"\U0001f3f7\ufe0f {' \u2014 '.join(parts)}")

    pos_parts = []
    if lat is not None and lon is not None:
        pos_parts.append(f"{lat:.4f}, {lon:.4f}")
    if alt is not None and not isinstance(alt, str):
        pos_parts.append(format_altitude(alt, display_units))
    if pos_parts:
        lines.append(f"\U0001f4cd {' | '.join(pos_parts)}")

    dist = get_distance_km(aircraft, location)
    if dist is not None:
        lines.append(
            f"\U0001f4cf {format_distance(dist, display_units)} from {location_name}"
        )

    if gs:
        lines.append(f"\U0001f4a8 {format_speed(gs, display_units)}")

    if squawk and reason != "squawk":
        sq_info = squawk_meaning(squawk)
        if sq_info:
            lines.append(
                f"\U0001f4e1 squawk {squawk}"
                f" ({sq_info['meaning']}, {sq_info['scope']})"
            )
        else:
            lines.append(f"\U0001f4e1 squawk {squawk}")

    lines.append(f"\U0001f5fa\ufe0f https://globe.adsb.fi/?icao={hex_code}")

    return "\n".join(lines)


def format_webhook_payload(
    aircraft: dict[str, Any],
    alert_name: str,
    match_info: dict[str, Any],
    location: dict[str, Any],
    location_name: str,
    display_units: str = "aviation",
) -> dict[str, Any]:
    dist = get_distance_km(aircraft, location)
    alt = aircraft.get("alt_baro")
    gs = aircraft.get("gs")
    labels = unit_labels(display_units)
    return {
        "alert": alert_name,
        "location": location_name,
        "match": match_info,
        "units": labels,
        "aircraft": {
            "hex": aircraft.get("hex"),
            "flight": (aircraft.get("flight") or "").strip(),
            "registration": aircraft.get("r"),
            "type": aircraft.get("t"),
            "description": aircraft.get("desc"),
            "owner_operator": aircraft.get("ownOp"),
            "year": aircraft.get("year"),
            "squawk": aircraft.get("squawk"),
            "squawk_meaning": squawk_meaning(aircraft.get("squawk")),
            "emergency": aircraft.get("emergency"),
            "altitude": (
                convert_altitude(alt, display_units)
                if alt is not None and not isinstance(alt, str)
                else None
            ),
            "lat": aircraft.get("lat"),
            "lon": aircraft.get("lon"),
            "speed": convert_speed(gs, display_units) if gs is not None else None,
            "track": aircraft.get("track"),
            "distance": convert_distance(dist, display_units) if dist is not None else None,
        },
    }


async def send_telegram(
    token: str,
    chat_id: str,
    text: str,
    session: aiohttp.ClientSession,
) -> None:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    log.debug("telegram payload: chat_id=%s msg_len=%d", chat_id, len(text))
    try:
        async with session.post(
            url, json=payload, timeout=aiohttp.ClientTimeout(total=10)
        ) as resp:
            log.debug("telegram response: %s", resp.status)
            if resp.status != 200:
                body = await resp.text()
                log.warning("telegram send failed: %s %s", resp.status, body)
    except Exception:
        log.warning("telegram send error", exc_info=True)


async def send_webhook(
    notif_config: dict[str, Any],
    payloads: list[dict[str, Any]],
    session: aiohttp.ClientSession,
) -> None:
    wh_url = notif_config.get("url", "")
    if not wh_url:
        log.warning("webhook notification missing url")
        return
    headers = dict(notif_config.get("headers", {}))
    headers.setdefault("Content-Type", "application/json")
    log.debug("webhook url=%s alerts=%d", wh_url, len(payloads))
    try:
        async with session.post(
            wh_url,
            json=payloads,
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=10),
        ) as resp:
            log.debug("webhook response: %s", resp.status)
            if resp.status >= 400:
                body = await resp.text()
                log.warning("webhook send failed: %s %s", resp.status, body)
    except Exception:
        log.warning("webhook send error", exc_info=True)
