"""Tests for config.py."""

import os
import tempfile

import pytest

from .config import (
    convert_altitude,
    convert_distance,
    convert_speed,
    format_altitude,
    format_distance,
    format_speed,
    load_config,
    parse_duration,
    resolve_altitude_ft,
    resolve_distance_km,
    unit_labels,
)

# --- parse_duration ---


class TestParseDuration:
    def test_int(self):
        assert parse_duration(15) == 15

    def test_float(self):
        assert parse_duration(15.9) == 15

    def test_str_digits(self):
        assert parse_duration("300") == 300

    def test_seconds(self):
        assert parse_duration("90s") == 90

    def test_minutes(self):
        assert parse_duration("5m") == 300

    def test_hours(self):
        assert parse_duration("2h") == 7200

    def test_hours_minutes(self):
        assert parse_duration("1h30m") == 5400

    def test_hours_minutes_seconds(self):
        assert parse_duration("1h3m8s") == 3788

    def test_minutes_seconds(self):
        assert parse_duration("2m30s") == 150

    def test_case_insensitive(self):
        assert parse_duration("5M") == 300
        assert parse_duration("1H") == 3600

    def test_empty_raises(self):
        with pytest.raises(ValueError, match="empty duration"):
            parse_duration("")

    def test_invalid_raises(self):
        with pytest.raises(ValueError, match="invalid duration"):
            parse_duration("abc")

    def test_invalid_suffix_raises(self):
        with pytest.raises(ValueError, match="invalid duration"):
            parse_duration("5x")

    def test_zero(self):
        assert parse_duration(0) == 0

    def test_str_zero(self):
        assert parse_duration("0") == 0


# --- resolve_distance_km ---


class TestResolveDistanceKm:
    def test_km(self):
        assert resolve_distance_km({"radius_km": 100}, "radius") == 100.0

    def test_mi(self):
        result = resolve_distance_km({"radius_mi": 100}, "radius")
        assert result == pytest.approx(160.934, rel=1e-3)

    def test_nm(self):
        result = resolve_distance_km({"radius_nm": 100}, "radius")
        assert result == pytest.approx(185.2, rel=1e-3)

    def test_default(self):
        assert resolve_distance_km({}, "radius", default=50) == 50

    def test_none_default(self):
        assert resolve_distance_km({}, "radius") is None

    def test_conflict_raises(self):
        with pytest.raises(SystemExit, match="conflicting"):
            resolve_distance_km({"radius_km": 10, "radius_mi": 10}, "radius")

    def test_inline_km(self):
        assert resolve_distance_km({"radius": "30km"}, "radius") == 30.0

    def test_inline_mi(self):
        result = resolve_distance_km({"radius": "50mi"}, "radius")
        assert result == pytest.approx(50 * 1.60934, rel=1e-3)

    def test_inline_nm(self):
        result = resolve_distance_km({"radius": "100nm"}, "radius")
        assert result == pytest.approx(100 * 1.852, rel=1e-3)

    def test_inline_plain_number(self):
        assert resolve_distance_km({"radius": 30}, "radius") == 30.0

    def test_inline_case_insensitive(self):
        assert resolve_distance_km({"radius": "30KM"}, "radius") == 30.0

    def test_inline_with_spaces(self):
        assert resolve_distance_km({"radius": " 30km "}, "radius") == 30.0

    def test_inline_decimal(self):
        assert resolve_distance_km({"radius": "30.5km"}, "radius") == 30.5

    def test_inline_invalid_raises(self):
        with pytest.raises(SystemExit, match="invalid distance"):
            resolve_distance_km({"radius": "30parsecs"}, "radius")

    def test_inline_takes_priority(self):
        # Single key should be checked first, suffix keys ignored
        result = resolve_distance_km(
            {"radius": "30km", "radius_mi": 100}, "radius"
        )
        assert result == 30.0


# --- resolve_altitude_ft ---


class TestResolveAltitudeFt:
    def test_ft(self):
        assert resolve_altitude_ft({"alt_ft": 3000}, "alt") == 3000.0

    def test_m(self):
        result = resolve_altitude_ft({"alt_m": 1000}, "alt")
        assert result == pytest.approx(3280.84, rel=1e-3)

    def test_default(self):
        assert resolve_altitude_ft({}, "alt", default=0) == 0

    def test_none_default(self):
        assert resolve_altitude_ft({}, "alt") is None

    def test_conflict_raises(self):
        with pytest.raises(SystemExit, match="conflicting"):
            resolve_altitude_ft({"alt_ft": 100, "alt_m": 100}, "alt")

    def test_inline_ft(self):
        assert resolve_altitude_ft({"alt": "3000ft"}, "alt") == 3000.0

    def test_inline_m(self):
        result = resolve_altitude_ft({"alt": "1000m"}, "alt")
        assert result == pytest.approx(1000 / 0.3048, rel=1e-3)

    def test_inline_plain_number(self):
        assert resolve_altitude_ft({"alt": 3000}, "alt") == 3000.0

    def test_inline_case_insensitive(self):
        assert resolve_altitude_ft({"alt": "3000FT"}, "alt") == 3000.0

    def test_inline_with_spaces(self):
        assert resolve_altitude_ft({"alt": " 3000ft "}, "alt") == 3000.0

    def test_inline_decimal(self):
        assert resolve_altitude_ft({"alt": "3000.5ft"}, "alt") == 3000.5

    def test_inline_invalid_raises(self):
        with pytest.raises(SystemExit, match="invalid altitude"):
            resolve_altitude_ft({"alt": "3000cubits"}, "alt")

    def test_inline_takes_priority(self):
        result = resolve_altitude_ft({"alt": "3000ft", "alt_m": 500}, "alt")
        assert result == 3000.0


# --- format_altitude ---


class TestFormatAltitude:
    def test_aviation(self):
        assert format_altitude(12350, "aviation") == "12,350 ft"

    def test_imperial(self):
        assert format_altitude(12350, "imperial") == "12,350 ft"

    def test_metric(self):
        assert format_altitude(12350, "metric") == "3,764 m"

    def test_zero(self):
        assert format_altitude(0, "metric") == "0 m"

    def test_float_input(self):
        # Should not show decimals for ft
        assert format_altitude(12350.7, "aviation") == "12,350 ft"


# --- format_distance ---


class TestFormatDistance:
    def test_metric(self):
        assert format_distance(183.2, "metric") == "183 km"

    def test_imperial(self):
        assert format_distance(183.2, "imperial") == "114 mi"

    def test_aviation(self):
        assert format_distance(183.2, "aviation") == "99 nm"

    def test_zero(self):
        assert format_distance(0, "metric") == "0 km"


# --- format_speed ---


class TestFormatSpeed:
    def test_aviation(self):
        assert format_speed(413, "aviation") == "413 kts"

    def test_metric(self):
        assert format_speed(413, "metric") == "765 km/h"

    def test_imperial(self):
        assert format_speed(413, "imperial") == "475 mph"

    def test_zero(self):
        assert format_speed(0, "aviation") == "0 kts"


# --- convert_altitude ---


class TestConvertAltitude:
    def test_aviation(self):
        assert convert_altitude(12350, "aviation") == 12350

    def test_imperial(self):
        assert convert_altitude(12350, "imperial") == 12350

    def test_metric(self):
        assert convert_altitude(12350, "metric") == pytest.approx(3764.3, rel=1e-3)


# --- convert_distance ---


class TestConvertDistance:
    def test_metric(self):
        assert convert_distance(183.2, "metric") == 183.2

    def test_imperial(self):
        assert convert_distance(183.2, "imperial") == pytest.approx(113.8, rel=1e-2)

    def test_aviation(self):
        assert convert_distance(183.2, "aviation") == pytest.approx(98.9, rel=1e-2)


# --- convert_speed ---


class TestConvertSpeed:
    def test_aviation(self):
        assert convert_speed(413, "aviation") == 413.0

    def test_metric(self):
        assert convert_speed(413, "metric") == pytest.approx(764.9, rel=1e-2)

    def test_imperial(self):
        assert convert_speed(413, "imperial") == pytest.approx(475.3, rel=1e-2)


# --- unit_labels ---


class TestUnitLabels:
    def test_aviation(self):
        assert unit_labels("aviation") == {
            "altitude": "ft",
            "distance": "nm",
            "speed": "kts",
        }

    def test_metric(self):
        assert unit_labels("metric") == {
            "altitude": "m",
            "distance": "km",
            "speed": "km/h",
        }

    def test_imperial(self):
        assert unit_labels("imperial") == {
            "altitude": "ft",
            "distance": "mi",
            "speed": "mph",
        }


# --- load_config ---


class TestLoadConfig:
    def _write_config(self, cfg_str: str) -> str:
        fd, path = tempfile.mkstemp(suffix=".yaml")
        os.write(fd, cfg_str.encode())
        os.close(fd)
        return path

    def _minimal_config(self, **overrides):
        cfg = {
            "poll_interval": "15s",
            "locations": {"home": {"lat": 0, "lon": 0, "radius_km": 50}},
            "sources": [{"type": "adsb_one"}],
            "watchlists": {"everything": {"type": "all"}},
            "alerts": [
                {
                    "name": "Test",
                    "watchlists": ["everything"],
                    "cooldown": "1m",
                    "notify": ["tg"],
                }
            ],
            "notifications": {
                "tg": {"type": "telegram", "bot_token": "x", "chat_id": "y"}
            },
        }
        cfg.update(overrides)
        import yaml

        return yaml.dump(cfg)

    def test_valid_config(self):
        path = self._write_config(self._minimal_config())
        try:
            cfg = load_config(path)
            assert cfg["poll_interval"] == 15
            assert cfg["display_units"] == "aviation"
            assert cfg["alerts"][0]["cooldown"] == 60
        finally:
            os.unlink(path)

    def test_display_units_metric(self):
        path = self._write_config(self._minimal_config(display_units="metric"))
        try:
            cfg = load_config(path)
            assert cfg["display_units"] == "metric"
        finally:
            os.unlink(path)

    def test_invalid_display_units(self):
        path = self._write_config(self._minimal_config(display_units="bananas"))
        try:
            with pytest.raises(SystemExit, match="invalid display_units"):
                load_config(path)
        finally:
            os.unlink(path)

    def test_missing_key(self):
        path = self._write_config("locations: {}\n")
        try:
            with pytest.raises(SystemExit, match="missing required"):
                load_config(path)
        finally:
            os.unlink(path)

    def test_empty_locations(self):
        path = self._write_config(self._minimal_config(locations={}))
        try:
            with pytest.raises(SystemExit, match="non-empty dict"):
                load_config(path)
        finally:
            os.unlink(path)

    def test_duration_poll_interval(self):
        path = self._write_config(self._minimal_config(poll_interval="2m"))
        try:
            cfg = load_config(path)
            assert cfg["poll_interval"] == 120
        finally:
            os.unlink(path)

    def test_invalid_poll_interval(self):
        path = self._write_config(self._minimal_config(poll_interval="nope"))
        try:
            with pytest.raises(SystemExit, match="invalid poll_interval"):
                load_config(path)
        finally:
            os.unlink(path)

    def test_invalid_cooldown(self):
        cfg_str = self._minimal_config()
        import yaml

        cfg = yaml.safe_load(cfg_str)
        cfg["alerts"][0]["cooldown"] = "lol"
        path = self._write_config(yaml.dump(cfg))
        try:
            with pytest.raises(SystemExit, match="invalid cooldown"):
                load_config(path)
        finally:
            os.unlink(path)
