# ADR Entries — FastAPI App, Persistence & Deployment

---

## ADR: FastAPI app structure — `app/` + `frontend/` as siblings to `src/`

**Status:** Accepted

**Context:** Needed to expose the CLI-only `RacquetSearchEngine` over HTTP without
entangling the library with web concerns.

**Decision:** Three top-level directories, none nested: `src/frame_finder/` (pure
library, no HTTP knowledge), `app/` (HTTP layer — routers, dependencies, schemas,
database), `frontend/` (static files served directly). Routers split by concern
(`search.py`, `feedback.py`, `health.py`).

**Why:** Keeps the engine reusable by both CLI and web without modification. The
`app/` layer only translates between HTTP and the library. Matches the same
"does this earn its place" test applied elsewhere.

**Alternatives considered:** `api/` naming (superseded by `app/`); frontend nested
in `app/` (rejected — muddies the Python-vs-static-assets distinction and
the StaticFiles mount path).

---

## ADR: Route concurrency — `async def` + `run_in_threadpool` for the whole search call

**Status:** Accepted (v1)

**Context:** `/search` does both an LLM call (I/O-bound) and BM25/embedding/RRF
retrieval (CPU-bound). The single-threaded event loop is blocked by CPU-bound work
run directly in an async route.

**Decision:** Wrap the entire synchronous `engine.search()` in a single
`run_in_threadpool(...)` call, awaited from an `async def` route.

**Why:** Prevents CPU-bound retrieval from freezing the event loop for other users.
Simpler than decomposing the engine, and still correct: the whole call runs off the event
loop thread. `await` is still required to retrieve the result and to yield the loop
while the worker thread runs.

**Alternatives considered:** Splitting the route into a native-async parse step +
threadpooled retrieval step (rejected for v1 — see the sync-query-parsing ADR;
the split was based on the false premise that a sync `_resolve_query` could be
awaited). Building a new engine helper solely for the route (rejected — the route
calls `search()` as one unit, so the helper earned no keep).

---

## ADR: Synchronous LLM adapter for v1 (deferred native async)

**Status:** Accepted (v1); revisit when logged latency justifies it

**Context:** `AnthropicAdapter` uses a synchronous SDK client. Making query parsing
natively async would require an `AsyncAnthropic` client, an async `complete_async`
method (duplicating validation logic), an `async def _resolve_query`, and ABC
contract changes — all touching code the CLI and distillation pipeline depend on,
which has no test suite.

**Decision:** Keep everything synchronous; parsing runs inside the same
`run_in_threadpool` as retrieval.

**Why:** The performance benefit is marginal and yet-to-be-required. `run_in_threadpool`
already prevents one user's LLM wait from blocking others — native async only
saves thread-handoff overhead, imperceptible at unknown/low traffic. Adding an
untested async code path behind the app's most central route, with no test net,
is riskier than the marginal gain. Consistent with the project's speculative-
complexity avoidance.

**Revisit when:** Logged search latency (via `searches.searched_at`, or added
duration tracking) shows request queuing under real concurrent load, or before a
deliberate load-testing effort. Implementation recipe recorded separately.

---

## ADR: Persistence — Postgres (Railway) over SQLite, raw psycopg2 over ORM

**Status:** Accepted

**Context:** Need to persist search logs and feedback. SQLite on Railway's
ephemeral filesystem is wiped on every redeploy unless a paid persistent volume is
attached. Analytics/eval require durable, queryable data accessible from anywhere.

**Decision:** Managed Postgres on Railway (free hobby tier). Access via raw
`psycopg2` with `RealDictCursor`. `DATABASE_URL` read from environment
(`os.environ`), public URL locally, private `${{ Postgres.DATABASE_URL }}` in
production. Same code path in both environments.

**Why:** Postgres is always-persistent by design (no volume config), free on
Railway's hobby tier, and queryable from a local machine via connection string,
which directly serves the eval/analytics goal. Raw psycopg2 keeps SQL transparent
and avoids learning an ORM for two tables and ~4 queries.

**Alternatives considered:** SQLite + persistent volume (rejected — recurring cost,
harder remote access). SQLite local / Postgres prod split (rejected — two code
paths, two placeholder syntaxes). SQLAlchemy ORM (rejected for v1 — machinery
unjustified at this scale; noted as a possible v1.1 if query complexity grows).

---

## ADR: Schema design — `searches` + `search_results`, impression-level logging

**Status:** Accepted

**Context:** Need to log both what was searched and what was shown, and to capture
positive feedback for eval.

**Decision:** Two tables. `searches` (search_id PK, raw_query, parsing_status,
semantic_query, keyword_query, searched_at). `search_results` (result_id PK,
search_id FK, racquet_id, rank, liked). One row per shown racquet at search time
with `liked` NULL; feedback updates it to 1. Thumbs-up only — `liked` is NULL or 1,
never 0.

**Why:** Logging every impression (not just liked ones) captures the implicit
negative signal (shown-and-ignored) needed for Hit@N/MRR analysis — the standard
impression-vs-engagement pattern. NULL default distinguishes "no feedback" from
"negative feedback," which a 0 default would collapse. Thumbs-up alone is
sufficient for the eval metric (which racquets users endorsed).

**Naming note:** Renamed from `impressions`/`impression_id` to
`search_results`/`result_id` for self-documenting clarity.

**Migration note:** `init_db()` uses `CREATE TABLE IF NOT EXISTS`, which does NOT
apply schema changes to existing tables. Future column additions require a manual
`ALTER TABLE` (Railway console) or idempotent `ADD COLUMN IF NOT EXISTS` in
`init_db()`.

---

## ADR: Match score computed server-side as integer percentage

**Status:** Accepted

**Context:** Raw RRF scores are tiny floats, meaningless in absolute terms, but
meaningful relatively. The frontend needs a displayable match indicator (based on user feedback).

**Decision:** Compute `racquet_match_score` in the search route as
`int((score / top_score) * 100)` — top result = 100%, others relative. Sent as an
integer field on `RacquetCard`.

**Why:** Normalization derives from retrieval internals (RRF scores); the client
shouldn't know those exist. Server-side keeps the API contract explicit and the
client math-free. This score communicates relative ranking, not absolute
quality. Consistent with the "Top result" badge copy chosen to avoid implying an
objective best match.

---

## ADR: Batched result inserts via `execute_values`

**Status:** Accepted

**Context:** Writing 1 search row + 20 result rows was 21 separate round trips.

**Decision:** Single `searches` insert, then one `execute_values` call for all 20
`search_results` rows. Rows collected in the existing card-building loop; both
inserts happen after the loop.

**Why:** `execute_values` collapses N rows into one multi-row INSERT — one round
trip, one parse/plan. Faster than `execute_batch` (which pipelines N executions)
for bulk same-table inserts. Building rows in the loop but inserting after keeps
"compute" and "persist" cleanly separated, and means a mid-loop failure writes
nothing. `searches` before `search_results` for the FK (checked at insert time).

---

## ADR: Rate limiting via slowapi, per-IP in-memory

**Status:** Accepted

**Context:** `/search` calls the paid Anthropic API. Without limits, abuse or a
traffic spike could burn credits or overwhelm the server.

**Decision:** `slowapi` with per-IP keying. `/search` at 10/min, `/feedback` at
30/min, `/health` unlimited. Shared `Limiter` instance in `app/limiter.py`,
imported by `main.py` and routers. `request: Request` param required on limited
routes (consumed by the decorator, not the body).

**Why:** Per-IP + time window is the standard, sufficient guardrail at this scale.
In-memory counters are fine — single instance, and a reset on restart is
acceptable. Redis-backed limiting deferred (seemed overengineered for anticipated deployment scale).

---

## ADR: Client picks provider — no dev parsing toggle in frontend

**Status:** Accepted (with noted alternative)

**Context:** A `DEV_SKIP_PARSING` flag exists in `app.js` to save API credits during
local testing.

**Decision:** Keep it as a hardcoded frontend constant, set to `false` for
production.

**Why:** The flag's visibility is harmless. A user flipping it in their own browser only
degrades that their own results; no data exposure or cost exploit. Decided to keep for ease of testing in local dev.

**Alternative recorded:** Move the toggle server-side (`os.environ` read in the
route, ignore any client `skip_parse`). Cleaner and un-manipulable by clients;
worth doing in v1.1 if it ever matters. Not worth the effort now.

---

## ADR: Design system — monochrome, no accent color, Inter, product-forward

**Status:** Accepted (supersedes the earlier TW-mimic design)

**Context:** Early frontend mimicked Tennis Warehouse's palette. Feedback: reads as
copying rather than integration unless the project is explicitly framed as a
TW-embedded tool. Also dropped the original warm-paper Frame Finder palette.

**Decision:** Fully monochrome (white/off-white/greys, black for emphasis only), no
accent color, single typeface (Inter). Racquet product photography is the only
color. Match-score bars and badges are monochrome. "Top result"
badge copy deliberately hedged (position, not quality claim).

**Why:** A standalone tool showing its own design judgment is a stronger portfolio
story than mimicking a retailer. Monochrome restraint reads as considered and
avoids the accent-heavy look that signals AI-generated design. Idea was to showcase a "futuristic" feel of being able to find relevant racquets by just writing out what you want rather than looking through a bunch of pages or racquet cards.

---

## v2 direction (recorded, not decided, pending eval data)

**Structured attribute retrieval.** The corpus already contains unused structured
specs (head size, strung weight, balance, stiffness, swing weight). v1 searches
only marketing copy + a few text fields. The likely retrieval ceiling is data
usage, not algorithm.

Leading design: a Pydantic filter DSL — `FilterCondition(column: ColumnEnum,
operator: OpEnum, value: float)`, parsed by the existing query parser into a list of
AND-ed conditions (ranges = two bounds on one column). Enums constrain the LLM to
valid columns/operators (also closes the SQL-injection surface, since column/operator
never come from raw LLM strings; value is parameterized).

Fusion approach: rank racquets by adherence to the structured conditions and pass
that as a **third ranked list into RRF** alongside semantic + BM25. This gives soft
constraint handling (a misparse of a structured field degrades a racquet's position rather than eliminating it)
**without reintroducing the defensible-weights problem** RRF was chosen to avoid.  Open modeling question:
how to turn binary constraint satisfaction into a ranking (count of satisfied
conditions, or distance-from-target).

Also cheap and worth doing regardless: surface specs on the cards (user value, no
retrieval change).

**Explicitly deferred:** hard filtering (over-elimination risk); soft
score-weighted ranking outside RRF (reintroduces weight-justification problem);
agentic grep retrieval (rejected — reintroduces lexical brittleness, slow/expensive
per query, doesn't fix the root data problem; the right version of that instinct is
LLM attribute extraction at ingestion, not query-time grep).

**Gate:** build the eval set FIRST. It determines whether structured filtering
helps or hurts before any of this is built.

---

## ADR: Query parsing temperature — DEFERRED (open experiment)

**Status:** Deferred — left at default for v1; revisit as a measured experiment

**Context:** Observed that identical queries could produce slightly different
`ParsedQuery` outputs across runs (LLM non-determinism), yielding slightly different
rankings for the same search. Raised the question of whether to cache queries, and
whether temperature=0 is appropriate given the parser involves some judgment in
mapping playability language to search terms.

**Provisional lean (not yet applied):** Setting `temperature=0` on the LLM calls in both `AnthropicAdapter` and
`GeminiAdapter` (top-level param for Anthropic `messages.parse`; inside
`GenerateContentConfig` for Gemini). No need to build query caching at this stage.

**Why:** The parser's two outputs are both faithful-interpretation/classification
tasks, not generation:
- `keyword_query` is constrained classification — map to a fixed vocabulary of
  category labels (power_level, stroke_style, swing_speed) or omit. There is a
  correct answer; sampling variety is pure downside.
- `semantic_query` is deliberately constrained by the prompt to "light cleanup
  only, not a full rewrite," leaving little legitimate creative surface.

I learned about how temperature controls *sampling variance*, not *judgment*. The model's
reasoning about what "arm-friendly" implies happens in the forward pass regardless
of temperature; temperature=0 just means "commit to the best interpretation
consistently" rather than "occasionally sample a less-likely one." For a search
*tool*, consistent application of judgment is desirable and variety is a defect.
This is the opposite of a generative task (writing, brainstorming) where variety is
the goal and higher temperature is correct. I did read that temperature=0 can cause infinite loops but I didn't read in depth about whether that is a common concern.

**Caveat:** temperature=0 is not perfectly deterministic in practice (provider-side
floating-point/batching effects), but it might reduce variation from "noticeably
different rankings" to "effectively stable," which resolves the original concern.

**On caching (rejected for now):** Caching would incidentally fix consistency but
primarily solves a cost/performance problem not present at this scale — exact-string
cache hit rate is low given natural-language query variety ("arm friendly racquet"
vs "easy on the arm" are different keys despite identical intent). temperature=0
addresses the consistency concern at the source for a one-line change. Decided to revisit
caching only if traffic and repeated-query rate justify it.

**Implementation seam noted:** the adapter is shared by query parsing and
distillation (both faithful-extraction, both fine at temperature=0), so hardcoding
temperature=0 in the adapter is acceptable. If a future task needs variety, I could promote
`temperature` to a `complete()` parameter rather than hardcoding.