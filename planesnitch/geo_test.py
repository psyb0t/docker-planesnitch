"""Tests for geo.py."""

import pytest

from .geo import calc_distance_km, find_nearest_location, get_distance_km


class TestCalcDistanceKm:
    def test_same_point(self):
        assert calc_distance_km(0, 0, 0, 0) == 0.0

    def test_known_distance(self):
        # New York to London ~ 5570 km
        dist = calc_distance_km(40.7128, -74.0060, 51.5074, -0.1278)
        assert dist == pytest.approx(5570, rel=0.01)

    def test_short_distance(self):
        # ~111 km per degree of latitude at equator
        dist = calc_distance_km(0, 0, 1, 0)
        assert dist == pytest.approx(111.19, rel=0.01)

    def test_antipodal(self):
        # North pole to south pole ~ 20015 km
        dist = calc_distance_km(90, 0, -90, 0)
        assert dist == pytest.approx(20015, rel=0.01)


class TestGetDistanceKm:
    def test_valid(self):
        ac = {"lat": 39.0, "lon": -77.0}
        loc = {"lat": 38.8719, "lon": -77.0563}
        dist = get_distance_km(ac, loc)
        assert dist is not None
        assert dist > 0

    def test_missing_lat(self):
        ac = {"lon": -77.0}
        loc = {"lat": 38.8719, "lon": -77.0563}
        assert get_distance_km(ac, loc) is None

    def test_missing_lon(self):
        ac = {"lat": 39.0}
        loc = {"lat": 38.8719, "lon": -77.0563}
        assert get_distance_km(ac, loc) is None

    def test_both_missing(self):
        ac = {}
        loc = {"lat": 38.8719, "lon": -77.0563}
        assert get_distance_km(ac, loc) is None


class TestFindNearestLocation:
    def test_single_location(self):
        ac = {"lat": 39.0, "lon": -77.0}
        locs = {"home": {"lat": 38.8719, "lon": -77.0563}}
        result = find_nearest_location(ac, locs)
        assert result is not None
        assert result[0] == "home"

    def test_picks_nearest(self):
        ac = {"lat": 39.0, "lon": -77.0}
        locs = {
            "far": {"lat": 50.0, "lon": 0.0},
            "near": {"lat": 38.9, "lon": -77.1},
        }
        result = find_nearest_location(ac, locs)
        assert result is not None
        assert result[0] == "near"

    def test_no_position_returns_first(self):
        ac = {}
        locs = {"home": {"lat": 0, "lon": 0}, "work": {"lat": 1, "lon": 1}}
        result = find_nearest_location(ac, locs)
        assert result is not None
        assert result[0] == "home"

    def test_empty_locations(self):
        ac = {"lat": 39.0, "lon": -77.0}
        assert find_nearest_location(ac, {}) is None

    def test_no_position_empty_locations(self):
        ac = {}
        assert find_nearest_location(ac, {}) is None
