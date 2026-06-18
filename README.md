# ✈️ Crew Roster to Calendar (`crew-calander`)

`crew-calander` is a smart utility designed for Airline flight crew (flight attendants) to automatically convert screenshots of their monthly crew roster app into standard calendar events. Instead of manually entering each flight, standby duty, or day off into Apple Calendar or Google Calendar, crew members can simply upload a screenshot of their monthly calendar, and `crew-calander` handles the rest.

---

## 📸 The Problem & The Solution

Crew members use a dedicated mobile application to view their monthly schedules. The schedules are displayed in a monthly calendar view (as shown below).

<div align="center">
  <img src="B42AB0C7-C83B-433D-9086-72F5091FA49E.jpg" alt="Crew App Screenshot Example" width="350"/>
</div>

### Manual Entry vs. `crew-calander`
*   **Manual Entry:** Manually typing flight numbers, check-in times, aircraft types (e.g., `B77A`, `B78N`, `A333`), standby blocks, and rest days is tedious, error-prone, and slow.
*   **`crew-calander` Solution:**
    1.  **Capture:** Take a screenshot of the monthly schedule in the Crew App.
    2.  **Parse:** `crew-calander` uses Vision LLMs (e.g., Google Gemini) or OCR technology to parse the calendar grid from the screenshot.
    3.  **Generate:** The extracted duty codes, flight numbers, aircraft types, and off-duty events are mapped to precise times and descriptions.
    4.  **Export:** A standard `.ics` (iCalendar) file is generated, which can be instantly imported into Apple Calendar, Google Calendar, Microsoft Outlook, etc.

---

## 🛠️ Features

*   **Roster Screenshot Parsing:** Recognizes grid cells, dates, months, and years from Crew App screenshots.
*   **Duty & Flight Recognition:**
    *   **Flight Duties:** Parses flight numbers (e.g., `217`, `228`, `132`, `391`) and aircraft codes (e.g., `B77A`, `B78N`, `A333`).
    *   **Off Duties:** Recognizes `DO` (Day Off) and `LO` (Leave/Off-duty) as all-day events.
    *   **Standby/Reserve:** Detects standby shifts like `SBE SHS`, `SBD SHS`, `S06 SCS`.
*   **Intelligent Schedule Resolution:** Infers departure and arrival times based on known Airline flight numbers or user templates.
*   **Standard Calendar Export:** Generates cross-platform `.ics` files.
*   **Crew-Centric UI/CLI:** Easy-to-use interface to upload screenshots, preview parsed entries, make manual corrections, and download the calendar file.

---

## 🚀 Getting Started

This project is built using **Python 3.13** and managed with **`uv`** for lightning-fast package management.

### Prerequisites

Make sure you have `uv` installed. If not, install it via:

```bash
# macOS/Linux
curl -FsSL https://astral.sh/uv/install.sh | sh
```

### Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd crew-calander
   ```

2. Sync the dependencies and virtual environment:
   ```bash
   uv sync
   ```

### Running the App

To run the application locally:
```bash
uv run main.py
```

---

## 🗺️ Development Roadmap

### Phase 1: Core Parsing & Extraction 🧪
*   Integrate Gemini Vision API (`google-genai` SDK) to analyze roster screenshots and return structured JSON data representing the monthly grid.
*   Implement parsing logic for common crew duty codes (`DO`, `LO`, `SBE`, `SBD`, `SCS`, etc.).
*   Parse flight details: Flight numbers, aircraft types.

### Phase 2: Calendar Generation (`.ics`) 📅
*   Map extracted dates to complete datetime structures (taking into account the month/year shown in the header).
*   Create a flight schedule database or lookup mechanism to enrich flight numbers with standard departure/arrival airports and times.
*   Generate `.ics` files using Python's `icalendar` or `ics` library.

### Phase 3: Interactive Web/Desktop UI 💻
*   Build a sleek, premium web interface (using Gradio, Streamlit, or a Next.js frontend with FastAPI backend) allowing crew members to:
    *   Upload screenshots.
    *   Preview extracted calendar entries in a table or interactive grid.
    *   Edit/correct any misparsed flights or times.
    *   Click "Export to Calendar" to download the `.ics` file.

### Phase 4: API Integration 🔗
*   Support direct sync with Google Calendar API.
*   Integrate with Apple Calendar sync.

---

## 📝 License

This project is open-source. See the LICENSE file for details.
