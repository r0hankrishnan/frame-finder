# frame-finder
> Work in progress -- soon to be deployed!
> This is a showcase and learning project. Please respect TW's terms of service

**Hybrid search over tennis racquets** built on scraped [Tennis Warehouse](https://www.tennis-warehouse.com/) data.



## What It Does

Finding the right tennis racquet is harder than it looks. Specs like weight, head size, and stiffness matter — but so do vague, feel-based descriptors like "arm-friendly," "control-oriented," or "good for aggressive baseliners." Traditional keyword search handles specs poorly and natural language queries not at all.

`racquet-sem-search` (soon-to-be-renamed as `frame-finder`) combines:

- **Semantic search over LLM-distilled descriptions** — retrieve racquets by embedding and comparing neutral, semantically rich natural language descriptions that were condensed from raw TW marketing copy. 
- **BM25-based lexical search** — LLM extracted keywords from your query are run against a data-informed keyword text corpus to produce lexically relevant racquets.

The goal is a search experience closer to asking a knowledgeable racquet associate than scrolling a spec sheet.
