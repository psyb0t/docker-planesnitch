"""Configuration loading and unit conversion helpers."""

import logging
from typing import Any

import yaml

log = logging.getLogger("planesnitch")

NM_TO_KM = 1.852
FT_TO_M = 0.3048
MI_TO_KM = 1.60934
KTS_TO_KMH = 1.852
KTS_TO_MPH = 1.15078
DATA_DIR = "/csv"

VALID_DISPLAY_UNITS = ("aviation", "metric", "imperial")

SQUAWK_LABELS = {
    "7500": "HIJACK",
    "7600": "RADIO FAILURE",
    "7700": "EMERGENCY",
    "7400": "UNMANNED LOST LINK",
    "7777": "MILITARY INTERCEPT",
}


def resolve_distance_km(
    cfg: dict[str, Any], key_prefix: str, default: float | None = None
) -> float | None:
    km = cfg.get(f"{key_prefix}_km")
    mi = cfg.get(f"{key_prefix}_mi")
    nm = cfg.get(f"{key_prefix}_nm")
    set_keys = [
        (k, v) for k, v in [("km", km), ("mi", mi), ("nm", nm)] if v is not None
    ]
    if len(set_keys) > 1:
        names = [f"{key_prefix}_{k}" for k, _ in set_keys]
        raise SystemExit(f"conflicting distance keys: {', '.join(names)} — pick one")
    if km is not None:
        return float(km)
    if mi is not None:
        return float(mi) * MI_TO_KM
    if nm is not None:
        return float(nm) * NM_TO_KM
    return default


def resolve_altitude_ft(
    cfg: dict[str, Any], key_prefix: str, default: float | None = None
) -> float | None:
    ft = cfg.get(f"{key_prefix}_ft")
    m = cfg.get(f"{key_prefix}_m")
    set_keys = [(k, v) for k, v in [("ft", ft), ("m", m)] if v is not None]
    if len(set_keys) > 1:
        names = [f"{key_prefix}_{k}" for k, _ in set_keys]
        raise SystemExit(f"conflicting altitude keys: {', '.join(names)} — pick one")
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

    log.debug("config loaded: %s", cfg)
    return cfg
