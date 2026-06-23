# AGENTS.md — Crew Roster to Calendar

## Overview
Streamlit app that parses crew roster screenshots via OCR + computer vision, enriches flight data from TDX API, and exports `.ics` for iOS/Android.

## Stack
- **OCR**: RapidOCR (ONNX runtime, not Gemini/LLM)
- **Grid detection**: scikit-image (Canny edge + Hough transform)
- **DB**: SQLite (`flight_info.db`), tables named `flight_schedules_{year}_{month}`
- **API**: Taiwan TDX Transport Data API (OAuth2)
- **Scheduler**: APScheduler (27th of month at 10:00)
- **No `icalendar` dependency** — ICS generated manually with f-strings

## Key Files

| File | Role |
|---|---|
| `app.py` | Streamlit entry point; scheduler, file upload, download button, debug expander |
| `process_image.py` | OCR pipeline, grid detection, cell parsing, DB enrichment |
| `generate_ics.py` | Manual ICS generation (`roster_to_ics`) |
| `get_flight_info.py` | TDX API client, `lookup_flight_info()`, DB creation |
| `cron_monthly_update.py` | Standalone alternative to APScheduler |

## Core patterns & conventions

### Flight number normalisation
- All-digit OCR (e.g. `"71"`) → `f"BR{raw.zfill(3)}"` → `"BR071"`
- Airline-prefixed (e.g. `"B7187"`) → kept as-is (`"B7187"`)
- Flight marker regex: `^\d+$|^[A-Za-z]\d{4,}$`

### Cell parsing flow (`parse_roster_cells`)
1. Extract date from `(N)` or `N` prefix
2. Pop shared aircraft if last element matches `^[A-Za-z]\d{2,3}[A-Za-z]?$`
3. Merge short fragments (≤3 chars) into preceding time-containing element
4. Split into duty groups at each flight marker
5. For each group: first element = duty; remaining → classify as aircraft / note / time / duty qualifier
6. BR flights enriched via `lookup_flight_info(flight_date, duty)`

### Duty qualifier appending
Text elements before the first time-like element (`:` or `\d{1,2}:\d{2}`) are appended to duty name (e.g. `Q05` + `SCS(TSA)` → `"Q05 SCS(TSA)"`).

### Note extraction
Standalone `(...)` elements matched by `^\([^)]+\)$` become the `note` field (e.g. `(DP1)`).

### ICS branching (`roster_to_ics`)
1. `_FLIGHT_DUTY.match(duty) + departure_time` → timed flight VEVENT (DB-enriched)
2. `_FLIGHT_DUTY.match(duty)` → all-day flight VEVENT (no DB data)
3. `entry.get("time")` → standby VEVENT with time range
4. `_FLIGHT_DUTY` regex: `^(?:BR\d{3,}|[A-Za-z]\d{4,})$`

### Time parsing leniency
`_parse_time_part` uses regex, right-pads single-digit minutes with `'0'` (OCR garbled as `"5A"` → `"5"` → `"50"`). Overnight `+1` in arrival_time handled by `timedelta(days=plus_days)`.

### Multi-flight days
Cell with multiple all-digit elements (e.g. `['12', '19', 'B77A']`) splits into two duty groups sharing the same aircraft.

### Codeshare flights
`B7`-prefixed flight numbers (Uni Air) → kept as-is, all-day events in ICS.

### Standby duties
Codes like `H04 SCS`, `SBE LHS`, `Q05 SCS(TSA)` with a `time` field become timed VEVENT events.

## DB notes
- Tables may not exist for a given month/year; `check_and_fetch_flight_info()` is called on startup and in `main()`
- Flight numbers stored as `"BR071"`, queried by `flight_date + flight_number`
- Only EVA Air (`BR`) international schedules fetched; other airlines not enriched

## Running
```bash
uv run streamlit run app.py
```

## Tests
No formal test framework. Verify by running against `screenshots/example_02.jpg` and `screenshots/example_03.jpg`.
