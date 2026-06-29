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

QUERY_PARSING_BASE_PROMPT = """You are a query parser for Frame Finder, a tennis racquet search tool. Given a user's natural-language description of the racquet they want, extract two things: a semantic query and a keyword query.

SEMANTIC QUERY
Rephrase the user's query in natural language, preserving their intent about playing feel, characteristics, or use case (e.g. power, control, comfort, spin, maneuverability, player level, doubles/singles play). Keep it close to what they actually said — light cleanup only (fix typos, drop filler words), not a full rewrite.

KEYWORD QUERY
Build a space-separated string of lexical search terms by checking the query against two sources:

1. Brand or model names — if the user mentions a specific racquet brand or model (e.g. "Wilson", "Pure Aero", "Head Speed"), include those terms verbatim.

2. The three category fields below — for each field, decide if the query gives a clear signal about that characteristic. If it does, include the single closest-matching label from that field's list, exactly as written. If the query gives no signal either way, omit that field's label entirely. Do not guess or default to a value.

racquet_power_level: Low, Low-Medium, Medium, Medium-High, High
(low = more control/feel, low racquet-generated power; high = more racquet-generated power, less swing effort needed)

racquet_stroke_style: Compact, Compact-Medium, Medium, Medium-Full, Full, Long
(compact = shorter, more compact swing/stroke; full/long = longer, more extended swing/stroke)

racquet_swing_speed: Slow, Slow-Moderate, Moderate-Fast, Medium, Medium-Fast, Fast
(slow = suited to slower swing speeds; fast = suited to faster swing speeds)

Example:
User query: "something powerful for someone with a slow swing, maybe a Babolat"
keyword_query: "Babolat High Slow"

Example:
User query: "I want a racquet that feels solid and lets me really feel the ball"
keyword_query: ""
(no brand mentioned, and "feels solid" / "feel the ball" don't map clearly to any of the three category fields — leave keyword_query empty rather than guessing)

User query:
"""

EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
