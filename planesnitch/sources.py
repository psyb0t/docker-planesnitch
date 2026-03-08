"""ADS-B data source fetching and deduplication."""

import asyncio
import json
import logging
from typing import Any

import aiohttp

from .config import NM_TO_KM, resolve_distance_km

log = logging.getLogger("planesnitch")

API_SOURCES: dict[str, dict[str, str]] = {
    "adsb_lol": {
        "url": "https://api.adsb.lol/v2/lat/{lat}/lon/{lon}/dist/{dist}",
        "key": "ac",
    },
    "adsb_fi": {
        "url": "https://opendata.adsb.fi/api/v3/lat/{lat}/lon/{lon}/dist/{dist}",
        "key": "ac",
    },
    "airplanes_live": {
        "url": "https://api.airplanes.live/v2/point/{lat}/{lon}/{dist}",
        "key": "ac",
    },
    "adsb_one": {
        "url": "https://api.adsb.one/v2/point/{lat}/{lon}/{dist}",
        "key": "ac",
    },
}


async def _fetch_api_source(
    name: str,
    url: str,
    ac_key: str,
    session: aiohttp.ClientSession,
) -> list[dict[str, Any]]:
    log.debug("fetching %s: %s", name, url)
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
            log.debug("%s response status: %s", name, resp.status)
            body = await resp.text()
            if resp.status not in (200, 429):
                log.warning(
                    "%s returned %d: %s",
                    name,
                    resp.status,
                    body[:200],
                )
                return []
            try:
                data = json.loads(body)
            except (json.JSONDecodeError, ValueError):
                log.warning(
                    "%s returned non-JSON (%d): %s",
                    name,
                    resp.status,
                    body[:200],
                )
                return []
            if resp.status == 429:
                log.debug("%s rate-limited (429)", name)
            ac_list = data.get(ac_key, [])
            log.debug("%s returned %d aircraft", name, len(ac_list))
            for ac in ac_list:
                log.debug(
                    "  %s ac: hex=%s flight=%s alt=%s lat=%s lon=%s squawk=%s",
                    name,
                    ac.get("hex"),
                    (ac.get("flight") or "").strip(),
                    ac.get("alt_baro"),
                    ac.get("lat"),
                    ac.get("lon"),
                    ac.get("squawk"),
                )
            return ac_list
    except Exception:
        log.warning("failed to fetch %s", name, exc_info=True)
        return []


async def _fetch_ultrafeeder(
    url: str, session: aiohttp.ClientSession
) -> list[dict[str, Any]]:
    log.debug("fetching ultrafeeder: %s", url)
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            log.debug("ultrafeeder response status: %s", resp.status)
            if resp.status != 200:
                body = await resp.text()
                log.warning(
                    "ultrafeeder returned %d: %s",
                    resp.status,
                    body[:200],
                )
                return []
            data = await resp.json(content_type=None)
            ac_list = data.get("aircraft", [])
            log.debug("ultrafeeder returned %d aircraft", len(ac_list))
            for ac in ac_list:
                log.debug(
                    "  ultrafeeder ac: hex=%s flight=%s alt=%s lat=%s lon=%s",
                    ac.get("hex"),
                    (ac.get("flight") or "").strip(),
                    ac.get("alt_baro"),
                    ac.get("lat"),
                    ac.get("lon"),
                )
            return ac_list
    except Exception:
        log.warning("failed to fetch ultrafeeder at %s", url, exc_info=True)
        return []


def _dedup_aircraft(
    seen: dict[str, dict[str, Any]], aircraft: list[dict[str, Any]]
) -> None:
    for ac in aircraft:
        hex_code = ac.get("hex", "").strip().lower()
        if not hex_code:
            continue
        existing = seen.get(hex_code)
        if not existing:
            seen[hex_code] = ac
            continue
        old_count = sum(1 for v in existing.values() if v)
        new_count = sum(1 for v in ac.values() if v)
        if new_count > old_count:
            seen[hex_code] = ac


async def fetch_aircraft(
    sources: list[dict[str, Any]],
    locations: dict[str, dict[str, Any]],
    session: aiohttp.ClientSession,
) -> list[dict[str, Any]]:
    tasks: list[tuple[str, asyncio.Task[list[dict[str, Any]]]]] = []

    for source in sources:
        src_type = source.get("type", "")

        if src_type == "ultrafeeder":
            log.debug("fetching from ultrafeeder")
            task = asyncio.create_task(_fetch_ultrafeeder(source["url"], session))
            tasks.append((src_type, task))
            continue

        api_def = API_SOURCES.get(src_type)
        if not api_def:
            log.debug("skipping unknown source type: %s", src_type)
            continue

        for loc_name, loc in locations.items():
            dist_km = resolve_distance_km(loc, "radius", default=150) or 150
            dist_nm = max(1, min(int(dist_km / NM_TO_KM), 250))
            label = f"{src_type}@{loc_name}"
            log.debug("fetching from %s", label)
            url = api_def["url"].format(
                lat=loc["lat"],
                lon=loc["lon"],
                dist=dist_nm,
            )
            task = asyncio.create_task(
                _fetch_api_source(label, url, api_def["key"], session)
            )
            tasks.append((label, task))

    seen: dict[str, dict[str, Any]] = {}
    for name, task in tasks:
        aircraft = await task
        log.debug("%s returned %d aircraft", name, len(aircraft))
        _dedup_aircraft(seen, aircraft)

    log.debug("total unique aircraft after dedup: %d", len(seen))
    return list(seen.values())
