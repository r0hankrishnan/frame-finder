"""Module to parse query into semantic and keyword components."""

from __future__ import annotations
import logging

from frame_finder.adapters import LLMAdapter
from frame_finder.config import QUERY_PARSING_BASE_PROMPT

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ParsedQuery(BaseModel):
    semantic_query: str = Field(
        description=(
            "A natural-language rephrasing of the user's query capturing the desired "
            "playing feel, characteristics, or use case (e.g. power, control, comfort, "
            "spin, maneuverability, player level). Used for cosine-similarity search "
            "against semantic racquet descriptions. Should stay close to the user's "
            "original phrasing and intent — light cleanup only, not aggressive rewriting."
        )
    )
    keyword_query: str = Field(
        description=(
            "A space-separated string of terms extracted or mapped from the user's query "
            "for lexical (BM25) search. Should include: any racquet brand or model names "
            "mentioned verbatim, and the closest matching racquet_power_level, "
            "racquet_stroke_style, and racquet_swing_speed category label(s) if the query "
            "implies them. Omit a category entirely if the query gives no signal for it — "
            "do not guess a default."
        )
    )


def parse_query(query: str, llm_adapter: LLMAdapter) -> ParsedQuery:
    prompt = QUERY_PARSING_BASE_PROMPT + f"\n{query}"
    parsed_query = llm_adapter.complete(prompt=prompt, output_format=ParsedQuery)

    return parsed_query
