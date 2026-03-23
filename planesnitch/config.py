"""Configuration loading and unit conversion helpers."""

import logging
import os
import re
from typing import Any

import yaml

log = logging.getLogger("planesnitch")

NM_TO_KM = 1.852
FT_TO_M = 0.3048
MI_TO_KM = 1.60934
KTS_TO_KMH = 1.852
KTS_TO_MPH = 1.15078
DATA_DIR = os.environ.get("PLANESNITCH_CSV_DIR", "/csv")

VALID_DISPLAY_UNITS = ("aviation", "metric", "imperial")
VALID_SOURCE_TYPES = ("adsb_lol", "adsb_fi", "airplanes_live", "adsb_one", "ultrafeeder")
VALID_WATCHLIST_TYPES = ("all", "squawk", "icao", "icao_csv", "proximity")
VALID_NOTIFICATION_TYPES = ("telegram", "webhook")

_DURATION_RE = re.compile(r"(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?$", re.IGNORECASE)


def parse_duration(value: Any) -> int:
    """Parse a duration value into seconds.

    Accepts int/float (raw seconds) or strings like '5m', '1h30m', '2h', '90s'.
    """
    if isinstance(value, (int, float)):
        return int(value)

    s = str(value).strip()
    if not s:
        raise ValueError("empty duration")

    if s.isdigit():
        return int(s)

    m = _DURATION_RE.match(s)
    if not m or not any(m.groups()):
        raise ValueError(f"invalid duration: {s!r} — use e.g. 5m, 1h30m, 90s")

    hours = int(m.group(1) or 0)
    minutes = int(m.group(2) or 0)
    seconds = int(m.group(3) or 0)
    return hours * 3600 + minutes * 60 + seconds


# Exact squawk codes: code -> (meaning, scope)
_SQUAWK_EXACT: dict[str, tuple[str, str]] = {
    # Global / ICAO
    "7700": ("Emergency", "global"),
    "7600": ("Radio failure", "global"),
    "7500": ("Hijack", "global"),
    "7400": ("Unmanned lost link", "global"),
    "7777": ("Military intercept", "global"),
    "0000": ("Military reserved", "global"),
    "2000": ("Entering SSR area", "global"),
    "1000": ("Mode S / ADS-B correlation", "global"),
    # Europe / ICAO
    "7000": ("VFR", "EU"),
    # US / Canada
    "1200": ("VFR", "US"),
    "1202": ("Glider VFR", "US"),
    "1255": ("Firefighting", "US"),
    "1276": ("ADIZ penetration, no comms", "US"),
    "1277": ("SAR mission", "US"),
    "4000": ("Military ops", "US"),
}

# Range-based squawk codes: (start, end, meaning, scope)
_SQUAWK_RANGES: list[tuple[int, int, str, str]] = [
    (4400, 4477, "High altitude / pressure suit", "US"),
    (4401, 4433, "Federal law enforcement", "US"),
    (4466, 4477, "Federal law enforcement", "US"),
    (5000, 5000, "DoD reserved", "US"),
    (5400, 5400, "DoD reserved", "US"),
    (6100, 6100, "DoD reserved", "US"),
    (6400, 6400, "DoD reserved", "US"),
    (7501, 7577, "DoD reserved", "US"),
]


def squawk_meaning(
    code: str | None,
) -> dict[str, str] | None:
    """Look up squawk code meaning. Returns dict with meaning+scope or None."""
    if not code:
        return None
    code = code.strip()
    exact = _SQUAWK_EXACT.get(code)
    if exact:
        return {"meaning": exact[0], "scope": exact[1]}
    try:
        num = int(code)
    except ValueError:
        return None
    # More specific ranges first (sorted narrower ranges earlier)
    for start, end, meaning, scope in _SQUAWK_RANGES:
        if start <= num <= end:
            return {"meaning": meaning, "scope": scope}
    return None


_UNIT_RE = re.compile(r"^([\d.]+)\s*(km|mi|nm|ft|m)$", re.IGNORECASE)

# All units convert to meters as base, then we convert out
_TO_METERS = {
    "m": 1.0,
    "km": 1000.0,
    "ft": FT_TO_M,
    "mi": MI_TO_KM * 1000.0,
    "nm": NM_TO_KM * 1000.0,
}

_FROM_METERS = {
    "km": 1.0 / 1000.0,
    "ft": 1.0 / FT_TO_M,
}


def _parse_length(value: Any, to_unit: str) -> float | None:
    """Parse a value with unit suffix and convert to target unit.

    Accepts any of: m, km, ft, mi, nm.
    to_unit must be 'km' or 'ft'.
    Returns None if value is a plain number or unparseable.
    """
    if isinstance(value, (int, float)):
        return None
    s = str(value).strip()
    match = _UNIT_RE.match(s)
    if not match:
        return None
    num = float(match.group(1))
    unit = match.group(2).lower()
    meters = num * _TO_METERS[unit]
    return meters * _FROM_METERS[to_unit]


def resolve_distance_km(
    cfg: dict[str, Any],
    key_prefix: str,
    default: float | None = None,
) -> float | None:
    single = cfg.get(key_prefix)
    if single is not None:
        parsed = _parse_length(single, "km")
        if parsed is not None:
            return parsed
        if isinstance(single, (int, float)):
            return float(single)
        raise SystemExit(
            f"invalid value for {key_prefix}: {single!r}"
            " — use e.g. 30km, 50nm, 100mi, 5000ft, 1000m"
        )

    # Fallback: separate keys with unit suffix
    km = cfg.get(f"{key_prefix}_km")
    mi = cfg.get(f"{key_prefix}_mi")
    nm = cfg.get(f"{key_prefix}_nm")
    set_keys = [
        (k, v) for k, v in [("km", km), ("mi", mi), ("nm", nm)] if v is not None
    ]
    if len(set_keys) > 1:
        names = [f"{key_prefix}_{k}" for k, _ in set_keys]
        raise SystemExit(f"conflicting keys: {', '.join(names)} — pick one")
    if km is not None:
        return float(km)
    if mi is not None:
        return float(mi) * MI_TO_KM
    if nm is not None:
        return float(nm) * NM_TO_KM
    return default


def resolve_altitude_ft(
    cfg: dict[str, Any],
    key_prefix: str,
    default: float | None = None,
) -> float | None:
    single = cfg.get(key_prefix)
    if single is not None:
        parsed = _parse_length(single, "ft")
        if parsed is not None:
            return parsed
        if isinstance(single, (int, float)):
            return float(single)
        raise SystemExit(
            f"invalid value for {key_prefix}: {single!r}"
            " — use e.g. 3000ft, 1000m, 1km, 5nm"
        )

    # Fallback: separate keys with unit suffix
    ft = cfg.get(f"{key_prefix}_ft")
    m = cfg.get(f"{key_prefix}_m")
    set_keys = [(k, v) for k, v in [("ft", ft), ("m", m)] if v is not None]
    if len(set_keys) > 1:
        names = [f"{key_prefix}_{k}" for k, _ in set_keys]
        raise SystemExit(f"conflicting keys: {', '.join(names)} — pick one")
    if ft is not None:
        return float(ft)
    if m is not None:
        return float(m) / FT_TO_M
    return default


def format_altitude(alt_ft: float, units: str) -> str:
    if units == "metric":
        return f"{alt_ft * FT_TO_M:,.0f} m"
    return f"{int(alt_ft):,} ft"


def format_distance(dist_km: float, units: str) -> str:
    if units == "imperial":
        return f"{dist_km / MI_TO_KM:.0f} mi"
    if units == "aviation":
        return f"{dist_km / NM_TO_KM:.0f} nm"
    return f"{dist_km:.0f} km"


def format_speed(speed_kts: float, units: str) -> str:
    if units == "metric":
        return f"{speed_kts * KTS_TO_KMH:.0f} km/h"
    if units == "imperial":
        return f"{speed_kts * KTS_TO_MPH:.0f} mph"
    return f"{speed_kts:.0f} kts"


def convert_altitude(alt_ft: float, units: str) -> float:
    if units == "metric":
        return round(alt_ft * FT_TO_M, 1)
    return alt_ft


def convert_distance(dist_km: float, units: str) -> float:
    if units == "imperial":
        return round(dist_km / MI_TO_KM, 1)
    if units == "aviation":
        return round(dist_km / NM_TO_KM, 1)
    return round(dist_km, 1)


def convert_speed(speed_kts: float, units: str) -> float:
    if units == "metric":
        return round(speed_kts * KTS_TO_KMH, 1)
    if units == "imperial":
        return round(speed_kts * KTS_TO_MPH, 1)
    return round(speed_kts, 1)


def unit_labels(units: str) -> dict[str, str]:
    if units == "metric":
        return {"altitude": "m", "distance": "km", "speed": "km/h"}
    if units == "imperial":
        return {"altitude": "ft", "distance": "mi", "speed": "mph"}
    return {"altitude": "ft", "distance": "nm", "speed": "kts"}


def _require_mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise SystemExit(f"{label} must be a mapping")
    return value


def _require_list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise SystemExit(f"{label} must be a list")
    return value


def _require_non_empty_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SystemExit(f"{label} must be a non-empty string")
    return value.strip()


def _require_number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SystemExit(f"{label} must be a number")
    return float(value)


def _validate_locations(locations: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(locations, dict) or not locations:
        raise SystemExit("locations must be a non-empty dict of named locations")

    for name, loc in locations.items():
        loc = _require_mapping(loc, f"location {name!r}")
        _require_number(loc.get("lat"), f"location {name!r}.lat")
        _require_number(loc.get("lon"), f"location {name!r}.lon")
        resolve_distance_km(loc, "radius", default=150)
        display_name = loc.get("name")
        if display_name is not None and not isinstance(display_name, str):
            raise SystemExit(f"location {name!r}.name must be a string")

    return locations


def _validate_sources(sources: Any) -> list[dict[str, Any]]:
    sources_list = _require_list(sources, "sources")
    if not sources_list:
        raise SystemExit("sources must be a non-empty list")

    for index, source in enumerate(sources_list):
        source = _require_mapping(source, f"sources[{index}]")
        src_type = _require_non_empty_string(
            source.get("type"), f"sources[{index}].type"
        )
        if src_type not in VALID_SOURCE_TYPES:
            raise SystemExit(
                f"sources[{index}].type must be one of {VALID_SOURCE_TYPES}"
            )
        if src_type == "ultrafeeder":
            _require_non_empty_string(source.get("url"), f"sources[{index}].url")

    return sources_list


def _validate_watchlists(watchlists: Any) -> dict[str, dict[str, Any]]:
    watchlists_map = _require_mapping(watchlists, "watchlists")
    if not watchlists_map:
        raise SystemExit("watchlists must be a non-empty mapping")

    for name, watchlist in watchlists_map.items():
        watchlist = _require_mapping(watchlist, f"watchlist {name!r}")
        wl_type = _require_non_empty_string(
            watchlist.get("type"), f"watchlist {name!r}.type"
        )
        if wl_type not in VALID_WATCHLIST_TYPES:
            raise SystemExit(
                f"watchlist {name!r}.type must be one of {VALID_WATCHLIST_TYPES}"
            )

        if wl_type in ("squawk", "icao"):
            values = _require_list(watchlist.get("values"), f"watchlist {name!r}.values")
            if not values:
                raise SystemExit(f"watchlist {name!r}.values must not be empty")
            for index, value in enumerate(values):
                _require_non_empty_string(
                    value, f"watchlist {name!r}.values[{index}]"
                )

        if wl_type == "icao_csv":
            _require_non_empty_string(
                watchlist.get("source"), f"watchlist {name!r}.source"
            )

        if wl_type == "proximity":
            resolve_altitude_ft(watchlist, "min_altitude")
            resolve_altitude_ft(watchlist, "max_altitude")

    return watchlists_map


def _validate_notifications(notifications: Any) -> dict[str, dict[str, Any]]:
    notifications_map = _require_mapping(notifications, "notifications")

    for name, notification in notifications_map.items():
        notification = _require_mapping(notification, f"notification {name!r}")
        notif_type = _require_non_empty_string(
            notification.get("type"), f"notification {name!r}.type"
        )
        if notif_type not in VALID_NOTIFICATION_TYPES:
            raise SystemExit(
                f"notification {name!r}.type must be one of {VALID_NOTIFICATION_TYPES}"
            )

        if notif_type == "telegram":
            bot_token = notification.get("bot_token")
            chat_id = notification.get("chat_id")
            if bot_token is not None and not isinstance(bot_token, str):
                raise SystemExit(f"notification {name!r}.bot_token must be a string")
            if chat_id is not None and not isinstance(chat_id, str):
                raise SystemExit(f"notification {name!r}.chat_id must be a string")

        if notif_type == "webhook":
            _require_non_empty_string(
                notification.get("url"), f"notification {name!r}.url"
            )
            headers = notification.get("headers")
            if headers is not None and not isinstance(headers, dict):
                raise SystemExit(f"notification {name!r}.headers must be a mapping")

    return notifications_map


def _validate_alerts(
    alerts: Any,
    watchlists: dict[str, dict[str, Any]],
    locations: dict[str, dict[str, Any]],
    notifications: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    alerts_list = _require_list(alerts, "alerts")
    if not alerts_list:
        raise SystemExit("alerts must be a non-empty list")

    for index, rule in enumerate(alerts_list):
        rule = _require_mapping(rule, f"alerts[{index}]")
        _require_non_empty_string(rule.get("name"), f"alerts[{index}].name")

        watchlist_names = _require_list(rule.get("watchlists"), f"alerts[{index}].watchlists")
        if not watchlist_names:
            raise SystemExit(f"alerts[{index}].watchlists must not be empty")
        for watchlist_name in watchlist_names:
            watchlist_name = _require_non_empty_string(
                watchlist_name, f"alerts[{index}].watchlists entry"
            )
            if watchlist_name not in watchlists:
                raise SystemExit(
                    f"alerts[{index}] references unknown watchlist {watchlist_name!r}"
                )

        notify_names = _require_list(rule.get("notify"), f"alerts[{index}].notify")
        if not notify_names:
            raise SystemExit(f"alerts[{index}].notify must not be empty")
        for notify_name in notify_names:
            notify_name = _require_non_empty_string(
                notify_name, f"alerts[{index}].notify entry"
            )
            if notify_name not in notifications:
                raise SystemExit(
                    f"alerts[{index}] references unknown notification {notify_name!r}"
                )
            notif = notifications[notify_name]
            if notif["type"] == "telegram":
                _require_non_empty_string(
                    notif.get("bot_token"),
                    f"notification {notify_name!r}.bot_token",
                )
                _require_non_empty_string(
                    notif.get("chat_id"),
                    f"notification {notify_name!r}.chat_id",
                )

        location_names = rule.get("locations")
        if location_names is not None:
            location_names = _require_list(
                location_names, f"alerts[{index}].locations"
            )
            if not location_names:
                raise SystemExit(f"alerts[{index}].locations must not be empty")
            for location_name in location_names:
                location_name = _require_non_empty_string(
                    location_name, f"alerts[{index}].locations entry"
                )
                if location_name not in locations:
                    raise SystemExit(
                        f"alerts[{index}] references unknown location {location_name!r}"
                    )

        if "cooldown" in rule:
            try:
                rule["cooldown"] = parse_duration(rule["cooldown"])
            except ValueError as e:
                raise SystemExit(
                    f"invalid cooldown in alert {rule.get('name', '?')!r}: {e}"
                ) from None

    return alerts_list


def load_config(path: str) -> dict[str, Any]:
    log.debug("loading config from %s", path)
    with open(path) as f:
        cfg = yaml.safe_load(f)

    if cfg is None:
        raise SystemExit("config file is empty")
    if not isinstance(cfg, dict):
        raise SystemExit("config file must contain a top-level mapping")

    for key in ("locations", "sources", "watchlists", "alerts", "notifications"):
        if key not in cfg:
            raise SystemExit(f"missing required config key: {key}")

    du = cfg.get("display_units", "aviation")
    if du not in VALID_DISPLAY_UNITS:
        raise SystemExit(
            f"invalid display_units: {du} — must be one of {VALID_DISPLAY_UNITS}"
        )
    cfg["display_units"] = du

    try:
        cfg["poll_interval"] = parse_duration(cfg.get("poll_interval", 15))
    except ValueError as e:
        raise SystemExit(f"invalid poll_interval: {e}") from None

    cfg["locations"] = _validate_locations(cfg["locations"])
    cfg["sources"] = _validate_sources(cfg["sources"])
    cfg["watchlists"] = _validate_watchlists(cfg["watchlists"])
    cfg["notifications"] = _validate_notifications(cfg["notifications"])
    cfg["alerts"] = _validate_alerts(
        cfg["alerts"],
        cfg["watchlists"],
        cfg["locations"],
        cfg["notifications"],
    )

    log.debug("config loaded: %s", cfg)
    return cfg
