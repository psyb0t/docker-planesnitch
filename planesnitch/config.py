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


SQUAWK_LABELS = {
    "7500": "HIJACK",
    "7600": "RADIO FAILURE",
    "7700": "EMERGENCY",
    "7400": "UNMANNED LOST LINK",
    "7777": "MILITARY INTERCEPT",
}


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


def load_config(path: str) -> dict[str, Any]:
    log.debug("loading config from %s", path)
    with open(path) as f:
        cfg = yaml.safe_load(f)

    for key in ("locations", "sources", "watchlists", "alerts", "notifications"):
        if key not in cfg:
            raise SystemExit(f"missing required config key: {key}")

    if not isinstance(cfg["locations"], dict) or not cfg["locations"]:
        raise SystemExit("locations must be a non-empty dict of named locations")

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

    for rule in cfg.get("alerts", []):
        if "cooldown" not in rule:
            continue
        try:
            rule["cooldown"] = parse_duration(rule["cooldown"])
        except ValueError as e:
            raise SystemExit(
                f"invalid cooldown in alert {rule.get('name', '?')!r}: {e}"
            ) from None

    log.debug("config loaded: %s", cfg)
    return cfg
