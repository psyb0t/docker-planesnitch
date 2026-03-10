"""ADS-B data source fetching and deduplication."""

import asyncio
import json
import logging
import time
from typing import Any

import aiohttp

from .config import NM_TO_KM, resolve_distance_km
from .geo import bounding_circle

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

MAX_GROUP_NM = 200
DEFAULT_RATE_LIMIT_BACKOFF = 10.0

# per-source cooldown: src_type -> earliest next request time
_source_cooldowns: dict[str, float] = {}


def _source_ready(src_type: str) -> bool:
    return time.time() >= _source_cooldowns.get(src_type, 0)


def _set_source_cooldown(src_type: str, retry_after: float | None) -> None:
    backoff = retry_after if retry_after else DEFAULT_RATE_LIMIT_BACKOFF
    until = time.time() + backoff
    _source_cooldowns[src_type] = until
    log.debug("%s: rate-limited, cooling down %.0fs", src_type, backoff)


async def _fetch_api_source(
    name: str,
    url: str,
    ac_key: str,
    session: aiohttp.ClientSession,
) -> list[dict[str, Any]] | None:
    """Fetch aircraft from an API source.

    Returns None on HTTP 400 (rejected — dist too large).
    Returns [] on other errors.
    Sets per-source cooldown on 429.
    """
    src_type = name.split("@")[0]
    log.debug("fetching %s: %s", name, url)
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
            log.debug("%s response status: %s", name, resp.status)
            body = await resp.text()

            if resp.status == 400:
                log.debug("%s rejected request (400): %s", name, body[:200])
                return None

            if resp.status == 429:
                retry_after = resp.headers.get("Retry-After")
                ra_val = None
                if retry_after:
                    try:
                        ra_val = float(retry_after)
                    except ValueError:
                        pass
                _set_source_cooldown(src_type, ra_val)

                # some APIs send valid JSON on 429 (adsb.fi)
                try:
                    data = json.loads(body)
                    ac_list = data.get(ac_key, [])
                    if ac_list:
                        log.debug(
                            "%s rate-limited (429) but got %d aircraft",
                            name,
                            len(ac_list),
                        )
                        return ac_list
                except (json.JSONDecodeError, ValueError):
                    pass
                log.debug("%s rate-limited (429), no data", name)
                return []

            if resp.status != 200:
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


def _auto_group_locations(
    locations: dict[str, dict[str, Any]],
) -> list[list[dict[str, Any]]]:
    """Cluster locations into groups that fit within MAX_GROUP_NM.

    Each entry gets radius_km and _key added.
    Returns list of groups, each group is a list of loc dicts.
    """
    groups: list[list[dict[str, Any]]] = []

    for key, loc in locations.items():
        r_km = resolve_distance_km(loc, "radius", default=150) or 150
        entry = {**loc, "radius_km": r_km, "_key": key}

        placed = False
        for group in groups:
            test = group + [entry]
            _, _, radius_km = bounding_circle(test)
            test_nm = int(radius_km / NM_TO_KM)
            if test_nm > MAX_GROUP_NM:
                existing = [e["_key"] for e in group]
                log.debug(
                    "auto-group: %s doesn't fit with [%s] (%dnm > %dnm)",
                    key,
                    ",".join(existing),
                    test_nm,
                    MAX_GROUP_NM,
                )
                continue
            group.append(entry)
            existing = [e["_key"] for e in group]
            log.debug(
                "auto-group: %s joined [%s] (%dnm)",
                key,
                ",".join(existing),
                test_nm,
            )
            placed = True
            break

        if not placed:
            log.debug("auto-group: %s starts new group", key)
            groups.append([entry])

    for group in groups:
        keys = [e["_key"] for e in group]
        _, _, r_km = bounding_circle(group)
        log.debug(
            "auto-group result: [%s] — %dnm",
            ",".join(keys),
            int(r_km / NM_TO_KM),
        )

    return groups


async def fetch_aircraft(
    sources: list[dict[str, Any]],
    locations: dict[str, dict[str, Any]],
    session: aiohttp.ClientSession,
) -> list[dict[str, Any]]:
    groups = _auto_group_locations(locations)

    # separate ultrafeeder (no grouping, no rate limits) from API sources
    api_sources: list[tuple[str, dict[str, str]]] = []
    uf_tasks: list[asyncio.Task[list[dict[str, Any]]]] = []

    for source in sources:
        src_type = source.get("type", "")

        if src_type == "ultrafeeder":
            uf_tasks.append(
                asyncio.create_task(_fetch_ultrafeeder(source["url"], session))
            )
            continue

        api_def = API_SOURCES.get(src_type)
        if not api_def:
            log.debug("skipping unknown source type: %s", src_type)
            continue

        api_sources.append((src_type, api_def))

    seen: dict[str, dict[str, Any]] = {}

    # process groups — 1s apart, all ready sources in parallel per group
    for i, group in enumerate(groups):
        if i > 0:
            await asyncio.sleep(1)

        # compute circle for this group
        if len(group) == 1:
            loc = group[0]
            lat, lon = loc["lat"], loc["lon"]
            dist_nm = max(1, min(int(loc["radius_km"] / NM_TO_KM), MAX_GROUP_NM))
            group_label = loc["_key"]
        else:
            lat, lon, radius_km = bounding_circle(group)
            dist_nm = max(1, int(radius_km / NM_TO_KM))
            keys = [loc["_key"] for loc in group]
            group_label = f"auto({','.join(keys)})"
            log.debug(
                "%s: %d locations, circle %.4f,%.4f r=%dnm",
                group_label,
                len(group),
                lat,
                lon,
                dist_nm,
            )

        # fire all ready sources in parallel
        group_tasks: list[asyncio.Task[list[dict[str, Any]] | None]] = []
        for src_type, api_def in api_sources:
            if not _source_ready(src_type):
                remaining = _source_cooldowns[src_type] - time.time()
                log.debug(
                    "skipping %s for %s (cooling down, %.0fs left)",
                    src_type,
                    group_label,
                    remaining,
                )
                continue

            label = f"{src_type}@{group_label}"
            url = api_def["url"].format(lat=lat, lon=lon, dist=dist_nm)
            group_tasks.append(
                asyncio.create_task(
                    _fetch_api_source(label, url, api_def["key"], session)
                )
            )

        for task in group_tasks:
            result = await task
            if result is not None:
                _dedup_aircraft(seen, result)

    # collect ultrafeeder results
    for task in uf_tasks:
        ac = await task
        _dedup_aircraft(seen, ac)

    log.debug("total unique aircraft after dedup: %d", len(seen))
    return list(seen.values())
