import requests

BASE_URL: str = "https://www.tennis-warehouse.com/"
BRAND_PATHS: list[str] = [
    "Babolatracquets.html",
    "Wilsonracquets.html",
    "Headracquets.html",
    "YonexRacquets.html",
    "PrinceRacquets.html",
    "Tecnifibreracquets.html",
    "DunlopRacquets.html",
    "VolklRacquets.html",
    "ProKennexracquets.html",
    "Solinco_Tennis_Racquets/catpage-SOLINCORAC.html",
    "LacosteRacquets.html",
]

EXPECTED_SPEC_KEYS = [
    "head_size",
    "length",
    "strung_weight",
    "balance",
    "swingweight",
    "stiffness",
    "beam_width",
    "composition",
    "power_level",
    "stroke_style",
    "swing_speed",
    "racquet_colors",
    "grip_type",
    "string_pattern",
    "string_tension",
]

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "Mozilla/5.0 (compatible; TW-Scraper/1.0)"})
