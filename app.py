import streamlit as st
from PIL import Image
from datetime import datetime
from process_image import (
    ocr_read_image,
    find_month_year_block_and_parse_month_year,
    find_calandar_bottom,
    find_largest_contour_and_crop,
    find_calendar_blocks,
    crop_from_image_each_cell_and_ocr,
    parse_roster_cells
)
from get_flight_info import check_and_fetch_flight_info, get_flight_info, parse_flight_info_and_store
from generate_ics import roster_to_ics
from apscheduler.schedulers.background import BackgroundScheduler

@st.cache_resource
def start_monthly_scheduler():
    def monthly_job():
        try:
            today = datetime.now()
            print(f"[Scheduler Job] Starting monthly flight data update at {today}")
            flight_data, total_records, year, month = get_flight_info()
            if flight_data:
                parse_flight_info_and_store(flight_data, year, month)
                print(f"[Scheduler Job] Successfully stored {total_records} flights for {month}/{year}.")
        except Exception as e:
            print(f"[Scheduler Job] Error in monthly job: {e}")

    scheduler = BackgroundScheduler()
    # Run at 10:00 AM on the 27th day of every month
    scheduler.add_job(monthly_job, 'cron', day=27, hour=10, minute=0)
    scheduler.start()
    print("[Scheduler] Started APScheduler background monthly job (on the 27th at 10:00 AM).")
    return scheduler

# Start background monthly scheduler
start_monthly_scheduler()

# Check and fetch this month's flight schedule table on startup
current_date = datetime.now()
check_and_fetch_flight_info(current_date.year, current_date.month)

st.set_page_config(page_title="Crew Roster Parser", page_icon="✈️")

st.title('✈️ Crew Roster to Calendar')
st.write("Upload a screenshot of your monthly roster to begin.")

uploaded_file = st.file_uploader("Choose a roster screenshot...", type=["jpg", "jpeg", "png"], accept_multiple_files=False)

if uploaded_file is not None:
    image = Image.open(uploaded_file)

    if st.button("Start Processing", width="stretch"):
        with st.spinner("Processing image and extracting data...", width="stretch"):
            # 1. Run initial OCR to find the roster boundaries
            ocr_result = ocr_read_image(image)
            if not ocr_result:
                st.error("Failed to extract text from the image. Please check the image quality.")
                st.stop()

            # 2. Detect boundaries and Month/Year
            top = find_month_year_block_and_parse_month_year(ocr_result)
            bottom = find_calandar_bottom(ocr_result)

            if top is None or bottom is None:
                st.error("Could not detect calendar boundaries. Ensure the header (Month Year) and the full grid are visible.")
                st.stop()

            st.success(f"Detected Roster: **{top["month"]} {top["year"]}**", width="stretch")

            # 3. Isolate the relevant calendar area
            y_start = max(0, top["min_y"])
            y_end = min(image.height, bottom)
            cropped_area = image.crop((0, y_start, image.width, y_end))

            # 4. Clean up and isolate the table grid
            table_img = find_largest_contour_and_crop(cropped_area)

            # 5. Detect and reconstruct the grid blocks
            grid_viz_img, calendar_grid = find_calendar_blocks(table_img)
            # st.image(grid_viz_img, caption="Detected Calendar Grid", width='stretch')

            if calendar_grid:
                # 6. Extract content for each grid cell
                grid_content = crop_from_image_each_cell_and_ocr(table_img, calendar_grid)

                parsed_roster = parse_roster_cells(grid_content, top.get('year'), top.get('month'))

                ics_content = roster_to_ics(parsed_roster)
                if ics_content:
                    st.download_button(
                        label="Add to Calendar",
                        data=ics_content,
                        file_name="crew_roster.ics",
                        mime="text/calendar",
                        width="stretch",
                    )
                    with st.expander("Debug: Parsed Data"):
                        st.write(parsed_roster)
            else:
                st.warning("Failed to detect individual calendar blocks.")
