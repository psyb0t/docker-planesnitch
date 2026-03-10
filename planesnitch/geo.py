"""Geographic distance calculations."""

import math
from typing import Any


def calc_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def get_distance_km(aircraft: dict[str, Any], location: dict[str, Any]) -> float | None:
    ac_lat = aircraft.get("lat")
    ac_lon = aircraft.get("lon")
    if ac_lat is None or ac_lon is None:
        return None

    return calc_distance_km(location["lat"], location["lon"], ac_lat, ac_lon)


def bounding_circle(
    locations: list[dict[str, Any]],
) -> tuple[float, float, float]:
    """Compute a bounding circle for a list of locations.

    Each location must have lat, lon, and optionally radius_km.
    Returns (center_lat, center_lon, radius_km).
    """
    if len(locations) == 1:
        loc = locations[0]
        return loc["lat"], loc["lon"], loc.get("radius_km", 150)

    clat = sum(loc["lat"] for loc in locations) / len(locations)
    clon = sum(loc["lon"] for loc in locations) / len(locations)

    radius = 0.0
    for loc in locations:
        dist = calc_distance_km(clat, clon, loc["lat"], loc["lon"])
        edge = dist + loc.get("radius_km", 150)
        if edge > radius:
            radius = edge

    return clat, clon, radius


def find_nearest_location(
    aircraft: dict[str, Any], locations: dict[str, dict[str, Any]]
) -> tuple[str, dict[str, Any]] | None:
    ac_lat = aircraft.get("lat")
    ac_lon = aircraft.get("lon")
    if ac_lat is None or ac_lon is None:
        for name, loc in locations.items():
            return name, loc
        return None

    best_name = None
    best_loc = None
    best_dist = float("inf")
    for name, loc in locations.items():
        dist = calc_distance_km(loc["lat"], loc["lon"], ac_lat, ac_lon)
        if dist < best_dist:
            best_dist = dist
            best_name = name
            best_loc = loc

    if best_name is None or best_loc is None:
        return None
    return best_name, best_loc
