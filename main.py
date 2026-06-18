from PIL import Image
import numpy as np
from process_image import ocr_read_image, find_month_year_block_and_parse_month_year, find_calandar_bottom, find_largest_contour_and_crop, find_calendar_blocks, map_text_to_calendar_grid, crop_from_image_each_cell_and_ocr

# ========= CONFIG =========

IMAGE_PATH = "screenshots/example_00.jpg"

# ========= CONFIG =========

def main():

    # possible step:
    # use ocr to parse all the text blocks in the image.
    ocr_result = ocr_read_image(IMAGE_PATH)
    # 1. find Month and Year block(e.g., "Jan 2026", "Feb2025") and use its Y coordinate as a reference to ignore anything above it, maybe even crop to that area only for better OCR accuracy
    top = find_month_year_block_and_parse_month_year(ocr_result)
    print(f"Detected month/year: {top['month']} {top['year']}")
    bottom = find_calandar_bottom(ocr_result)

    if top is None or bottom is None:
        print("Failed to detect calendar boundaries (top or bottom).")
        return

    raw_img = Image.open(IMAGE_PATH)
    # Ensure the slice indices are valid
    y_start = max(0, top["min_y"])
    y_end = min(raw_img.height, bottom)

    cropped_area = raw_img.crop((0, y_start, raw_img.width, y_end))
    img = find_largest_contour_and_crop(cropped_area)
    calandar_ocr_result = ocr_read_image(img)
    qq, calendar_grid = find_calendar_blocks(img)

    if calendar_grid:
        print(f"{calandar_ocr_result.txts}\nDetected calendar grid with {len(calendar_grid)} rows and {len(calendar_grid[0])} columns.")

        # grid_content = map_text_to_calendar_grid(calandar_ocr_result, calendar_grid)
        grid_content = crop_from_image_each_cell_and_ocr(img, calendar_grid)

        # for r_idx, row in enumerate(grid_content):
        #     for c_idx, cell_texts in enumerate(row):
        #         if cell_texts:
        #             print(f"Cell [{r_idx}][{c_idx}] contains: {cell_texts}")
        #         else:
        #             print(f"Cell [{r_idx}][{c_idx}] contains: []")

        # flatten the grid content
        arrays = [x for x in np.array(grid_content, dtype=object).reshape(-1) if x]

        print(f"Calendar grid content mapping complete.{arrays}")




    # 6. Your display block to show the result (optional)
    # qq.show()

if __name__ == "__main__":
    main()
