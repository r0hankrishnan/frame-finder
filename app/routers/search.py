import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from fastapi.concurrency import run_in_threadpool
import psycopg2
import psycopg2.extras

from app.dependencies import get_engine, get_db
from app.schemas import SearchRequest, SearchResponse, RacquetCard
from app.limiter import limiter
from frame_finder.engine import RacquetSearchEngine

router = APIRouter()

CARD_COLS = [
    "racquet_name",
    "racquet_url",
    "racquet_img",
    "racquet_rating",
    "racquet_rating_count",
    "racquet_price",
    "racquet_description",
]
TOP_N = 20


@router.post("/search")
@limiter.limit("10/minute")
async def search(
    request: Request,
    body: SearchRequest,
    engine: RacquetSearchEngine = Depends(get_engine),
    db: psycopg2.extras.RealDictCursor = Depends(get_db),
):

    now = datetime.now(timezone.utc).isoformat()
    search_id = str(uuid.uuid4())
    raw_query = body.query

    result = await run_in_threadpool(engine.search, body.query, body.skip_parse)
    parsing_status = result.parsing_status.value  # now it's just "success" etc.

    semantic_query = result.parsed_query.semantic_query if result.parsed_query else None
    keyword_query = result.parsed_query.keyword_query if result.parsed_query else None

    cards = []
    search_results_rows = []
    top_score = result.fused_result[0][1]
    for rank, (racquet_id, score) in enumerate(result.fused_result[0:TOP_N], start=1):
        result_id = str(uuid.uuid4())
        racquet = engine.get_racquet(racquet_id=racquet_id, cols_to_get=CARD_COLS)
        racquet_match_score = int((score / top_score) * 100)

        racquet_card = RacquetCard(
            racquet_id=racquet_id,
            racquet_rank=rank,
            racquet_name=racquet["racquet_name"],
            racquet_url=racquet["racquet_url"],
            racquet_img=racquet["racquet_img"],
            racquet_rating=racquet["racquet_rating"],
            racquet_rating_count=racquet["racquet_rating_count"],
            racquet_price=racquet["racquet_price"],
            racquet_description=racquet["racquet_description"],
            racquet_match_score=racquet_match_score,
        )
        cards.append(racquet_card)
        search_results_rows.append((result_id, search_id, racquet_id, rank, None))

    # Write to searches
    db.execute(
        "INSERT INTO searches VALUES (%s, %s, %s, %s, %s, %s)",
        (search_id, raw_query, parsing_status, semantic_query, keyword_query, now),
    )

    # Write to impressions as a batch of 20
    psycopg2.extras.execute_values(
        db,
        "INSERT INTO search_results (result_id, search_id, racquet_id, rank, liked) VALUES %s",
        search_results_rows,
    )

    return SearchResponse(
        search_id=search_id, parsing_status=result.parsing_status, results=cards
    )
