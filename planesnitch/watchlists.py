"""Watchlist loading and matching."""

import csv
import io
import logging
import os
from typing import Any

from .config import DATA_DIR, resolve_altitude_ft, resolve_distance_km
from .geo import get_distance_km

log = logging.getLogger("planesnitch")


def parse_alert_csv(text: str) -> dict[str, dict[str, str]]:
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        return {}

    clean_fields = []
    for f in reader.fieldnames:
        clean_fields.append(f.lstrip("$#").strip())
    reader.fieldnames = clean_fields

    result: dict[str, dict[str, str]] = {}
    icao_key = clean_fields[0]

    for row in reader:
        icao = row.get(icao_key, "").strip().lower()
        if not icao:
            continue
        result[icao] = {k: v.strip() for k, v in row.items() if k != icao_key}

    return result


def load_watchlists(
    watchlists_config: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    loaded: dict[str, dict[str, Any]] = {}

    for name, wl in watchlists_config.items():
        wl_type = wl.get("type", "")

        if wl_type == "icao_csv":
            source = wl.get("source", "")
            path = os.path.join(DATA_DIR, source)
            log.info("loading watchlist %s from %s", name, path)
            try:
                with open(path) as f:
                    text = f.read()
                db = parse_alert_csv(text)
                log.info("watchlist %s: %d aircraft loaded", name, len(db))
                loaded[name] = {"type": "icao_csv", "db": db}
            except Exception:
                log.warning("failed to load watchlist %s", name, exc_info=True)
                loaded[name] = {"type": "icao_csv", "db": {}}
            continue

        if wl_type == "squawk":
            values = set(str(v) for v in wl.get("values", []))
            log.debug("watchlist %s: squawk values %s", name, values)
            loaded[name] = {"type": "squawk", "values": values}
            continue

        if wl_type == "icao":
            values = set(v.lower() for v in wl.get("values", []))
            log.debug("watchlist %s: icao values %s", name, values)
            loaded[name] = {"type": "icao", "values": values}
            continue

        if wl_type == "all":
            log.debug("watchlist %s: matches all aircraft", name)
            loaded[name] = {"type": "all"}
            continue

        if wl_type == "proximity":
            min_alt_ft = resolve_altitude_ft(wl, "min_altitude")
            max_alt_ft = resolve_altitude_ft(wl, "max_altitude")
            log.debug(
                "watchlist %s: proximity alt=%s-%sft",
                name,
                min_alt_ft,
                max_alt_ft,
            )
            loaded[name] = {
                "type": "proximity",
                "min_altitude_ft": min_alt_ft,
                "max_altitude_ft": max_alt_ft,
            }
            continue

        log.warning("unknown watchlist type %s for %s", wl_type, name)

    return loaded


def matches_watchlist(
    aircraft: dict[str, Any],
    watchlist: dict[str, Any],
    location: dict[str, Any],
) -> dict[str, Any] | None:
    wl_type = watchlist["type"]
    hex_code = aircraft.get("hex", "").lower()

    if wl_type == "squawk":
        squawk = str(aircraft.get("squawk", ""))
        if squawk not in watchlist["values"]:
            return None
        log.debug("squawk match: %s squawk=%s", hex_code, squawk)
        return {"reason": "squawk", "squawk": squawk}

    if wl_type == "icao":
        if hex_code not in watchlist["values"]:
            return None
        log.debug("icao match: %s", hex_code)
        return {"reason": "icao_match"}

    if wl_type == "icao_csv":
        db = watchlist.get("db", {})
        if hex_code not in db:
            return None
        log.debug("icao_csv match: %s info=%s", hex_code, db[hex_code])
        return {"reason": "icao_csv_match", "info": db[hex_code]}

    if wl_type == "all":
        log.debug("all match: %s", hex_code)
        return {"reason": "all"}

    if wl_type == "proximity":
        dist = get_distance_km(aircraft, location)
        if dist is None:
            return None
        radius_km = resolve_distance_km(location, "radius", default=150)
        if dist > radius_km:
            return None

        alt = aircraft.get("alt_baro")
        if isinstance(alt, str):
            return None
        if alt is not None:
            min_alt = watchlist.get("min_altitude_ft")
            if min_alt is not None and alt < min_alt:
                return None
            max_alt = watchlist.get("max_altitude_ft")
            if max_alt is not None and alt > max_alt:
                return None

        log.debug(
            "proximity match: %s dist=%.1fkm alt=%s",
            hex_code,
            dist,
            aircraft.get("alt_baro"),
        )
        return {"reason": "proximity", "distance_km": round(dist, 1)}

    return None
