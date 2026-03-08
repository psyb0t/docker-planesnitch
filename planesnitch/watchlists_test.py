"""Tests for watchlists.py."""

import pytest

from .watchlists import matches_watchlist, parse_alert_csv


class TestParseAlertCsv:
    def test_basic(self):
        text = "$ICAO,$Registration,$Operator\nae07e1,94-0067,USAF\n"
        result = parse_alert_csv(text)
        assert "ae07e1" in result
        assert result["ae07e1"]["Registration"] == "94-0067"
        assert result["ae07e1"]["Operator"] == "USAF"

    def test_strips_prefixes(self):
        text = "$ICAO,$#Tag 1,$Tag 2\nabc123,mil,cargo\n"
        result = parse_alert_csv(text)
        assert "abc123" in result
        assert result["abc123"]["Tag 1"] == "mil"
        assert result["abc123"]["Tag 2"] == "cargo"

    def test_lowercases_hex(self):
        text = "$ICAO,$Operator\nAE07E1,USAF\n"
        result = parse_alert_csv(text)
        assert "ae07e1" in result

    def test_strips_whitespace(self):
        text = "$ICAO,$Operator\n ae07e1 , USAF \n"
        result = parse_alert_csv(text)
        assert "ae07e1" in result
        assert result["ae07e1"]["Operator"] == "USAF"

    def test_empty(self):
        assert parse_alert_csv("") == {}

    def test_header_only(self):
        assert parse_alert_csv("$ICAO,$Operator\n") == {}

    def test_skips_empty_hex(self):
        text = "$ICAO,$Operator\n,USAF\nae07e1,RAF\n"
        result = parse_alert_csv(text)
        assert "" not in result
        assert "ae07e1" in result

    def test_multiple_rows(self):
        text = "$ICAO,$Operator\nae07e1,USAF\nbee123,RAF\n"
        result = parse_alert_csv(text)
        assert len(result) == 2

    def test_short_rows(self):
        text = "$ICAO,$Registration,$Operator,$Type\n0000c8,N917BC\n"
        result = parse_alert_csv(text)
        assert "0000c8" in result
        assert result["0000c8"]["Registration"] == "N917BC"
        assert result["0000c8"]["Operator"] == ""
        assert result["0000c8"]["Type"] == ""


class TestMatchesWatchlist:
    LOC = {"lat": 38.8719, "lon": -77.0563, "radius": "50km"}

    def test_squawk_match(self):
        ac = {"hex": "abc123", "lat": 38.88, "lon": -77.06, "squawk": "7700"}
        wl = {"type": "squawk", "values": {"7500", "7600", "7700"}}
        result = matches_watchlist(ac, wl, self.LOC)
        assert result is not None
        assert result["reason"] == "squawk"
        assert result["squawk"] == "7700"
        assert "distance_km" in result

    def test_squawk_no_match(self):
        ac = {"hex": "abc123", "lat": 38.88, "lon": -77.06, "squawk": "1234"}
        wl = {"type": "squawk", "values": {"7500", "7600", "7700"}}
        assert matches_watchlist(ac, wl, self.LOC) is None

    def test_squawk_no_position(self):
        ac = {"hex": "abc123", "squawk": "7700"}
        wl = {"type": "squawk", "values": {"7500", "7600", "7700"}}
        assert matches_watchlist(ac, wl, self.LOC) is None

    def test_squawk_too_far(self):
        ac = {"hex": "abc123", "lat": 50.0, "lon": 0.0, "squawk": "7700"}
        wl = {"type": "squawk", "values": {"7500", "7600", "7700"}}
        assert matches_watchlist(ac, wl, self.LOC) is None

    def test_icao_match(self):
        ac = {"hex": "abc123", "lat": 38.88, "lon": -77.06}
        wl = {"type": "icao", "values": {"abc123", "def456"}}
        result = matches_watchlist(ac, wl, self.LOC)
        assert result is not None
        assert result["reason"] == "icao_match"
        assert "distance_km" in result

    def test_icao_no_match(self):
        ac = {"hex": "zzz999", "lat": 38.88, "lon": -77.06}
        wl = {"type": "icao", "values": {"abc123"}}
        assert matches_watchlist(ac, wl, self.LOC) is None

    def test_icao_case_insensitive(self):
        ac = {"hex": "ABC123", "lat": 38.88, "lon": -77.06}
        wl = {"type": "icao", "values": {"abc123"}}
        result = matches_watchlist(ac, wl, self.LOC)
        assert result is not None

    def test_icao_no_position(self):
        ac = {"hex": "abc123"}
        wl = {"type": "icao", "values": {"abc123"}}
        assert matches_watchlist(ac, wl, self.LOC) is None

    def test_icao_csv_match(self):
        ac = {"hex": "ae07e1", "lat": 38.88, "lon": -77.06}
        db = {"ae07e1": {"Operator": "USAF"}}
        wl = {"type": "icao_csv", "db": db}
        result = matches_watchlist(ac, wl, self.LOC)
        assert result is not None
        assert result["reason"] == "icao_csv_match"
        assert result["info"]["Operator"] == "USAF"
        assert "distance_km" in result

    def test_icao_csv_no_match(self):
        ac = {"hex": "zzz999", "lat": 38.88, "lon": -77.06}
        wl = {"type": "icao_csv", "db": {"ae07e1": {}}}
        assert matches_watchlist(ac, wl, self.LOC) is None

    def test_all_match(self):
        ac = {"hex": "abc123", "lat": 38.88, "lon": -77.06}
        wl = {"type": "all"}
        result = matches_watchlist(ac, wl, self.LOC)
        assert result is not None
        assert result["reason"] == "all"
        assert "distance_km" in result

    def test_all_too_far(self):
        ac = {"hex": "abc123", "lat": 50.0, "lon": 0.0}
        wl = {"type": "all"}
        assert matches_watchlist(ac, wl, self.LOC) is None

    def test_all_no_position(self):
        ac = {"hex": "abc123"}
        wl = {"type": "all"}
        assert matches_watchlist(ac, wl, self.LOC) is None

    def test_proximity_match(self):
        # Aircraft very close to location
        ac = {"hex": "abc123", "lat": 38.88, "lon": -77.06, "alt_baro": 5000}
        wl = {
            "type": "proximity",
            "min_altitude_ft": 0,
            "max_altitude_ft": 10000,
        }
        result = matches_watchlist(ac, wl, self.LOC)
        assert result is not None
        assert result["reason"] == "proximity"
        assert "distance_km" in result

    def test_proximity_too_far(self):
        # Aircraft far away
        ac = {"hex": "abc123", "lat": 50.0, "lon": 0.0, "alt_baro": 5000}
        wl = {
            "type": "proximity",
            "min_altitude_ft": 0,
            "max_altitude_ft": 10000,
        }
        assert matches_watchlist(ac, wl, self.LOC) is None

    def test_proximity_too_high(self):
        ac = {"hex": "abc123", "lat": 38.88, "lon": -77.06, "alt_baro": 50000}
        wl = {
            "type": "proximity",
            "min_altitude_ft": 0,
            "max_altitude_ft": 10000,
        }
        assert matches_watchlist(ac, wl, self.LOC) is None

    def test_proximity_too_low(self):
        ac = {"hex": "abc123", "lat": 38.88, "lon": -77.06, "alt_baro": 100}
        wl = {
            "type": "proximity",
            "min_altitude_ft": 500,
            "max_altitude_ft": 10000,
        }
        assert matches_watchlist(ac, wl, self.LOC) is None

    def test_proximity_no_position(self):
        ac = {"hex": "abc123", "alt_baro": 5000}
        wl = {"type": "proximity"}
        assert matches_watchlist(ac, wl, self.LOC) is None

    def test_proximity_ground_string_alt(self):
        ac = {"hex": "abc123", "lat": 38.88, "lon": -77.06, "alt_baro": "ground"}
        wl = {
            "type": "proximity",
            "min_altitude_ft": 0,
            "max_altitude_ft": 10000,
        }
        assert matches_watchlist(ac, wl, self.LOC) is None

    def test_proximity_no_alt_limits(self):
        ac = {"hex": "abc123", "lat": 38.88, "lon": -77.06, "alt_baro": 50000}
        wl = {"type": "proximity"}
        result = matches_watchlist(ac, wl, self.LOC)
        assert result is not None

    def test_unknown_type(self):
        ac = {"hex": "abc123"}
        wl = {"type": "bananas"}
        assert matches_watchlist(ac, wl, self.LOC) is None
