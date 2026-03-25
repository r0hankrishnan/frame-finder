from racquet_sem_search.clean import clean_raw_data

from pathlib import Path
from datetime import date
import pandas as pd

if __name__ == "__main__":
    DATA_DIR = Path().cwd().parent / "data"
    RAW_DATA_NAME = "racquets_raw_02_14_26.csv"

    today_date = date.today().strftime("%m_%d_%y")
    CLEANED_DATA_NAME = f"racquets_cleaned_{today_date}.csv"

    raw_data = pd.read_csv(DATA_DIR / "raw" / RAW_DATA_NAME)
    cleaned_data = clean_raw_data(df = raw_data)

    cleaned_data.to_csv(DATA_DIR / "interim" / CLEANED_DATA_NAME)