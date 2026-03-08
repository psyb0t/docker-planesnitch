"""Alert checking logic."""

import logging
import time
from typing import Any

from .geo import find_nearest_location
from .watchlists import matches_watchlist

log = logging.getLogger("planesnitch")


def check_alerts(
    aircraft_list: list[dict[str, Any]],
    alert_rules: list[dict[str, Any]],
    watchlists: dict[str, dict[str, Any]],
    locations: dict[str, dict[str, Any]],
    cooldowns: dict[tuple[str, str], float],
) -> list[tuple[dict[str, Any], dict[str, Any], dict[str, Any], str, dict[str, Any]]]:
    now = time.time()
    triggered: list[
        tuple[
            dict[str, Any],
            dict[str, Any],
            dict[str, Any],
            str,
            dict[str, Any],
        ]
    ] = []

    for ac in aircraft_list:
        hex_code = ac.get("hex", "").lower()
        if not hex_code:
            continue

        for rule in alert_rules:
            rule_name = rule["name"]
            cooldown_key = (rule_name, hex_code)
            cooldown_sec = rule.get("cooldown", 300)

            last = cooldowns.get(cooldown_key, 0)
            if now - last < cooldown_sec:
                log.debug(
                    "cooldown active for [%s] %s (%.0fs left)",
                    rule_name,
                    hex_code,
                    cooldown_sec - (now - last),
                )
                continue

            rule_locs = locations
            rule_loc_filter = rule.get("locations")
            if rule_loc_filter:
                rule_locs = {n: l for n, l in locations.items() if n in rule_loc_filter}
                if not rule_locs:
                    continue

            matched = False
            for wl_name in rule.get("watchlists", []):
                wl = watchlists.get(wl_name)
                if not wl:
                    continue

                if wl["type"] in ("proximity", "all"):
                    for loc_name, loc in rule_locs.items():
                        match = matches_watchlist(ac, wl, loc)
                        if not match:
                            continue
                        match["watchlist"] = wl_name
                        cooldowns[cooldown_key] = now
                        triggered.append((ac, rule, match, loc_name, loc))
                        matched = True
                        break
                else:
                    nearest = find_nearest_location(ac, rule_locs)
                    if not nearest:
                        continue
                    loc_name, loc = nearest
                    match = matches_watchlist(ac, wl, loc)
                    if not match:
                        continue
                    match["watchlist"] = wl_name
                    cooldowns[cooldown_key] = now
                    triggered.append((ac, rule, match, loc_name, loc))
                    matched = True

                if matched:
                    break

    max_cooldown = max((r.get("cooldown", 300) for r in alert_rules), default=300)
    expired = [k for k, v in cooldowns.items() if now - v > max_cooldown * 2]
    for k in expired:
        log.debug("expiring cooldown: %s", k)
        del cooldowns[k]

    log.debug(
        "check_alerts: %d aircraft, %d triggered, %d active cooldowns",
        len(aircraft_list),
        len(triggered),
        len(cooldowns),
    )
    return triggered
