# ✈️ Crew Roster to Calendar (`crew-calander`)

`crew-calander` is a smart utility designed for Airline flight crew (flight attendants) to automatically convert screenshots of their monthly crew roster app into standard calendar events. Instead of manually entering each flight, standby duty, or day off into Apple Calendar or Google Calendar, crew members can simply upload a screenshot of their monthly calendar, and `crew-calander` handles the rest.

---

## 📸 The Problem & The Solution

Crew members use a dedicated mobile application to view their monthly schedules. The schedules are displayed in a monthly calendar view.

### Manual Entry vs. `crew-calander`
*   **Manual Entry:** Manually typing flight numbers, check-in times, aircraft types (e.g., `B77A`, `B78N`, `A333`), standby blocks, and rest days is tedious, error-prone, and slow.
*   **`crew-calander` Solution:**
    1.  **Capture:** Take a screenshot of the monthly schedule in the Crew App.
    2.  **Parse:** `crew-calander` uses OCR (RapidOCR) and computer vision (scikit-image) to detect the calendar grid and extract text from each cell in the screenshot.
    3.  **Enrich:** Fetches EVA Air (`BR`) flight schedule data from the Taiwan TDX Transport Data API to enrich parsed flights with departure/arrival airports and times.
    4.  **Export:** Download a single `.ics` file compatible with both iOS and Android calendars.

---

## 🛠️ Features

*   **Roster Screenshot Parsing:** Uses computer vision (Canny edge detection, Hough transform) to detect the calendar grid structure, then OCRs each cell individually.
*   **Duty & Flight Recognition:**
    *   **Flight Duties:** Parses flight numbers and aircraft codes (e.g., `B77A`, `B78N`, `A333`); supports multi-flight days sharing one aircraft.
    *   **Codeshare Flights:** Detects other-airline prefixes (e.g., `B7` Uni Air) and exports them as all-day events.
    *   **Off Duties:** Recognizes `DO` (Day Off), `LO` (Leave/Off-duty), `ADO`, `AL`, `L5`.
    *   **Standby/Reserve:** Detects standby shifts like `SCS`, `LCS`, `LHS`, `SBE`, `SBD`, `S06` with time ranges.
    *   **Duty Qualifiers:** Combines multi-token duty codes (e.g., `Q05 SCS(TSA)`) and extracts parenthetical notes (e.g., `(DP1)`).
*   **Flight Schedule Enrichment:** Automatically fetches EVA Air (`BR`) international flight schedules from the [TDX Transport Data API](https://tdx.transportdata.tw) and stores them in a local SQLite database for fast lookup.
*   **Timezone-Aware Calendar Events:** Anchors all events in TPE time using a UTC offset table (57 airports). Flights departing from TPE anchor DTSTART at TPE departure time; flights arriving into TPE anchor DTEND at TPE arrival time and calculate the departure backwards — ensuring accurate flight duration in calendar blocks.
*   **Cell Merging & Normalization:** Short OCR fragments (≤3 chars) are merged into preceding time elements; garbled times like `08:5A` are right-padded to `08:50`; parenthetical notes like `(DP1)` are extracted into the event description.
*   **Automated Monthly Updates:** APScheduler runs a background job on the 27th of each month to pre-fetch the next month's flight schedule.
*   **Crew-Centric UI:** Streamlit-based web interface to upload screenshots, preview parsed entries, and export.

---

## 🚀 Getting Started

This project is built using **Python 3.13** and managed with **`uv`** for lightning-fast package management.

### Prerequisites

Make sure you have `uv` installed. If not, install it via:

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd crew-calander
   ```

2. Set up environment variables for the TDX API:
   ```bash
   # Create a .env file with your TDX API credentials from https://tdx.transportdata.tw
   echo "CLIENT_ID=your_client_id_here" > .env
   echo "CLIENT_SECRET=your_client_secret_here" >> .env
   ```

3. Sync the dependencies and virtual environment:
   ```bash
   uv sync
   ```

### Running the App

To run the application locally:

```bash
uv run streamlit run app.py
```

---

## 🗺️ Project Structure

```
crew-calander/
├── app.py                   # Streamlit web application (entry point)
├── process_image.py         # OCR & computer vision pipeline
│                            #   - Grid detection via Canny + Hough transform
│                            #   - Per-cell OCR via RapidOCR
│                            #   - Roster cell parsing (multi-duty, qualifier merging)
├── generate_ics.py          # Manual .ics generation (no external library)
│                            #   - AIRPORT_OFFSETS dict for UTC-to-local conversion
│                            #   - TPE-anchored DTSTART / DTEND via flight duration
├── get_flight_info.py       # TDX API client for flight schedule data
│                            #   - OAuth2 authentication
│                            #   - Paginated API fetching
│                            #   - SQLite storage with weekday expansion
├── cron_monthly_update.py   # Standalone cron script (alternative to APScheduler in app.py)
├── flight_info.db           # Local SQLite database (auto-created on demand)
├── screenshots/             # Example roster screenshots
├── .env                     # TDX API credentials (not tracked)
├── pyproject.toml           # Project dependencies
└── uv.lock                  # Lockfile
```

## 🗺️ Development Roadmap

### Phase 1: Core Parsing & Extraction ✅
- Integrate RapidOCR for text extraction from roster screenshots.
- Implement Canny edge detection + Hough transform to detect calendar grid lines.
- Parse common crew duty codes (`DO`, `LO`, `SBE`, `SBD`, `SCS`, etc.).
- Parse flight details: Flight numbers, aircraft types.

### Phase 2: Calendar Generation & Enrichment ✅
- Map extracted dates to complete datetime structures.
- Integrate with the TDX Transport Data API for EVA Air flight schedules.
- Store flight schedules in SQLite with weekday-based expansion.
- Generate `.ics` files manually (no external library) with timed/all-day/standby event types.

### Phase 3: Interactive Web/Desktop UI ✅
- Streamlit web interface allowing crew members to:
  - Upload roster screenshots.
  - View parsed entries in a collapsible debug view.
  - Download a single `.ics` file compatible with iOS and Android.

### Phase 4: API Integration 🔗
- Support direct sync with Google Calendar API.
- Integrate with Apple Calendar sync.

---

## 📝 License

This project is open-source. See the LICENSE file for details.
