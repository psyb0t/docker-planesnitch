"""Tests for __main__.py."""

import os
import tempfile

from .__main__ import reload_config
from .config import load_config

GOOD = """
locations: {home: {lat: 0, lon: 0, radius: 5km}}
sources: [{type: adsb_one}]
watchlists: {everything: {type: all}}
alerts: [{name: Test, watchlists: [everything], notify: [tg]}]
notifications: {tg: {type: telegram, bot_token: x, chat_id: y}}
"""


def _write(text: str) -> str:
    fd, path = tempfile.mkstemp(suffix=".yaml")
    os.write(fd, text.encode())
    os.close(fd)
    return path


def test_invalid_reload_keeps_the_current_config():
    path = _write(GOOD)
    try:
        current = load_config(path)
        for broken in (GOOD + "display_units: bananas\n", "locations: {}\n", ": ["):
            with open(path, "w") as f:
                f.write(broken)
            assert reload_config(path, current) is current
    finally:
        os.unlink(path)


def test_changed_reload_returns_the_new_config():
    path = _write(GOOD)
    try:
        current = load_config(path)
        assert reload_config(path, current) is current
        with open(path, "w") as f:
            f.write(GOOD + "poll_interval: 2m\n")
        changed = reload_config(path, current)
        assert changed is not current
        assert changed["poll_interval"] == 120
    finally:
        os.unlink(path)
