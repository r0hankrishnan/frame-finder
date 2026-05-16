from racquet_sem_search.scrape import scrape_tw_racquets

from pathlib import Path
from datetime import date

if __name__ == "__main__":
    PROJECT_ROOT = Path(__file__).resolve().parents[1] # Get project root based on file location NOT where script is run from 
    DATA_DIR = PROJECT_ROOT / "data"
    
    today_date = date.today().strftime("%Y_%m_%d") # Format so it can be sorted
    RAW_DATA_PATH = DATA_DIR / "raw" / f"racquets_raw_{today_date}.csv"
    
    RAW_DATA_PATH.parent.mkdir(parents = True, exist_ok = True) # Make sure dirs exist
    
    SAVE_HTML_PATH = DATA_DIR / "raw" / "racquets_raw_html"

    scrape_tw_racquets(save_file = True, save_path = str(RAW_DATA_PATH),
                       save_html = True, save_html_path = str(SAVE_HTML_PATH),
                       verbose = True)
