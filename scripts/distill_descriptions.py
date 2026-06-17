from racquet_sem_search.distill import distill_descriptions, AnthropicAdapter

from pathlib import Path
from datetime import date
import csv
import logging

import pandas as pd

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    
    logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s — %(levelname)s — %(message)s"
        )

    PROJECT_ROOT = Path(__file__).resolve().parents[1]
    DATA_DIR = PROJECT_ROOT / "data"
    PARTIAL_SAVE_PATH = DATA_DIR / "interim"
    CLEANED_DATA_PATH = DATA_DIR / "racquets_cleaned_2026_05_16.csv" # should use argparse here
    
    today_date = date.today().strftime("%Y_%m_%d")
    
    racquets_df = pd.read_csv(CLEANED_DATA_PATH)
    anthropic_adapter = AnthropicAdapter()
    
    logger.info("Distilling descriptions...")
    distilled_descs = distill_descriptions(racquets_df=racquets_df, llm_adapter=anthropic_adapter, partial_save_path=PARTIAL_SAVE_PATH)
    logger.info("Finished distilling!")
   
    with open(PARTIAL_SAVE_PATH / f"distilled_descriptions_{today_date}.csv", "w", newline="") as f:
        fieldnames = ["racquet_id", "distilled_description"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)

        writer.writeheader()
        for item in distilled_descs:
            writer.writerow(item.model_dump())
    