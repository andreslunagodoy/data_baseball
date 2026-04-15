import pandas as pd
import time
import os
from urllib.request import urlopen, Request
from bs4 import BeautifulSoup

OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "immaculate_grids.csv")
TOTAL_GRIDS = 1102
DELAY = 1.5  # seconds between requests

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


def parse_grid(grid_num):
    """Scrape a single immaculate grid page and return its 6 conditions."""
    url = f"https://www.sports-reference.com/immaculate-grid/grid-{grid_num}"
    req = Request(url, headers=HEADERS)
    html = urlopen(req).read().decode("utf-8")
    soup = BeautifulSoup(html, "html.parser")

    def extract_conditions(cells):
        conditions = []
        for cell in cells:
            text = cell.get_text(strip=True)
            if text == "Loading...":
                continue
            img = cell.find("img", src=lambda s: s and "light" in s)
            if img:
                code = img["src"].split("/")[-1].replace(".svg", "")
                conditions.append({"type": "team", "code": code, "label": img.get("alt", "")})
            else:
                conditions.append({"type": "stat", "code": "", "label": text})
        return conditions

    # Column headers: w-24, h-16 sizing
    col_cells = soup.find_all(
        "div", class_=lambda c: c and "w-24" in c and "h-16" in c
    )
    # Row headers: w-20, h-24 sizing
    row_cells = soup.find_all(
        "div", class_=lambda c: c and "w-20" in c and "h-24" in c
    )

    cols = extract_conditions(col_cells)
    rows = extract_conditions(row_cells)

    if len(cols) != 3 or len(rows) != 3:
        raise ValueError(f"Expected 3 cols and 3 rows, got {len(cols)} cols and {len(rows)} rows")

    return {
        "grid_num": grid_num,
        "col1_type": cols[0]["type"], "col1_code": cols[0]["code"], "col1_label": cols[0]["label"],
        "col2_type": cols[1]["type"], "col2_code": cols[1]["code"], "col2_label": cols[1]["label"],
        "col3_type": cols[2]["type"], "col3_code": cols[2]["code"], "col3_label": cols[2]["label"],
        "row1_type": rows[0]["type"], "row1_code": rows[0]["code"], "row1_label": rows[0]["label"],
        "row2_type": rows[1]["type"], "row2_code": rows[1]["code"], "row2_label": rows[1]["label"],
        "row3_type": rows[2]["type"], "row3_code": rows[2]["code"], "row3_label": rows[2]["label"],
    }


def load_progress():
    """Load already-scraped grids to support resuming."""
    if os.path.exists(OUTPUT_FILE):
        df = pd.read_csv(OUTPUT_FILE)
        done = set(df["grid_num"].tolist())
        rows = df.to_dict("records")
        print(f"Resuming: {len(done)} grids already scraped.")
        return rows, done
    return [], set()


def save_progress(rows):
    df = pd.DataFrame(rows)
    df.sort_values("grid_num", inplace=True)
    df.to_csv(OUTPUT_FILE, index=False)


def main():
    rows, done = load_progress()
    remaining = [g for g in range(1, TOTAL_GRIDS + 1) if g not in done]

    if not remaining:
        print("All grids already scraped!")
        return

    print(f"Scraping {len(remaining)} grids ({remaining[0]} to {remaining[-1]})...")
    errors = []

    for i, grid_num in enumerate(remaining):
        try:
            row = parse_grid(grid_num)
            rows.append(row)

            if (i + 1) % 10 == 0:
                save_progress(rows)

            print(f"  [{i+1}/{len(remaining)}] Grid #{grid_num} OK")
        except Exception as e:
            print(f"  [{i+1}/{len(remaining)}] Grid #{grid_num} FAILED: {e}")
            errors.append(grid_num)

        time.sleep(DELAY)

    save_progress(rows)
    print(f"\nDone! {len(rows)} grids saved to {OUTPUT_FILE}")
    if errors:
        print(f"Failed grids ({len(errors)}): {errors}")


if __name__ == "__main__":
    main()
