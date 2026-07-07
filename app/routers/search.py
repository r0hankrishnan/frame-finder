import uuid
import os
import logging
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, Request, BackgroundTasks
from fastapi.concurrency import run_in_threadpool
import psycopg2
import psycopg2.extras

from app.dependencies import get_engine
from app.schemas import SearchRequest, SearchResponse, RacquetCard
from app.limiter import limiter
from frame_finder.engine import RacquetSearchEngine

router = APIRouter()

logger = logging.getLogger(__name__)

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


def log_search_request(
    searches_row: tuple[
        str, str, Literal["success", "skipped", "failed"], str | None, str | None, str
    ],
    search_results_rows: list[tuple[str, str, str, int, None]],
) -> None:
    """Function that opens a DB and cursor connection, writes a single row to the searches table
    to record the key query metadata, then writes 20 rows to the search_results table where each row
    represents one returned racquet.

    Args:
        searches_row (tuple[str, str, Literal['success', 'skipped', 'failed'], str | None, str | None, str]): A tuple of search metadata in the following order:
            search ID, raw query, parsing status, semantic query, keyword query, current timestamp
        search_results_rows (list[str | int | None]): A list of 20 tuples where each tuple is one of the 20 returned racquets from the user's query.
            The tuple values are the following: result ID, search ID, racquet ID, rank, None (placeholder for whether user liked racquet or not)
    """
    con = None
    cur = None
    try:
        # Get connection and cursor
        con = psycopg2.connect(os.environ["DATABASE_URL"])
        cur = con.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Write to searches
        cur.execute(
            "INSERT INTO searches VALUES (%s, %s, %s, %s, %s, %s)", searches_row
        )

        # Write to impressions as a batch of 20
        psycopg2.extras.execute_values(
            cur=cur,
            sql="INSERT INTO search_results (result_id, search_id, racquet_id, rank, liked) VALUES %s",
            argslist=search_results_rows,
        )

        con.commit()  # send to DB

    except Exception:
        logger.exception("Failed to log search in database")

    finally:
        if cur is not None:
            cur.close()

        if con is not None:
            con.close()


@router.post("/search")
@limiter.limit("10/minute")
async def search(
    request: Request,
    body: SearchRequest,
    background_tasks: BackgroundTasks,
    engine: RacquetSearchEngine = Depends(get_engine),
):
    now = datetime.now(timezone.utc).isoformat()
    search_id = str(uuid.uuid4())
    raw_query = body.query

    result = await run_in_threadpool(engine.search, body.query, body.skip_parse)
    parsing_status = (
        result.parsing_status.value
    )  # now it's just a Literal of the ENUM strings not the ENUM type itself

    semantic_query = result.parsed_query.semantic_query if result.parsed_query else None
    keyword_query = result.parsed_query.keyword_query if result.parsed_query else None

    searches_row = (
        search_id,
        raw_query,
        parsing_status,
        semantic_query,
        keyword_query,
        now,
    )

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

    # Write to DB in the background
    background_tasks.add_task(
        log_search_request,
        searches_row=searches_row,
        search_results_rows=search_results_rows,
    )

    return SearchResponse(
        search_id=search_id, parsing_status=result.parsing_status, results=cards
    )
