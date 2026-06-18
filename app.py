import streamlit as st
import io
from PIL import Image
import numpy as np
from process_image import (
    ocr_read_image,
    find_month_year_block_and_parse_month_year,
    find_calandar_bottom,
    find_largest_contour_and_crop,
    find_calendar_blocks,
    crop_from_image_each_cell_and_ocr
)

# # Multi language support
# # 1. Define translations for your UI elements
# TRANSLATIONS = {
#     "English": {
#         "page_title": "Crew Roster Parser",
#         "file_uploader": "Choose a roster screenshot...",
#         "button": "Fetch Data",
#         "spinner": "Processing data, please wait...",
#         "success": "Data loaded successfully!",
#         "label": "Choose Language"
#     },
#     "中文": {
#         "page_title": "Crew Roster Parser",
#         "file_uploader": "中Choose a roster screenshot...",
#         "button": "Fetch Data123123",
#         "spinner": "Procesqweqwsing data, please wait...",
#         "success": "Data loaded successfully!",
#         "label": "Choose Language"
#     }
# }
# DEFAULT_LANG = "中文"

# # 2. Initialize default language state
# if "current_lang" not in st.session_state:
#     st.session_state["current_lang"] = DEFAULT_LANG

# # 3. Callback function to trigger on selection
# def update_language():
#     st.session_state["current_lang"] = st.session_state["lang_control"]

# # 4. Horizontal Segmented Control Widget
# st.segmented_control(
#     label="Language Selection",
#     options=list(TRANSLATIONS.keys()),
#     default=st.session_state["current_lang"],
#     key="lang_control",
#     on_change=update_language,
#     label_visibility="collapsed"  # Hides label for a cleaner UI look
# )

# # 5. Load strings based on active state
# lang = TRANSLATIONS[st.session_state["current_lang"]]

# st.divider()
# ####

st.set_page_config(page_title="Crew Roster Parser", page_icon="✈️")

st.title('✈️ Crew Roster to Calendar')
st.write("Upload a screenshot of your monthly roster to begin.")

uploaded_file = st.file_uploader("Choose a roster screenshot...", type=["jpg", "jpeg", "png"], accept_multiple_files=False)

if uploaded_file is not None:
    # Display the uploaded image
    image = Image.open(uploaded_file)
    # st.image(image, caption='Uploaded Roster Screenshot', width="stretch")

    options = ["Apple Calendar", "Google Calendar"]
    selection = st.pills("Calenders", options, selection_mode="multi")

    if st.button("Start Processing", width="stretch"):
        if not selection:
            st.error("Please select at least one calendar.")
            st.stop()
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

                # st.subheader("Extracted Content Preview")
                # # Preview non-empty items extracted from the grid
                # flat_content = [item for row in grid_content for cell in row for item in cell if item]
                # st.write(flat_content)

                # Convert PIL image to bytes for download
                buf = io.BytesIO()
                table_img.save(buf, format="PNG")
                byte_im = buf.getvalue()
                secs = st.columns(len(selection))
                for index, s in enumerate(selection):
                    secs[index].download_button(
                        label=f"Download {s}",
                        data=byte_im,
                        file_name="parsed_roster.png",
                        mime="image/png",
                        width="stretch",
                        key=s
                    )
            else:
                st.warning("Failed to detect individual calendar blocks.")
