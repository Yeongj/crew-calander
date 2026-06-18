# cron job for monthly update of flight info mapping table

import schedule
import time
from datetime import datetime
from get_flight_info import get_flight_info, parse_flight_info_and_store

def monthly_job():
    today = datetime.now()
    # Run only if it's the 27th day of the month
    if today.day == 27:
        print(f"Starting monthly flight data update at {today}")
        flight_data, total_records, year, month = get_flight_info()
        if flight_data:
            parse_flight_info_and_store(flight_data, year, month)
            print(f"Successfully stored {total_records} flight schedules for {month}/{year}.")
    else:
        print(f"Skipped — today is {today.day}")

# Check every day at 10:00 AM
schedule.every().day.at("10:00").do(monthly_job)

print("Scheduler started. Press Ctrl+C to stop.")

try:
    while True:
        schedule.run_pending()
        time.sleep(1)
except KeyboardInterrupt:
    print("\nScheduler stopped.")
