"""Module to hold base variables for web scraping and other tasks."""

import requests

BASE_URL: str = "https://www.tennis-warehouse.com/"

# Go to Tennis Warehouse website and check listed racquet brands before running -> brand paths need to be manually set
BRAND_PATHS: list[str] = [
    "Babolatracquets.html",
    "Wilsonracquets.html",
    "Headracquets.html",
    "YonexRacquets.html",
    "PrinceRacquets.html",
    "Tecnifibreracquets.html",
    "Mizuno_Tennis_Racquets/catpage-MIZTEN.html",
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

DISTILLATION_BASE_PROMPT = """You are helping build a semantic search tool for tennis racquets. Your job is to rewrite each racquet description into a concise, feel-focused summary that captures how the racquet actually plays.
    
    For each racquet, rewrite the description to focus only on:
        - Power level, control, and spin
        - How it feels on contact (stiff, plush, muted, crisp, etc.)
        - Maneuverability and stability
        - Who it suits (player level, style, swing speed)
        - Arm-friendliness if mentioned
        
    Accuracy is critical. Only include information explicitly stated in the original description. Do not infer, extrapolate, or invent characteristics. If arm-friendliness is not mentioned, do not include it. If power level is not described, do not guess.
    
    Keep each rewritten description to 2-4 sentences. If a description contains no usable feel or performance content, return an empty string for that racquet's distilled_description field.
    
    Here are the racquets to process:"""
