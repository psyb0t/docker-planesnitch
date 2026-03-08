"""Tests for alerts.py."""

import time

from .alerts import check_alerts


def _make_ac(hex_code, lat=38.88, lon=-77.06, squawk="1234", alt=10000):
    return {
        "hex": hex_code,
        "lat": lat,
        "lon": lon,
        "squawk": squawk,
        "alt_baro": alt,
    }


LOCATIONS = {
    "home": {"lat": 38.8719, "lon": -77.0563},
    "far": {"lat": 50.0, "lon": 0.0},
}

WATCHLISTS = {
    "everything": {"type": "all"},
    "emergencies": {"type": "squawk", "values": {"7500", "7600", "7700"}},
    "my_planes": {"type": "icao", "values": {"abc123"}},
}


class TestCheckAlerts:
    def test_all_match(self):
        aircraft = [_make_ac("aaa111")]
        rules = [
            {"name": "All", "watchlists": ["everything"], "cooldown": 300, "notify": ["tg"]}
        ]
        cooldowns = {}
        result = check_alerts(aircraft, rules, WATCHLISTS, LOCATIONS, cooldowns)
        assert len(result) == 1
        ac, rule, match, loc_name, loc = result[0]
        assert ac["hex"] == "aaa111"
        assert rule["name"] == "All"
        assert match["reason"] == "all"
        assert match["watchlist"] == "everything"

    def test_squawk_match(self):
        aircraft = [_make_ac("aaa111", squawk="7700")]
        rules = [
            {"name": "Emergency", "watchlists": ["emergencies"], "cooldown": 60, "notify": ["tg"]}
        ]
        cooldowns = {}
        result = check_alerts(aircraft, rules, WATCHLISTS, LOCATIONS, cooldowns)
        assert len(result) == 1
        assert result[0][2]["reason"] == "squawk"
        assert result[0][2]["squawk"] == "7700"

    def test_squawk_no_match(self):
        aircraft = [_make_ac("aaa111", squawk="1234")]
        rules = [
            {"name": "Emergency", "watchlists": ["emergencies"], "cooldown": 60, "notify": ["tg"]}
        ]
        result = check_alerts(aircraft, rules, WATCHLISTS, LOCATIONS, {})
        assert len(result) == 0

    def test_icao_match(self):
        aircraft = [_make_ac("abc123")]
        rules = [
            {"name": "My Planes", "watchlists": ["my_planes"], "cooldown": 60, "notify": ["tg"]}
        ]
        result = check_alerts(aircraft, rules, WATCHLISTS, LOCATIONS, {})
        assert len(result) == 1
        assert result[0][2]["reason"] == "icao_match"

    def test_cooldown_blocks(self):
        aircraft = [_make_ac("aaa111")]
        rules = [
            {"name": "All", "watchlists": ["everything"], "cooldown": 300, "notify": ["tg"]}
        ]
        cooldowns = {("All", "aaa111"): time.time()}
        result = check_alerts(aircraft, rules, WATCHLISTS, LOCATIONS, cooldowns)
        assert len(result) == 0

    def test_cooldown_expired(self):
        aircraft = [_make_ac("aaa111")]
        rules = [
            {"name": "All", "watchlists": ["everything"], "cooldown": 300, "notify": ["tg"]}
        ]
        cooldowns = {("All", "aaa111"): time.time() - 301}
        result = check_alerts(aircraft, rules, WATCHLISTS, LOCATIONS, cooldowns)
        assert len(result) == 1

    def test_location_filter(self):
        aircraft = [_make_ac("aaa111")]
        rules = [
            {
                "name": "Home Only",
                "locations": ["home"],
                "watchlists": ["everything"],
                "cooldown": 60,
                "notify": ["tg"],
            }
        ]
        result = check_alerts(aircraft, rules, WATCHLISTS, LOCATIONS, {})
        assert len(result) == 1
        assert result[0][3] == "home"

    def test_location_filter_nonexistent(self):
        aircraft = [_make_ac("aaa111")]
        rules = [
            {
                "name": "Nowhere",
                "locations": ["mars"],
                "watchlists": ["everything"],
                "cooldown": 60,
                "notify": ["tg"],
            }
        ]
        result = check_alerts(aircraft, rules, WATCHLISTS, LOCATIONS, {})
        assert len(result) == 0

    def test_empty_hex_skipped(self):
        aircraft = [{"hex": "", "lat": 38.88, "lon": -77.06}]
        rules = [
            {"name": "All", "watchlists": ["everything"], "cooldown": 60, "notify": ["tg"]}
        ]
        result = check_alerts(aircraft, rules, WATCHLISTS, LOCATIONS, {})
        assert len(result) == 0

    def test_missing_watchlist_skipped(self):
        aircraft = [_make_ac("aaa111")]
        rules = [
            {"name": "Ghost", "watchlists": ["nonexistent"], "cooldown": 60, "notify": ["tg"]}
        ]
        result = check_alerts(aircraft, rules, WATCHLISTS, LOCATIONS, {})
        assert len(result) == 0

    def test_multiple_aircraft(self):
        aircraft = [_make_ac("aaa111"), _make_ac("bbb222")]
        rules = [
            {"name": "All", "watchlists": ["everything"], "cooldown": 60, "notify": ["tg"]}
        ]
        result = check_alerts(aircraft, rules, WATCHLISTS, LOCATIONS, {})
        assert len(result) == 2

    def test_cooldown_cleanup(self):
        aircraft = []
        rules = [
            {"name": "All", "watchlists": ["everything"], "cooldown": 10, "notify": ["tg"]}
        ]
        cooldowns = {("All", "old_plane"): time.time() - 100}
        check_alerts(aircraft, rules, WATCHLISTS, LOCATIONS, cooldowns)
        assert ("All", "old_plane") not in cooldowns

    def test_sets_cooldown(self):
        aircraft = [_make_ac("aaa111")]
        rules = [
            {"name": "All", "watchlists": ["everything"], "cooldown": 300, "notify": ["tg"]}
        ]
        cooldowns = {}
        check_alerts(aircraft, rules, WATCHLISTS, LOCATIONS, cooldowns)
        assert ("All", "aaa111") in cooldowns

    def test_nearest_location_used_for_icao(self):
        # Aircraft near "home", should pick "home" not "far"
        aircraft = [_make_ac("abc123", lat=38.88, lon=-77.06)]
        rules = [
            {"name": "My", "watchlists": ["my_planes"], "cooldown": 60, "notify": ["tg"]}
        ]
        result = check_alerts(aircraft, rules, WATCHLISTS, LOCATIONS, {})
        assert len(result) == 1
        assert result[0][3] == "home"
