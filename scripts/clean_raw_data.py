from pathlib import Path
from datetime import date

import pandas as pd

from frame_finder.clean import clean_raw_data

if __name__ == "__main__":

    PROJECT_ROOT = (
        Path(__file__).resolve().parents[1]
    )  # Get project root based on file location NOT where script is run from
    DATA_DIR = PROJECT_ROOT / "data"
    RAW_DATA_PATH = DATA_DIR / "raw" / "racquets_raw_2026_06_24.csv"

    today_date = date.today().strftime("%Y_%m_%d")  # Format so it can be sorted

    CLEANED_DATA_PATH = DATA_DIR / "interim" / f"racquets_cleaned_{today_date}.csv"

    CLEANED_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)  # Make sure dirs exist

    raw_data = pd.read_csv(RAW_DATA_PATH)
    cleaned_data = clean_raw_data(df=raw_data)

    cleaned_data.to_csv(CLEANED_DATA_PATH)
