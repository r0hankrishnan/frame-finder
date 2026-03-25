from racquet_sem_search.scrape import scrape_tw_racquets

from pathlib import Path
from datetime import date

if __name__ == "__main__":
    DATA_DIR = Path().cwd().parent / "data"
    
    today_date = date.today().strftime("%m_%d_%y")
    RAW_DATA_PATH = DATA_DIR / f"raw/racquets_raw_{today_date}.csv"

    scrape_tw_racquets(save_file = True, save_path = str(RAW_DATA_PATH), 
                       verbose = True)
