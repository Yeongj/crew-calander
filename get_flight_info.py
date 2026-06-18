'''
https://tdx.transportdata.tw/api-service/swagger/basic/eb87998f-2f9c-4592-8d75-c62e5b724962#/Air/AirApi_International_2018
filter: AirlineID eq 'BR' and date(ScheduleStartDate) ge 2026-05-29 and date(ScheduleStartDate) lt 2026-06-29
filter: AirlineID eq 'BR' and ScheduleStartDate ge 2026-05-29T00:00:00+08:00 and ScheduleStartDate lt 2026-06-29T00:00:00+08:00

reference: https://github.com/tdxmotc/SampleCode
use this api /v2/Air/GeneralSchedule/International to get flight schedule for the month,
and create a mapping table for date to flight info,
start date and time, end date and time, flight number, departure airport, arrival airport, etc.

this mapping table update monthly? not sure yet, but can be update at the end of each month.
'''

import os
from dotenv import load_dotenv
import requests
import json
import sqlite3
from datetime import datetime, timedelta

env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
load_dotenv(dotenv_path=env_path)

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")

def get_next_month_start_end_dates():
    # Calculate dates for the filter to get the next month's data
    today = datetime.now()

    # Calculate the first day of the current month
    first_day_current_month = today.replace(day=1)

    # Calculate the first day of the next month
    next_month_start_date = (first_day_current_month + timedelta(days=31)).replace(day=1)

    # Calculate the first day of the month after the next month (exclusive end date for filter)
    month_after_next_start_date = (next_month_start_date + timedelta(days=31)).replace(day=1)

    # Format dates for the API filter
    start_date_filter = next_month_start_date.strftime("%Y-%m-%dT00:00:00+08:00")
    end_date_filter = month_after_next_start_date.strftime("%Y-%m-%dT00:00:00+08:00")

    return start_date_filter, end_date_filter

'''
curl --request POST \
     --url 'https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token' \
     --header 'content-type: application/x-www-form-urlencoded' \
     --data grant_type=client_credentials \
     --data client_id=YOUR_CLIENT_ID \
     --data client_secret=YOUR_CLIENT_SECRET \
'''
def get_access_token():
    url = "https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token"
    headers = {
        "content-type": "application/x-www-form-urlencoded"
    }
    data = {
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET
    }

    # response should looks like this:
    # {
    #     "access_token": "eyJh...",
    #     "expires_in": 86400,
    #     "token_type": "Bearer",
    #     (...省略其他內容)
    # }
    response = requests.post(url, headers=headers, data=data)
    # error handling
    if response.status_code != 200:
        print(f"Failed to get access token. Status code: {response.status_code}, Response: {response.text}")
        return None
    # print(f"Access token response: {response.status_code} {response.text}")
    return response.json().get("access_token")

'''
curl --request GET \
     --url TDX_API_URI /v2/Air/GeneralSchedule/International \
     --header 'authorization: Bearer ACCESS_TOKEN'
'''
def get_flight_info():
    access_token = get_access_token()
    if not access_token:
        return None, 0, None, None

    url = "https://tdx.transportdata.tw/api/basic/v2/Air/GeneralSchedule/International"
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {access_token}",
        "Accept-Encoding": "gzip"
    }

    all_flight_data = []
    top = os.getenv("API_DATA_BATCH_SIZE")
    skip = 0

    start_date_filter, end_date_filter = get_next_month_start_end_dates()

    while True:
        params = {
            "$filter": f"AirlineID eq 'BR' and ScheduleStartDate ge {start_date_filter} and ScheduleStartDate lt {end_date_filter}",
            "$format": "JSON",
            "$orderby": "FlightNumber",
            "$top": str(top),
            "$skip": str(skip),
            "health": "false"
        }

        # the sample response is in file response_1780030093291.json
        response = requests.get(url, headers=headers, params=params)

        if response.status_code == 200:
            try:
                data = response.json()
                if not data:
                    break
                all_flight_data.extend(data)
                # If we received fewer items than requested, we've reached the end
                if len(data) < top:
                    break
                skip += top
            except Exception as e:
                print(f"Error parsing JSON at skip {skip}: {e}")
                break
        else:
            print(f"Failed to retrieve flight information at skip {skip}. Status code: {response.status_code}")
            break

    # Extract year and month from the start date filter for the return values
    dt = datetime.strptime(start_date_filter.split('T')[0], "%Y-%m-%d")
    target_year, target_month = dt.year, dt.month

    return all_flight_data, len(all_flight_data), target_year, target_month

'''
parse the flight info and store each individual flight instance in a SQLite database.
Each entry from the API represents a schedule for a period, so this function expands
those schedules into concrete daily flight records.
'''
def parse_flight_info_and_store(flight_data, year, month):
    conn = sqlite3.connect("./flight_info.db")
    cursor = conn.cursor()

    table_name = f"flight_schedules_{year}_{month:02d}"

    # Create table with a composite primary key to allow multiple flights per day
    cursor.execute(f'''CREATE TABLE IF NOT EXISTS {table_name} (
                        flight_date TEXT NOT NULL,
                        flight_number TEXT NOT NULL,
                        departure_airport TEXT,
                        arrival_airport TEXT,
                        departure_time TEXT NOT NULL,
                        arrival_time TEXT,
                        schedule_start_period TEXT,
                        schedule_end_period TEXT,
                        PRIMARY KEY (flight_date, flight_number, departure_time)
                    )''')

    weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    for flight_schedule_entry in flight_data:
        schedule_start = flight_schedule_entry.get("ScheduleStartDate")
        schedule_end = flight_schedule_entry.get("ScheduleEndDate")

        start_date = datetime.strptime(schedule_start, "%Y-%m-%d").date()
        end_date = datetime.strptime(schedule_end, "%Y-%m-%d").date()

        current_date = start_date
        while current_date <= end_date:
            day_of_week_index = current_date.weekday() # Monday is 0, Sunday is 6
            weekday_name = weekdays[day_of_week_index]

            if flight_schedule_entry.get(weekday_name):
                # This flight operates on current_date
                flight_number = flight_schedule_entry.get("FlightNumber")
                departure_airport = flight_schedule_entry.get("DepartureAirportID")
                arrival_airport = flight_schedule_entry.get("ArrivalAirportID")
                departure_time = flight_schedule_entry.get("DepartureTime")
                arrival_time = flight_schedule_entry.get("ArrivalTime")

                cursor.execute(f'''INSERT OR REPLACE INTO {table_name} VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                               (current_date.isoformat(),
                                flight_number,
                                departure_airport,
                                arrival_airport,
                                departure_time,
                                arrival_time,
                                schedule_start,
                                schedule_end))
            current_date += timedelta(days=1)
    conn.commit()
    conn.close()

if __name__ == "__main__":
    # flight_data, total_records, year, month = get_flight_info()
    # # write to file
    # with open("response_example.json", "w") as f:
    #     json.dump(flight_data, f)
    # read from file

    with open("api_response_sample/response_example.json", "r") as f:
        flight_data = json.load(f)
    year = 2026 # Assuming the example data is for June 2026
    month = 6   # Assuming the example data is for June 2026
    parse_flight_info_and_store(flight_data, year, month)
