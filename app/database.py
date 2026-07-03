"""File defines init and get functions for Postgres DB to track logs and feedback"""

import os
import psycopg2


def init_db():
    con = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = con.cursor()

    cur.execute(
        """
                CREATE TABLE IF NOT EXISTS searches(
                    search_id TEXT PRIMARY KEY,
                    raw_query TEXT NOT NULL,
                    parsing_status  TEXT NOT NULL,
                    semantic_query TEXT,
                    keyword_query TEXT,
                    searched_at TEXT NOT NULL
                )
                """
    )
    cur.execute(
        """
                CREATE TABLE IF NOT EXISTS search_results(
                    result_id TEXT PRIMARY KEY,
                    search_id TEXT NOT NULL,
                    racquet_id TEXT NOT NULL,
                    rank INTEGER NOT NULL,
                    liked INTEGER,
                    FOREIGN KEY (search_id) REFERENCES searches(search_id)
                )
                """
    )

    con.commit()
    cur.close()
    con.close()
