"""Defines functions to return objects needed as dependencies in routes."""
import os
from typing import Generator

from fastapi.requests import Request
import psycopg2
import psycopg2.extras

from frame_finder.engine import RacquetSearchEngine

def get_engine(request: Request) -> RacquetSearchEngine:
    return request.app.state.engine

def get_db() -> Generator[psycopg2.extras.RealDictCursor]:
    con = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = con.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        yield cur
    finally:
        con.commit()
        cur.close()
        con.close()