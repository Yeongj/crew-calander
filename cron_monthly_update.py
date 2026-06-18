# cron job for monthly update of flight info mapping table

from datetime import datetime
from get_flight_info import get_flight_info, parse_flight_info_and_store

def main():
    today = datetime.now()
    # Run only if it's the 27th day of the month
    if today.day == 27:
        print(f"Starting monthly flight data update at {today}")
        flight_data, total_records, year, month = get_flight_info()
        if flight_data:
            parse_flight_info_and_store(flight_data, year, month)
            print(f"Successfully stored {total_records} flight schedules for {month}/{year}.")
    else:
        print(f"Skipped — today is {today.day} (expected 27th)")

if __name__ == "__main__":
    main()
