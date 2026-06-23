import re
import numpy as np
from skimage import measure, filters, morphology, transform, feature
from PIL import Image, ImageDraw
from rapidocr import EngineType, LangDet, LangRec, ModelType, OCRVersion, RapidOCR
from datetime import datetime
from get_flight_info import lookup_flight_info

# ========= CONFIG =========

IMAGE_PATH = "screenshots/example_03.jpg"

TOP_MARGIN = 20
BOTTOM_MARGIN = 150

MONTH_YEAR_PATTERN = r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s(20\d{2})\b"
MONTH_PATTERN=r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\b"
YEAR_PATTERN=r"\b(20\d{2})\b"

# ==========================

engine = RapidOCR(
    params={
        "Det.lang_type": LangDet.EN,
        "Det.ocr_version": OCRVersion.PPOCRV4,
        "Det.engine_type": EngineType.ONNXRUNTIME,
        "Det.model_type": ModelType.MOBILE,
        "Rec.lang_type": LangRec.EN,
        "Rec.ocr_version": OCRVersion.PPOCRV5,
        "Rec.engine_type": EngineType.ONNXRUNTIME,
        "Rec.model_type": ModelType.MOBILE,
    }
)

# Simple OCR wrapper with error handling
def ocr_read_image(image):
    result = engine(image)
    # error handling
    if not result:
        return None
    return result

# {
#     "month": None,
#     "year": None,
#     "croped_img": None
# }
def find_month_year_block_and_parse_month_year(ocr_result):
    """Parses month, year, and weekdays from the header image using OCR."""

    data = {
        "month": None,
        "year": None,
        "min_y": None
    }

    # Line-level coordinates
    for box, text in zip(ocr_result.boxes, ocr_result.txts):
        match = re.search(MONTH_YEAR_PATTERN, text, re.IGNORECASE)
        if match:
            # Extract Year separately (fallback/general)
            year_match = re.search(YEAR_PATTERN, text)
            if year_match and not data["year"]:
                data["year"] = year_match.group(1)

            # Extract Month separately (fallback/general)
            month_match = re.search(MONTH_PATTERN, text, re.IGNORECASE)
            if month_match and not data["month"]:
                data["month"] = month_match.group(1)

            # Find the minimum Y coordinate to define the top of the block
            # Bounding box is typically [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
            if not data["min_y"]:
                data["min_y"] = int(min(point[1] for point in box)) - TOP_MARGIN

            return data
    return None


def find_calandar_bottom(ocr_result):
    # find the block with the last day of the month (e.g., "28" or "29" for Feb, "30" or "31") and return its Y coordinate as the bottom of the calendar
    day_pattern = r"^\(?(28|29|30|31)\)?$"
    max_y = 0
    highest_day = 0

    for box, text in zip(ocr_result.boxes, ocr_result.txts):
        match = re.search(day_pattern, text.strip())
        if match:
            day_num = int(match.group(1))

            # Find the maximum Y coordinate to define the bottom of the block
            current_box_bottom = int(max(point[1] for point in box))

            # Track the numerically largest day (the end of the month) to find the bottom line
            if day_num > highest_day:
                highest_day = day_num
                max_y = current_box_bottom
            elif day_num == highest_day:
                # In case of multiple detections for the same day, take the lowest one
                max_y = max(max_y, current_box_bottom)

    return (max_y + BOTTOM_MARGIN) if max_y > 0 else None

## not table and accurate enough, deprecate.
def map_text_to_calendar_grid(ocr_result, calendar_grid):
    """Determines which OCR text blocks reside within which grid cell."""
    rows = len(calendar_grid)
    cols = len(calendar_grid[0])
    mapped_data = [[[] for _ in range(cols)] for _ in range(rows)]

    for box, text in zip(ocr_result.boxes, ocr_result.txts):
        # Calculate the center point of the text block in global coordinates
        cx = sum(p[0] for p in box) / 4
        cy = sum(p[1] for p in box) / 4

        # Convert global coordinates to local coordinates relative to the grid image
        lx, ly = cx, cy

        for r in range(rows):
            for c in range(cols):
                cell = calendar_grid[r][c]
                # Check if the local center point is within the cell boundaries
                if cell[0][0] <= lx <= cell[1][0] and cell[0][1] <= ly <= cell[2][1]:
                    mapped_data[r][c].append(text)
    return mapped_data


def crop_from_image_each_cell_and_ocr(img, calendar_grid):
    """
    For each cell in the calendar grid, crop the corresponding area from the image
    and run OCR on it to get more accurate text for that cell.
    """
    rows = len(calendar_grid)
    cols = len(calendar_grid[0])
    mapped_data = [[[] for _ in range(cols)] for _ in range(rows)]

    for r in range(rows):
        for c in range(cols):
            cell = calendar_grid[r][c]
            # Pillow crop uses (left, top, right, bottom)
            left, top = int(cell[0][0]), int(cell[0][1])
            right, bottom = int(cell[2][0]), int(cell[2][1])
            cropped_cell = img.crop((left, top, right, bottom))
            cell_ocr_result = ocr_read_image(cropped_cell)
            if cell_ocr_result:
                # print(f"OCR for cell [{r}][{c}] detected: {cell_ocr_result.txts}")
                for text in cell_ocr_result.txts:
                    mapped_data[r][c].append(text)
            # else:
                # print(f"OCR for cell [{r}][{c}] detected no text.")

    return mapped_data


def find_largest_contour_and_crop(img):
    """Locates the main calendar table within the image, crops it,
    and returns the cropped Pillow Image.
    """
    # 1. Load image and convert to binary mask
    gray = img.convert('L')
    gray_arr = np.array(gray)

    # 2. Adaptive thresholding: Increase block_size to handle the large gradient dark shadow on the right side.
    # A larger block_size (e.g., 151) and a lower offset help retain details in the brighter areas on the left.
    block_size = 151
    local_thresh = filters.threshold_local(gray_arr, block_size, offset=5)
    binary_arr = gray_arr > local_thresh

    # 3. Morphological closing: Merge table lines, text, and cells into a single massive connected region.
    # This prevents the cells on the left from being fragmented and discarded due to local brightness variations.
    binary_closed = morphology.closing(binary_arr, morphology.footprint_rectangle((5, 5)))

    # 4. Convert back to Pillow image to allow manual adjustments/drawing if needed.
    binary_img = Image.fromarray((binary_closed * 255).astype(np.uint8))

    # [Optional] Draw black lines to disconnect any unwanted noise near the margins.
    # Example: If there is noise on the leftmost 10 pixels, draw a black line to cut it off.
    # mask_draw = ImageDraw.Draw(binary_img)
    # mask_draw.line([(10, 0), (10, img.height)], fill=0, width=5)

    # 5. Convert back to NumPy for connected component labeling to locate the main calendar table region.
    final_binary_arr = np.array(binary_img)
    label_image = measure.label(final_binary_arr, background=0)
    regions = measure.regionprops(label_image)

    if regions:
        # Select the largest region (which is the consolidated calendar grid)
        largest_region = max(regions, key=lambda r: r.area)

        # Get bounding box coordinates (min_row, min_col, max_row, max_col)
        minr, minc, maxr, maxc = largest_region.bbox

        # Security margin: Add a small padding (e.g., 5px) to ensure no border lines are clipped.
        padding = 5
        left = max(0, minc - padding)
        upper = max(0, minr - padding)
        right = min(img.width, maxc + padding)
        lower = min(img.height, maxr + padding)

        pillow_bbox = (left, upper, right, lower)

        # 6. Crop the image to the detected table area
        cropped_obj = img.crop(pillow_bbox)
    else:
        print("Cannot find any contours in the image.")
        cropped_obj = img

    return cropped_obj

def find_calendar_blocks(img):
    """Detects calendar grid lines using Canny edge detection, Hough transform,
    and anchor-based grid reconstruction.
    """
    w, h = img.size
    gray = img.convert('L')

    # Convert Pillow image to a NumPy array for scikit-image processing
    gray_arr = np.array(gray)

    # 1. Apply Canny edge detection (corresponds to OpenCV's cv2.Canny)
    # sigma=1.5 mimics OpenCV's kernel smoothing for apertureSize=3
    edges = feature.canny(
        image=gray_arr,
        sigma=1.5,
        low_threshold=50,
        high_threshold=150
    )

    # 2. Build theta range (from -pi/2 to pi/2, spaced by 1 degree) for Hough transform
    theta_array = np.linspace(-np.pi / 2, np.pi / 2, 180, endpoint=False)

    # 3. Detect line segments using Probabilistic Hough Transform (corresponds to cv2.HoughLinesP)
    lines = transform.probabilistic_hough_line(
        image=edges,
        theta=theta_array,
        threshold=150,
        line_length=int(w * 0.2),
        line_gap=10
    )

    # Initialize coordinate lists for line clustering (with image boundaries as default values)
    y_coords = [0, h]
    x_coords = [0, w]

    # 4. Classify line coordinates as horizontal or vertical
    if lines:
        for (x1, y1), (x2, y2) in lines:
            # If horizontal delta is greater than vertical, it's a horizontal line
            if abs(x2 - x1) > abs(y2 - y1):
                y_coords.append(y1)  # Collect horizontal line Y coordinate
            else:
                x_coords.append(x1)  # Collect vertical line X coordinate

    def get_unique_lines(coords, delta=20):
        """Clusters nearby coordinates and returns their averages."""
        if not coords: return []
        coords.sort()
        unique = []
        curr_group = [coords[0]]
        for i in range(1, len(coords)):
            if coords[i] - curr_group[-1] <= delta:
                curr_group.append(coords[i])
            else:
                unique.append(int(sum(curr_group) / len(curr_group)))
                curr_group = [coords[i]]
        unique.append(int(sum(curr_group) / len(curr_group)))
        return unique

    unique_y = get_unique_lines(y_coords)
    unique_x = get_unique_lines(x_coords)

    def reconstruct_grid_lines(unique_coords, max_val, is_cols, expected_spacing=155, delta=20):
        """Reconstructs missing calendar grid lines based on detected anchors.

        Since calendar grids are highly uniform (exactly 7 columns, and 5 or 6 rows of ~155px height),
        we can use the coordinates detected successfully as anchors to fill in the missing lines.
        """
        # Exclude coordinates that are close to image boundaries (0 or max_val)
        internal_coords = [c for c in unique_coords if delta < c < max_val - delta]

        # Fallback if no internal lines were detected
        if not internal_coords:
            if is_cols:
                return [int(5 + i * (max_val - 10) / 7) for i in range(8)]
            else:
                expected_rows = 6 if max_val > 850 else 5
                return [int(5 + i * (max_val - 10) / expected_rows) for i in range(expected_rows + 1)]

        # Calculate spacing between consecutive detected lines
        spacings = []
        for i in range(len(internal_coords) - 1):
            diff = internal_coords[i+1] - internal_coords[i]
            mult = round(diff / expected_spacing)
            if mult > 0:
                spacings.append(diff / mult)

        # Average spacing from detected segments
        spacing = sum(spacings) / len(spacings) if spacings else expected_spacing

        # Bound spacing to reasonable values
        if not (140 <= spacing <= 170):
            spacing = expected_spacing

        # Use the first internal coordinate as the anchor point
        anchor = internal_coords[0]

        # Enforce exact grid line counts:
        # Columns always need exactly 7 cells (8 grid lines)
        # Rows need 6 cells (7 grid lines) for larger heights, or 5 cells (6 grid lines) for smaller heights
        if is_cols:
            expected_lines = 8
        else:
            expected_rows = 6 if max_val > 850 else 5
            expected_lines = expected_rows + 1

        # Generate grid lines extending to the left of the anchor
        left_lines = []
        curr = anchor - spacing
        while curr > 0 and len(left_lines) + 1 < expected_lines:
            left_lines.append(int(curr))
            curr -= spacing
        left_lines.reverse()

        # Generate grid lines extending to the right of the anchor
        right_lines = []
        curr = anchor + spacing
        while len(left_lines) + 1 + len(right_lines) < expected_lines:
            right_lines.append(int(curr))
            curr += spacing

        return left_lines + [anchor] + right_lines

    # Reconstruct exact column and row grid lines
    unique_y = reconstruct_grid_lines(unique_y, h, is_cols=False)
    unique_x = reconstruct_grid_lines(unique_x, w, is_cols=True)

    # Draw the reconstructed grid lines for visualization
    output = img.copy().convert("RGB")
    draw = ImageDraw.Draw(output)
    for y in unique_y:
        draw.line([(0, y), (w, y)], fill=(0, 255, 0), width=2)
    for x in unique_x:
        draw.line([(x, 0), (x, h)], fill=(255, 0, 0), width=2)

    # Generate block coordinates for each calendar cell
    num_rows = len(unique_y) - 1
    num_cols = len(unique_x) - 1

    calendar_grid = [[None for _ in range(num_cols)] for _ in range(num_rows)]

    for r in range(num_rows):
        for c in range(num_cols):
            x1, y1 = unique_x[c], unique_y[r]
            x2, y2 = unique_x[c+1], unique_y[r+1]

            # Store as a 4-point bounding box: [TopLeft, TopRight, BottomRight, BottomLeft]
            calendar_grid[r][c] = np.array([
                [x1, y1], [x2, y1], [x2, y2], [x1, y2]
            ], dtype=np.float32)

    return output, calendar_grid

def parse_roster_cells(cells_data, year=None, month=None):
    parsed = []
    # If the input is a 2D grid (list of rows containing lists of cells), flatten it
    flat_cells = []
    for item in cells_data:
        if isinstance(item, list) and len(item) > 0 and isinstance(item[0], list):
            # It's a row of cells
            for cell in item:
                if cell:
                    flat_cells.append(cell)
        else:
            # It's already a flat list of cells (list of lists)
            if item:
                flat_cells.append(item)

    # Convert month string to month number if provided
    month_num = 1
    if month is not None:
        if isinstance(month, int):
            month_num = month
        elif isinstance(month, str):
            try:
                month_abbr = month.strip()[:3].title()
                month_num = datetime.strptime(month_abbr, "%b").month
            except Exception:
                month_map = {
                    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
                    "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12
                }
                month_num = month_map.get(month_abbr, 1)

    year_num = 2026
    if year is not None:
        try:
            year_num = int(year)
        except ValueError:
            pass

    for cell in flat_cells:
        if not cell:
            continue

        # 1. Clean the date (first element)
        raw_date = str(cell[0]).strip()
        date_match = re.search(r'\d+', raw_date)
        if not date_match:
            continue
        date = int(date_match.group(0))

        # 2. Collect remaining elements (after date)
        elements = [str(x).strip() for x in cell[1:] if str(x).strip()]
        if not elements:
            continue

        # 3. Check if the last element is a shared aircraft code
        shared_aircraft = ""
        if re.match(r'^[A-Za-z]\d{2,3}[A-Za-z]?$', elements[-1]):
            shared_aircraft = elements.pop()

        # 4. Merge OCR fragments into preceding time-containing element
        merged = []
        for el in elements:
            if merged and len(el) <= 3 and ':' in merged[-1]:
                merged[-1] += el
            elif merged and el.isdigit() and len(el) == 1 and not merged[-1].isdigit():
                merged[-1] += el
            else:
                merged.append(el)
        elements = merged

        # 5. Split into duty groups at each flight number marker
        _FLIGHT_MARKER = re.compile(r'^\d+$|^[A-Za-z]\d{4,}$')
        split_indices = [i for i, el in enumerate(elements) if _FLIGHT_MARKER.match(el)]

        if len(split_indices) >= 2:
            groups = []
            for i, idx in enumerate(split_indices):
                end = split_indices[i+1] if i + 1 < len(split_indices) else len(elements)
                groups.append(elements[idx:end])
        else:
            groups = [elements]

        # 6. Process each duty group into an entry
        for group in groups:
            raw_duty = group[0]
            duty = f"BR{raw_duty.zfill(3)}" if raw_duty.isdigit() else raw_duty

            time_info = ""
            aircraft = shared_aircraft or ""
            note_parts = []
            time_pattern = re.compile(r'\d{1,2}:\d{2}')
            seen_time = False
            for el in group[1:]:
                if re.match(r'^[A-Za-z]\d{2,3}[A-Za-z]?$', el):
                    aircraft = el
                elif re.match(r'^\([^)]+\)$', el):
                    note_parts.append(el)
                elif time_pattern.search(el) or ':' in el:
                    time_info += el
                    seen_time = True
                elif not seen_time:
                    duty += f" {el}"
                else:
                    time_info += el
            note = " ".join(note_parts)

            item_dict = {
                "date": date,
                "duty": duty,
                "time": time_info,
                "aircraft": aircraft,
            }
            if note:
                item_dict["note"] = note

            # Merge month/year to create flight_date to match DB (YYYY-MM-DD)
            if year is not None and month is not None:
                item_dict["flight_date"] = f"{year_num:04d}-{month_num:02d}-{date:02d}"

            # 7. Enrich flight duties with schedule data from DB
            if duty.startswith("BR") and duty[2:].isdigit() and item_dict.get("flight_date"):
                flight_info = lookup_flight_info(item_dict["flight_date"], duty)
                if flight_info:
                    item_dict.update(flight_info)

            parsed.append(item_dict)

    # Sort the parsed roster by date
    parsed.sort(key=lambda x: x["date"])
    return parsed


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
    final_result, calendar_grid = find_calendar_blocks(img)

    if calendar_grid:
        # print(f"{calandar_ocr_result.txts}\nDetected calendar grid with {len(calendar_grid)} rows and {len(calendar_grid[0])} columns.")

        # grid_content = map_text_to_calendar_grid(calandar_ocr_result, calendar_grid)
        grid_content = crop_from_image_each_cell_and_ocr(img, calendar_grid)

        # for r_idx, row in enumerate(grid_content):
        #     for c_idx, cell_texts in enumerate(row):
        #         if cell_texts:
        #             print(f"Cell [{r_idx}][{c_idx}] contains: {cell_texts}")
        #         else:
        #             print(f"Cell [{r_idx}][{c_idx}] contains: []")

        # # flatten the grid content
        # arrays = [x for x in np.array(grid_content, dtype=object).reshape(-1) if x]

        # print(f"Calendar grid content mapping complete.{arrays}")

        parsed_result = parse_roster_cells(grid_content, top.get('year'), top.get('month'))
        print(f"Parsed roster content: {parsed_result}")

    # 6. Your display block to show the result (optional)
    # final_result.show()

if __name__ == "__main__":
    main()
