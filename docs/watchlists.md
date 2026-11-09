---
title: "Watchlists"
description: "The six planesnitch watchlist types, from emergency squawks and ICAO hex lists to plane-alert-db CSVs and low-flyer altitude filters, and how matching works."
nav_order: 4
---

# Watchlists

A watchlist says what to snitch on. [Alert rules](configuration.md#alerts) point at watchlists by name, and a rule fires when an aircraft inside a location's radius matches one of them.

Every type respects the location's radius first. An aircraft outside it never matches, and neither does one that reports no position.

## Types

| `type` | Matches | Keys |
| --- | --- | --- |
| `all` | Every aircraft in range | none |
| `squawk` | Transponder code | `values`: list of codes |
| `icao` | ICAO hex address | `values`: list of hex codes, any case |
| `icao_type` | ICAO type designator from [Doc 8643](https://www.icao.int/publications/DOC8643/Pages/Search.aspx), such as `C17` or `B738` | `values`: list of designators, any case |
| `icao_csv` | ICAO hex listed in a CSV file | `source`: file name inside the CSV directory |
| `proximity` | Altitude band | `min_altitude`, `max_altitude`: both optional |

An unknown `type` is skipped with `unknown watchlist type ... for ...` in the log.

```yaml
watchlists:
  # The panic buttons
  emergencies:
    type: squawk
    values: ["7500", "7600", "7700"]

  # 8,709 military aircraft
  military:
    type: icao_csv
    source: plane-alert-mil.csv

  # Stalk specific aircraft
  my_planes:
    type: icao
    values: ["4ca123", "a12345"]

  # Any A400M, Rafale or Alpha Jet
  cool_jets:
    type: icao_type
    values: ["A400", "RFAL", "AJET"]

  # Every single aircraft in range
  everything:
    type: all

  # What just buzzed my house
  low_flyers:
    type: proximity
    min_altitude: 0ft
    max_altitude: 3000ft
```

Quote squawk codes. Unquoted, YAML reads `0000` as the number `0` and the code never matches.

### Proximity details

`proximity` uses barometric altitude. Aircraft that report `ground` instead of a number never match. Aircraft that report no altitude at all do match, since the altitude limits can't rule them out. Leave both limits out and it behaves like `all`.

`icao_type` needs the type field, which the enriched sources fill in. See [sources](configuration.md#sources).

## CSV watchlists and plane-alert-db

`icao_csv` reads a CSV from the CSV directory (`/csv` in the container, or `PLANESNITCH_CSV_DIR`). The first column must be the ICAO hex. Every other column is copied into the alert as `info`, and its column name has any leading `$` or `#` stripped.

The community-curated [sdr-enthusiasts/plane-alert-db](https://github.com/sdr-enthusiasts/plane-alert-db) lists use that format:

| List | Count | File |
| --- | --- | --- |
| Military | 8,709 | [`plane-alert-mil.csv`](https://github.com/sdr-enthusiasts/plane-alert-db/blob/main/plane-alert-mil.csv) |
| Government | 1,743 | [`plane-alert-gov.csv`](https://github.com/sdr-enthusiasts/plane-alert-db/blob/main/plane-alert-gov.csv) |
| Police | 932 | [`plane-alert-pol.csv`](https://github.com/sdr-enthusiasts/plane-alert-db/blob/main/plane-alert-pol.csv) |
| Civilian | 4,530 | [`plane-alert-civ.csv`](https://github.com/sdr-enthusiasts/plane-alert-db/blob/main/plane-alert-civ.csv) |
| Privacy (PIA) | 94 | [`plane-alert-pia.csv`](https://github.com/sdr-enthusiasts/plane-alert-db/blob/main/plane-alert-pia.csv) |
| Everything | 15,914 | [`plane-alert-db.csv`](https://github.com/sdr-enthusiasts/plane-alert-db/blob/main/plane-alert-db.csv) |

The counts drift as the project updates its lists. `plane-alert-db.csv` holds all the others in one file.

```bash
mkdir -p csv
BASE=https://raw.githubusercontent.com/sdr-enthusiasts/plane-alert-db/main
for list in mil gov pol civ pia; do
  curl -sLo "csv/plane-alert-$list.csv" "$BASE/plane-alert-$list.csv"
done
curl -sLo csv/plane-alert-db.csv "$BASE/plane-alert-db.csv"
```

planesnitch reads the CSVs at startup, whenever the config changes, and again every 24 hours, so re-downloading them is enough to pick up new data within a day. A file that can't be read logs `failed to load watchlist <name>` and that watchlist matches nothing until a later reload succeeds.

Write your own CSV the same way: a header row, the hex in the first column, anything you like after it.

```text
icao,Operator,Note
ae07e1,USAF,the C-17 that keeps circling
```
