"""Route to log/store when a user marks a racquet with a thumbs up"""
import logging

from fastapi import APIRouter, Depends, Request
import psycopg2
import psycopg2.extras

from app.schemas import FeedbackRequest
from app.dependencies import get_db
from app.limiter import limiter

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/feedback")
@limiter.limit("30/minute")
async def feedback(request: Request,
                   body:FeedbackRequest,
                   db: psycopg2.extras.RealDictCursor = Depends(get_db)
                   ) -> None:
    
    liked = 1 if body.liked else None
    
    db.execute("UPDATE search_results SET liked = %s WHERE search_id = %s AND racquet_id = %s",
               (liked, body.search_id, body.racquet_id))
    
    if db.rowcount == 0:
        logger.warning(f"Feedback update matched no rows: search_id={body.search_id} racquet_id={body.racquet_id}")