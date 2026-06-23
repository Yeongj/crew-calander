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
    3.  **Enrich:** Fetches flight schedule data from the Taiwan TDX Transport Data API to enrich parsed flights with departure/arrival airports and times.
    4.  **Export:** A parsed roster preview is displayed in the app, ready for calendar export.

---

## 🛠️ Features

*   **Roster Screenshot Parsing:** Uses computer vision (Canny edge detection, Hough transform) to detect the calendar grid structure, then OCRs each cell individually.
*   **Duty & Flight Recognition:**
    *   **Flight Duties:** Parses flight numbers and aircraft codes (e.g., `B77A`, `B78N`, `A333`).
    *   **Off Duties:** Recognizes `DO` (Day Off) and `LO` (Leave/Off-duty).
    *   **Standby/Reserve:** Detects standby shifts like `SBE`, `SBD`, `S06`.
*   **Flight Schedule Enrichment:** Automatically fetches EVA Air (`BR`) international flight schedules from the [TDX Transport Data API](https://tdx.transportdata.tw) and stores them in a local SQLite database for fast lookup.
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
   cp .env.example .env
   # Edit .env and add your CLIENT_ID and CLIENT_SECRET from https://tdx.transportdata.tw
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
│                            #   - Roster cell parsing
├── get_flight_info.py       # TDX API client for flight schedule data
│                            #   - OAuth2 authentication
│                            #   - Paginated API fetching
│                            #   - SQLite storage with weekday expansion
├── cron_monthly_update.py   # Standalone cron script for monthly data refresh
├── flight_info.db           # Local SQLite database (auto-created)
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

### Phase 2: Calendar Generation & Enrichment 🔄
- Map extracted dates to complete datetime structures.
- Integrate with the TDX Transport Data API for EVA Air flight schedules.
- Store flight schedules in SQLite with weekday-based expansion.
- Generate `.ics` files using Python's `icalendar` or `ics` library.

### Phase 3: Interactive Web/Desktop UI 💻
- Build a Streamlit web interface (in progress) allowing crew members to:
  - Upload screenshots.
  - Preview extracted calendar entries.
  - Edit/correct any misparsed flights or times.
  - Click "Export to Calendar" to download the `.ics` file.

### Phase 4: API Integration 🔗
- Support direct sync with Google Calendar API.
- Integrate with Apple Calendar sync.

---

## 📝 License

This project is open-source. See the LICENSE file for details.
