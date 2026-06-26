# frame-finder
> Work in progress
> 
**Hybrid search over tennis racquets** built on scraped [Tennis Warehouse](https://www.tennis-warehouse.com/) data.

---

## What It Does

Finding the right tennis racquet is harder than it looks. Specs like weight, head size, and stiffness matter — but so do vague, feel-based descriptors like "arm-friendly," "control-oriented," or "good for aggressive baseliners." Traditional keyword search handles specs poorly and natural language queries not at all.

`racquet-sem-search` combines:

- **Structured filtering** — slice by head size, weight, stiffness, balance, string pattern, and more
- **Semantic search** — retrieve racquets by embedding and comparing natural language descriptions
- **LLM-distilled descriptions** — raw TW marketing copy is condensed into neutral, semantically rich blurbs for better embedding quality

The goal is a search experience closer to asking a knowledgeable racquet associate than scrolling a spec sheet.

---

## Current State

### Done
- **Scraper** (`src/racquet_sem_search/scrape.py`) — scrapes all racquet listings from Tennis Warehouse across 11 brands, collecting name, price, rating, description, and 15 spec fields
- **Data cleaning** (`src/racquet_sem_search/clean.py`) — removes junior racquets, extracts numeric specs via regex (head size, weight, balance, stiffness, beam width, string pattern, tension), adds brand and ID columns
- **Description experiments** (`notebooks/03`) — explored using LLMs (ChatGPT, Gemini) to distill TW marketing copy into neutral, semantically useful blurbs; identified that chunk-based rewriting is necessary at this scale
- **Text engineering exploration** (`notebooks/04`) — began exploring how categorical spec fields (`power_level`, `stroke_style`, etc.) can contribute to semantic richness of embeddings
- **Frontend prototype** (`app/static/index.html`) — static demo UI with racquet cards, search hints, relevance bar, and a mock scoring function to validate card design before backend wiring

### Next
- [ ] Finalize LLM description pipeline (produce `semantic_description` for all ~300 racquets)
- [ ] Build text representation combining semantic description + soft specs
- [ ] Embed text representations (likely `text-embedding-3-small` or similar)
- [ ] Create sparse matrix representations (TF-IDF)
- [ ] Implement hybrid lexicographic - semantic search
- [ ] Implement hybrid word - structured feature search: semantic rank + lexical rank + structured rank
- [ ] Wire up FastAPI backend
- [ ] Connect frontend to live backend
- [ ] Generate small eval set from TW articles
- [ ] Gather domain-expert eval instances
- [ ] Evaluation / result quality demos

---

## Project Structure

```
racquet-sem-search/
├── app/
│   ├── main.py                # FastAPI backend (in progress)
│   └── static/index.html      # Search UI prototype
├── data/
│   ├── raw/                   # Scraped CSV (Feb 2026)
│   └── interim/               # Cleaned + staged data
|   └── external/              # External data
|   └── processed/             # Final processed data
├── notebooks/
│   ├── 01_load_data.ipynb
│   ├── 02_clean_data.ipynb
│   ├── 03_description_llm_experiments.ipynb
│   ├── 04_text_engineering.ipynb
│   └── 99_extra_data_scraping_experimentation.ipynb
├── prompts/                   # LLM prompts for description distillation
├── scripts/
│   ├── scrape_racquets.py
│   └── clean_raw_data.py
├── src/racquet_sem_search/
│   ├── scrape.py
│   ├── clean.py
│   └── config.py
└── tests/
    └── test_clean.py
```

---


## Data

~321 racquets scraped from [Tennis Warehouse](https://www.tennis-warehouse.com/) across 11 brands (Babolat, Wilson, Head, Yonex, Prince, Tecnifibre, Dunlop, Völkl, ProKennex, Solinco, Lacoste). Junior racquets are excluded.

Structured fields include: head size, length, strung weight, balance, swingweight, stiffness, beam width, string pattern, string tension, power level, stroke style, swing speed.

> **Note:** Data is used for educational/portfolio purposes. Please respect Tennis Warehouse's terms of service.

---

## Tech Stack

| Component | Tool |
|---|---|
| Scraping | `requests` + `BeautifulSoup` |
| Data pipeline | `pandas`, `numpy` |
| Embeddings | TBD (`text-embedding-3-small` or `sentence-transformers`) |
| Vector store | local `numpy` * `scipy` matrices |
| LLM (description distillation) | OpenAI / Anthropic / Gemini |
| LLM (structured feature extraction) | Gemini Flash |
| Backend | FastAPI (in progress) |
| Frontend | Vanilla HTML/CSS/JS (vibe coded prototype w/ hardcoded data) |

---

## Setup

```bash
git clone https://github.com/r0hankrishnan/racquet-sem-search.git
cd racquet-sem-search
pip install -e .
```

To re-scrape:
```bash
cd scripts && python scrape_racquets.py
```

To re-clean:
```bash
cd scripts && python clean_raw_data.py
```

---

## License

MIT
