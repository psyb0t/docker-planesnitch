"""Tests for notify.py."""

from .notify import cluster_messages, format_message, format_webhook_payload


class TestClusterMessages:
    def test_empty(self):
        assert cluster_messages([], 100, "\n") == []

    def test_single(self):
        assert cluster_messages(["hello"], 100, "\n") == ["hello"]

    def test_fits_in_one(self):
        msgs = ["aaa", "bbb", "ccc"]
        result = cluster_messages(msgs, 100, "\n")
        assert result == ["aaa\nbbb\nccc"]

    def test_splits_when_needed(self):
        msgs = ["aaa", "bbb", "ccc"]
        # "aaa\nbbb" = 7 chars, adding "\nccc" = 11 > 10
        result = cluster_messages(msgs, 10, "\n")
        assert result == ["aaa\nbbb", "ccc"]

    def test_each_message_own_batch(self):
        msgs = ["aaaa", "bbbb", "cccc"]
        result = cluster_messages(msgs, 4, "\n")
        assert result == ["aaaa", "bbbb", "cccc"]

    def test_custom_separator(self):
        msgs = ["a", "b"]
        result = cluster_messages(msgs, 100, " | ")
        assert result == ["a | b"]

    def test_exact_fit(self):
        msgs = ["aaa", "bbb"]
        result = cluster_messages(msgs, 7, "\n")
        assert result == ["aaa\nbbb"]

    def test_one_over(self):
        msgs = ["aaa", "bbbb"]
        result = cluster_messages(msgs, 7, "\n")
        assert result == ["aaa", "bbbb"]


SAMPLE_AIRCRAFT = {
    "hex": "ae07e1",
    "flight": "TEDDY64 ",
    "r": "94-0067",
    "t": "C17",
    "desc": "BOEING C-17A Globemaster III",
    "ownOp": "USAF",
    "year": "1994",
    "alt_baro": 12350,
    "lat": 37.9306,
    "lon": -78.7019,
    "gs": 413,
    "squawk": "1613",
    "emergency": "none",
    "track": 245.3,
}

SAMPLE_LOCATION = {"lat": 38.8719, "lon": -77.0563}


class TestFormatMessage:
    def test_contains_alert_name(self):
        msg = format_message(
            SAMPLE_AIRCRAFT, "Military", {"reason": "all"}, SAMPLE_LOCATION, "Home"
        )
        assert "Military" in msg

    def test_contains_flight(self):
        msg = format_message(
            SAMPLE_AIRCRAFT, "Test", {"reason": "all"}, SAMPLE_LOCATION, "Home"
        )
        assert "TEDDY64" in msg

    def test_contains_link(self):
        msg = format_message(
            SAMPLE_AIRCRAFT, "Test", {"reason": "all"}, SAMPLE_LOCATION, "Home"
        )
        assert "https://globe.adsb.fi/?icao=ae07e1" in msg

    def test_contains_location_name(self):
        msg = format_message(
            SAMPLE_AIRCRAFT, "Test", {"reason": "all"}, SAMPLE_LOCATION, "The Pentagon"
        )
        assert "The Pentagon" in msg

    def test_squawk_reason_shows_squawk(self):
        msg = format_message(
            SAMPLE_AIRCRAFT,
            "Emergency",
            {"reason": "squawk", "squawk": "7700"},
            SAMPLE_LOCATION,
            "Home",
        )
        assert "7700" in msg
        assert "EMERGENCY" in msg

    def test_squawk_field_shown_when_not_reason(self):
        msg = format_message(
            SAMPLE_AIRCRAFT, "Test", {"reason": "all"}, SAMPLE_LOCATION, "Home"
        )
        assert "1613" in msg

    def test_squawk_field_not_duplicated_when_reason(self):
        ac = {**SAMPLE_AIRCRAFT, "squawk": "7700"}
        msg = format_message(
            ac,
            "Emergency",
            {"reason": "squawk", "squawk": "7700"},
            SAMPLE_LOCATION,
            "Home",
        )
        # squawk should appear in the reason line but not in the extra squawk line
        lines = msg.split("\n")
        squawk_lines = [l for l in lines if "7700" in l]
        assert len(squawk_lines) == 1

    def test_csv_info(self):
        match = {
            "reason": "icao_csv_match",
            "info": {"Operator": "USAF", "Category": "Military"},
        }
        msg = format_message(
            SAMPLE_AIRCRAFT, "Test", match, SAMPLE_LOCATION, "Home"
        )
        assert "USAF" in msg

    def test_aviation_units(self):
        msg = format_message(
            SAMPLE_AIRCRAFT,
            "Test",
            {"reason": "all"},
            SAMPLE_LOCATION,
            "Home",
            display_units="aviation",
        )
        assert "ft" in msg
        assert "kts" in msg
        assert "nm" in msg

    def test_metric_units(self):
        msg = format_message(
            SAMPLE_AIRCRAFT,
            "Test",
            {"reason": "all"},
            SAMPLE_LOCATION,
            "Home",
            display_units="metric",
        )
        assert " m" in msg
        assert "km/h" in msg
        assert "km" in msg

    def test_imperial_units(self):
        msg = format_message(
            SAMPLE_AIRCRAFT,
            "Test",
            {"reason": "all"},
            SAMPLE_LOCATION,
            "Home",
            display_units="imperial",
        )
        assert "ft" in msg
        assert "mph" in msg
        assert "mi" in msg

    def test_no_position(self):
        ac = {"hex": "abc123", "flight": "TEST"}
        msg = format_message(ac, "Test", {"reason": "all"}, SAMPLE_LOCATION, "Home")
        assert "abc123" in msg

    def test_ground_alt_skipped(self):
        ac = {**SAMPLE_AIRCRAFT, "alt_baro": "ground"}
        msg = format_message(
            ac, "Test", {"reason": "all"}, SAMPLE_LOCATION, "Home"
        )
        assert "ground" not in msg

    def test_desc_preferred_over_type(self):
        msg = format_message(
            SAMPLE_AIRCRAFT, "Test", {"reason": "all"}, SAMPLE_LOCATION, "Home"
        )
        assert "BOEING C-17A Globemaster III" in msg
        # Should not show raw type code when desc is present
        lines = [l for l in msg.split("\n") if "C17" in l and "BOEING" not in l]
        assert len(lines) == 0

    def test_type_fallback_when_no_desc(self):
        ac = {**SAMPLE_AIRCRAFT, "desc": ""}
        msg = format_message(
            ac, "Test", {"reason": "all"}, SAMPLE_LOCATION, "Home"
        )
        assert "C17" in msg


class TestFormatWebhookPayload:
    def test_structure(self):
        match = {"reason": "all"}
        p = format_webhook_payload(
            SAMPLE_AIRCRAFT, "Test", match, SAMPLE_LOCATION, "Home"
        )
        assert p["alert"] == "Test"
        assert p["location"] == "Home"
        assert p["match"] is match
        assert "units" in p
        assert "aircraft" in p

    def test_aircraft_fields(self):
        p = format_webhook_payload(
            SAMPLE_AIRCRAFT, "Test", {"reason": "all"}, SAMPLE_LOCATION, "Home"
        )
        ac = p["aircraft"]
        assert ac["hex"] == "ae07e1"
        assert ac["flight"] == "TEDDY64"
        assert ac["registration"] == "94-0067"
        assert ac["type"] == "C17"
        assert ac["description"] == "BOEING C-17A Globemaster III"
        assert ac["owner_operator"] == "USAF"
        assert ac["year"] == "1994"
        assert ac["squawk"] == "1613"
        assert ac["emergency"] == "none"
        assert ac["track"] == 245.3

    def test_aviation_units(self):
        p = format_webhook_payload(
            SAMPLE_AIRCRAFT,
            "Test",
            {"reason": "all"},
            SAMPLE_LOCATION,
            "Home",
            display_units="aviation",
        )
        assert p["units"] == {"altitude": "ft", "distance": "nm", "speed": "kts"}
        ac = p["aircraft"]
        assert ac["altitude"] == 12350
        assert ac["speed"] == 413.0
        assert ac["distance"] is not None

    def test_metric_units(self):
        p = format_webhook_payload(
            SAMPLE_AIRCRAFT,
            "Test",
            {"reason": "all"},
            SAMPLE_LOCATION,
            "Home",
            display_units="metric",
        )
        assert p["units"]["altitude"] == "m"
        ac = p["aircraft"]
        # 12350 ft * 0.3048 = 3764.3 m
        assert ac["altitude"] == 3764.3
        # 413 kts * 1.852 = 764.9 km/h
        assert ac["speed"] == 764.9

    def test_imperial_units(self):
        p = format_webhook_payload(
            SAMPLE_AIRCRAFT,
            "Test",
            {"reason": "all"},
            SAMPLE_LOCATION,
            "Home",
            display_units="imperial",
        )
        assert p["units"]["distance"] == "mi"
        ac = p["aircraft"]
        assert ac["altitude"] == 12350  # ft stays ft in imperial

    def test_no_position(self):
        ac = {"hex": "abc123"}
        p = format_webhook_payload(
            ac, "Test", {"reason": "all"}, SAMPLE_LOCATION, "Home"
        )
        assert p["aircraft"]["altitude"] is None
        assert p["aircraft"]["speed"] is None
        assert p["aircraft"]["distance"] is None

    def test_ground_alt(self):
        ac = {**SAMPLE_AIRCRAFT, "alt_baro": "ground"}
        p = format_webhook_payload(
            ac, "Test", {"reason": "all"}, SAMPLE_LOCATION, "Home"
        )
        assert p["aircraft"]["altitude"] is None

    def test_flight_stripped(self):
        p = format_webhook_payload(
            SAMPLE_AIRCRAFT, "Test", {"reason": "all"}, SAMPLE_LOCATION, "Home"
        )
        assert p["aircraft"]["flight"] == "TEDDY64"
