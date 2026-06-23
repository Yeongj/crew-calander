from datetime import datetime, timedelta
import re

ICS_HEADER = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//crew-calander//EN
CALSCALE:GREGORIAN
METHOD:PUBLISH"""

ICS_FOOTER = "END:VCALENDAR"

_FLIGHT_DUTY = re.compile(r'^(?:BR\d{3,}|[A-Za-z]\d{4,})$')


def _fmt_dt(dt):
    return dt.strftime("%Y%m%dT%H%M%S")


def _fmt_date(d):
    return d.strftime("%Y%m%d")


def _parse_time_part(s):
    m = re.match(r'(\d{1,2}):(\d{0,2})', s.strip())
    if not m:
        return None
    h = int(m.group(1))
    mi_str = m.group(2).ljust(2, '0')[:2]
    mi = int(mi_str)
    if 0 <= h <= 23 and 0 <= mi <= 59:
        return h, mi
    return None


def _parse_time_range(time_str, flight_date):
    parts = time_str.split("-")
    if len(parts) != 2:
        return None, None
    start_str, end_str = parts[0].strip(), parts[1].strip()
    start_part = _parse_time_part(start_str)
    end_part = _parse_time_part(end_str)
    if not start_part or not end_part:
        return None, None
    start = datetime(flight_date.year, flight_date.month, flight_date.day,
                     start_part[0], start_part[1])
    end = datetime(flight_date.year, flight_date.month, flight_date.day,
                   end_part[0], end_part[1])
    if end <= start:
        end += timedelta(days=1)
    return start, end


def _parse_departure_time(t_str):
    m = re.match(r"(\d{2}):(\d{2})", t_str.strip())
    if not m:
        return None
    return int(m.group(1)), int(m.group(2))


def _parse_arrival_time(t_str):
    m = re.match(r"(\d{2}):(\d{2})(?:\+(\d+))?", t_str.strip())
    if not m:
        return None, 0
    return (int(m.group(1)), int(m.group(2))), int(m.group(3) or 0)


def roster_to_ics(parsed_roster):
    events = []
    uid_seq = 0

    for entry in parsed_roster:
        duty = entry.get("duty", "")
        flight_date_str = entry.get("flight_date")
        if not flight_date_str:
            continue
        try:
            flight_date = datetime.strptime(flight_date_str, "%Y-%m-%d")
        except ValueError:
            continue

        if _FLIGHT_DUTY.match(duty) and entry.get("departure_time"):
            dep = _parse_departure_time(entry["departure_time"])
            arr, plus_days = _parse_arrival_time(entry["arrival_time"])
            if not dep or not arr:
                continue
            dep_h, dep_m = dep
            arr_h, arr_m = arr
            dtstart = datetime(flight_date.year, flight_date.month, flight_date.day,
                               dep_h, dep_m)
            dtend = datetime(flight_date.year, flight_date.month, flight_date.day,
                             arr_h, arr_m) + timedelta(days=plus_days)
            if dtend <= dtstart:
                dtend += timedelta(days=1)

            dep_port = entry.get("departure_airport", "")
            arr_port = entry.get("arrival_airport", "")
            route = f" {dep_port}→{arr_port}" if dep_port and arr_port else ""
            summary = f"{duty}{route}"

            aircraft = entry.get("aircraft", "")
            note = entry.get("note", "")
            desc = f"Flight {duty}"
            if aircraft:
                desc += f" ({aircraft})"
            if route:
                desc += f"\n{dep_port} {entry['departure_time']} → {arr_port} {entry['arrival_time']}"
            if note:
                desc += f"\n{note}"

            events.append(f"""BEGIN:VEVENT
UID:{uid_seq:04d}@crew-calander
DTSTART:{_fmt_dt(dtstart)}
DTEND:{_fmt_dt(dtend)}
SUMMARY:{summary}
DESCRIPTION:{desc}
END:VEVENT""")
            uid_seq += 1

        elif _FLIGHT_DUTY.match(duty):
            dtend = flight_date + timedelta(days=1)
            summary = f"Flight {duty}"
            note = entry.get("note", "")
            desc = summary
            if note:
                desc += f"\n{note}"

            events.append(f"""BEGIN:VEVENT
UID:{uid_seq:04d}@crew-calander
DTSTART;VALUE=DATE:{_fmt_date(flight_date)}
DTEND;VALUE=DATE:{_fmt_date(dtend)}
SUMMARY:{summary}
DESCRIPTION:{desc}
END:VEVENT""")
            uid_seq += 1

        elif entry.get("time"):
            t = entry["time"].strip()
            if not t:
                continue
            start, end = _parse_time_range(t, flight_date)
            if not start:
                continue
            summary = f"Standby {duty}"

            note = entry.get("note", "")
            desc = f"{duty} · {t}"
            if note:
                desc += f"\n{note}"

            events.append(f"""BEGIN:VEVENT
UID:{uid_seq:04d}@crew-calander
DTSTART:{_fmt_dt(start)}
DTEND:{_fmt_dt(end)}
SUMMARY:{summary}
DESCRIPTION:{desc}
END:VEVENT""")
            uid_seq += 1

    if not events:
        return ""

    return ICS_HEADER + "\n" + "\n".join(events) + "\n" + ICS_FOOTER + "\n"
