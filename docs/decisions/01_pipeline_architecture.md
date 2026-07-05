# ADR Entries — Data Pipeline & Search Architecture (pre-web-app)

> Consolidated from development sessions spanning ~2026-05 through 2026-06-29,
> reconstructed from session history and **verified against the repo implementation
> as of 2026-07-04**. Where a discussed decision was NOT implemented, that is
> recorded explicitly — this log reflects what shipped, not what was talked about.

---

## ADR: Staged CSV data pipeline (scrape → clean → distill → build)

**Status:** Accepted

**Context:** Needed a repeatable path from Tennis Warehouse's website to
serving-time artifacts.

**Decision:** Four sequential stages, each a separate script reading/writing CSVs
through `data/raw/` → `data/interim/` → `data/processed/`:
`scrape_racquets.py` → `clean_raw_data.py` → `distill_descriptions.py` →
`build_processed_artifacts.py`. Serving artifacts are
`racquet_data_artifact.csv` + `embedding_artifacts.npz`. v1 treats data as fully
static — no incremental updates.

**Why:** Simple, inspectable intermediate outputs; each stage independently
re-runnable; matches the manual workflow the project grew out of.

**Known limitation (recorded, deferred):** Scripts read hardcoded dated filenames
(e.g. `racquets_cleaned_2026_06_24.csv`) and write with `date.today()`. A
`find_latest(directory, prefix)` utility was designed but **never implemented** — the repo
still hardcodes dated paths. Incremental change-detection updates are a v1.1+
design task (see the pipeline-overhaul notes in the deployment-era ADR file).

---

## ADR: Provider-agnostic LLM adapter (ABC pattern)

**Status:** Accepted

**Context:** Both distillation and query parsing need LLM calls; wanted the
ability to swap providers (cost, free tiers, testing).

**Decision:** `adapters.py` defines an `LLMAdapter` ABC with a single generic
method `complete(prompt: str, output_format: type[T]) -> T` where
`T = TypeVar("T", bound=BaseModel)`. Concrete `AnthropicAdapter`
(`claude-haiku-4-5`, `client.messages.parse` with `output_format`) and
`GeminiAdapter` (`gemini-3.5-flash`, `generate_content` with
`GenerateContentConfig(response_mime_type="application/json",
response_schema=...)`, plus an `isinstance` check the SDK's union return type
requires).

**Why:** Infrastructure (provider plumbing) separated from task orchestration
(`distill.py`, `parse_query.py`). The generic TypeVar lets one adapter serve any
Pydantic output schema — distillation batches and parsed queries use the same
`complete()`.

**Superseded detail:** Gemini was originally slated as the runtime query parser
(generous free tier). **The deployed app uses `AnthropicAdapter`** — the engine is
constructed with it in `app/main.py`. `GeminiAdapter` remains implemented and
tested as an alternative.

---

## ADR: Structured outputs over prompt-JSON or tool-use

**Status:** Accepted

**Context:** LLM responses must be machine-parseable (batch distillations, parsed
queries).

**Decision:** Use each provider's native structured-output mechanism bound to
Pydantic models (`messages.parse` / `response_schema`), not "please return JSON"
prompting and not the older tool-use pattern.

**Why:** Schema enforcement at the SDK level; no hand-rolled JSON parsing or
fence-stripping; validation failures surface as typed errors.

---

## ADR: Distillation pipeline —> batching, retries, partial saves, dual validation

**Status:** Accepted

**Context:** ~300 racquet descriptions rewritten via LLM; a full run costs
money and time, and silent data corruption (wrong/duplicated IDs) is worse than a
loud failure.

**Decision (all verified in `distill.py`):**
- Batches of 10 racquets per prompt (`build_batch_prompts`)
- Per-batch validation: set-equality of expected vs. returned `racquet_id`s AND a
  length check — the length check exists because set equality alone missed
  duplicate IDs within a batch (a real failure from the first full run)
- 3-attempt retry with exponential backoff (`2**(i+1)` seconds)
- `_save_partial()` on every failure path, so a crash never loses completed batches
- Final row-count assertion against the input dataframe

**Why:** The first full run failed at the final count check despite per-batch
checks passing — the duplicate-ID gap. The dual check and partial-save discipline
came directly from that incident.

**Distillation prompt policy:** rewrite to feel-focused content only (power,
control, spin, contact feel, maneuverability, suitability, arm-friendliness);
extraction-only — "do not infer, extrapolate, or invent"; 2–4 sentences; empty
string when a description has no usable content. Named `distilled_description`
(not `semantic_description`) for consistency with the module/process names.

**Note on prompt location:** externalizing runtime prompts to a `prompts/`
directory was considered; **in the repo, the runtime prompts
(`DISTILLATION_BASE_PROMPT`, `QUERY_PARSING_BASE_PROMPT`) live in `config.py`**.

---

## ADR: Different text fields for semantic vs. BM25 retrieval

**Status:** Accepted

**Context:** Hybrid search needs both an embedding corpus and a lexical corpus;
using one shared field for both seemed natural but is wrong.

**Decision:**
- **Semantic search** embeds `distilled_description` ONLY.
- **BM25** indexes a concatenated `keyword_text` blob:
  `racquet_name + racquet_power_level + racquet_stroke_style +
  racquet_swing_speed + distilled_description`.

**Why:** Brand/model names and categorical labels in the embedding corpus pollute
the semantic space with lexical signal (embeddings of "Babolat Pure Aero..." drift
toward brand tokens rather than feel). BM25 is exactly where lexical signal
belongs, so names and category labels go there.

**Alternatives rejected:** per-column BM25 indices — BM25 requires one consistent
IDF distribution over one document unit; splitting by column breaks the statistics.

**Placement:** `create_keyword_text` lives in `dataset.py`, not `clean.py`,
because it depends on `distilled_description`, which doesn't exist yet at the
clean stage — a cross-pipeline-stage dependency.

---

## ADR: Keyword grounding against small categorical enums only

**Status:** Accepted

**Context:** The query parser maps user language onto lexical category terms; which
columns are reliable targets?

**Decision:** Ground the keyword-extraction prompt against exactly three
low-cardinality categorical columns, confirmed by CSV inspection:
`racquet_power_level` (5 values), `racquet_stroke_style` (6),
`racquet_swing_speed` (6) — 17 labels total. Higher-cardinality columns
(`racquet_composition`: 51, `racquet_grip_type`: 45, `racquet_colors`: 58) are
excluded from `keyword_text` and from the prompt.

**Why:** A 17-label vocabulary is small enough for reliable LLM mapping and dense
enough in the corpus to matter for BM25; 50-value sparse columns are neither.
This decision driven by explicitly inspecting each column.

**Empirical BM25 note:** `bm25s.tokenize()` splits on hyphens
(`"low-medium"` → `["low","medium"]` which is desirable for graded partial matching
across these labels) and lowercases internally (manual lowercasing removed as
redundant). Verified by testing, not assumed.

---

## ADR: RRF over weighted score blending (the fusion decision)

**Status:** Accepted — supersedes two rejected designs

**Context:** BM25 scores and cosine similarities live on incomparable scales;
naive score averaging is statistically wrong. Needed a fusion method.

**Decision:** Reciprocal Rank Fusion. Implemented as
`_reciprocal_rank_fusion(*ranked_id_lists, k=60)` — a `@staticmethod` on
`RacquetSearchEngine` accepting any number of ranked lists, canonical
`1/(k+rank)` accumulation.

**Why:** RRF uses only rank position, never score magnitude, sidestepping scale
incomparability entirely — and, decisively, it requires **no weights**. Weighted
blending requires weight values that are indefensible without labeled relevance
data, which doesn't exist yet.

**Full reversal history (all dead ends recorded):**
1. *Query-dependent weighted blending* (rejected): the parser would set
   BM25/semantic/structured mix weights per query. Died on the weights problem —
   no data to justify any particular values.
2. *Filter-then-RRF* (rejected): hard structured filtering before fusion. Died on
   over-filtering risk with unknown precision/recall tradeoffs.
3. *Continuous structured scoring* (deferred, not rejected): revisit with eval
   data; the current v2 lean is a third ranked list fused into RRF (see
   deployment-era ADR file).

**Implementation placement:** a `@staticmethod`, not a separate `fusion.py`
module. Learned about how adding an `*args` signature means
a third ranked list (v2 structured retrieval) plugs in without an interface change.

---

## ADR: v1 scope —> `ParsedQuery` is two strings; structured filtering deferred

**Status:** Accepted (supersedes the fuller `StructuredFilters` design)

**Context:** Early designs had `ParsedQuery` carrying a `StructuredFilters` object
(brand, spec bounds, etc.) plus a `bm25_keywords` list.

**Decision (implemented in `parse_query.py`):** `ParsedQuery` has exactly two fields —
`semantic_query: str` and `keyword_query: str`. `StructuredFilters` is fully
removed (not present-but-unused). `bm25_keywords` was cut earlier — BM25 consumes a
query string directly, so a separate keyword list field had no job.

**Why:** Choosing hard-filter vs. continuous-scoring architecture requires eval
evidence that doesn't exist. Shipping v1 as BM25 + semantic + RRF creates the
eval baseline that makes the v2 structured design an evidence-based
before/after, instead of an upfront guess. Keeping dead fields "for later"
results in unneeded complexity.

---

## ADR: Engine shape — `RacquetSearchEngine` with explicit init + `setup()` wrapper

**Status:** Accepted

**Context:** Startup requires four expensive/ordered steps (embedder, embeddings,
BM25 corpus tuple, BM25 index); search requires them all ready.

**Decision (verified in `engine.py`):**
- Four explicit idempotent init methods (each no-ops with a log line if already
  done) + a `setup()` convenience wrapper calling them in order — callers get
  one-call convenience without losing the decomposed steps.
- `_check_ready()` raises actionable `ValueError`s naming the missing step.
- `search()` returns a `SearchResult` Pydantic model (`fused_result`,
  `parsed_query`, `parsing_status`) — not a bare list.
- `ParsingStatus` enum (SUCCESS / SKIPPED / FAILED) replaced a boolean
  `used_fallback` flag — three states, not two, and self-documenting.
- `_resolve_query()` returns a `ResolvedQuery` NamedTuple (lighter than Pydantic —
  no validation needed for an internal 4-field pass-through).
- Parsing failure falls back to the raw query for both retrieval legs
  (try/except in `_resolve_query`, status = FAILED) — an LLM outage degrades
  search quality, never availability.
- Empty `keyword_query` → BM25 leg skipped; RRF runs on the semantic list alone.
- BM25 is built at startup from the dataframe, NOT saved as an artifact — fitting
  is near-instant at ~300 documents; an artifact file adds pipeline surface for no
  startup savings.

---

## ADR: LLM as translator, not domain expert (design principle)

**Status:** Accepted (principle applied across distillation and parsing)

**Context:** I had some early confusion about whether the runtime model needed to
"understand racquets" to map queries onto the data. I wasn't sure if I needed to encode
"expertise" about the racquet specs into the LLM.

**Decision:** Domain knowledge is encoded at design time — into the distillation
prompt's feel-taxonomy, the `ParsedQuery` field descriptions, and the grounded
category vocabularies. The runtime model performs narrow NLP translation against
those structures. No need for RAG, fine-tuning, or runtime domain reasoning.

**Why:** The hard part (what dimensions matter for racquet feel; which categories
are reliable) was my judgment, fixed in schemas and prompts where it's
reviewable and versioned. The model's job stays small, cheap (Haiku-class), and
swappable. This principle also drove the later rejection of agentic grep-based
retrieval (see deployment-era ADR file): the correct home for LLM flexibility is
ingestion-time extraction, not query-time reasoning. In the future, it would be nice to audit my logic with a proper racquet expert.
