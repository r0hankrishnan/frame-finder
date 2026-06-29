"""Module to implement BM25 indexing and search"""

import logging

import pandas as pd
import bm25s

logger = logging.getLogger(__name__)


def create_corpus(racquet_df: pd.DataFrame) -> tuple[list[str], list[str]]:
    """Creates a 'corpus' of ids and keyword text by creating a tuple of a list of
    racquet_id values and a list of their corresponding keyword_text values.

    Args:
        racquet_df (pd.DataFrame): The DataFrame to pull the id and keyword text columns from.

    Raises:
        ValueError: Raised if DataFrame does not have racquet_id or keyword_text columns.

    Returns:
        tuple[list[str], list[str]]: A tuple of a list of racquet_id values and a list of their
        corresponding keyword_text values.
    """

    if "keyword_text" not in racquet_df:
        msg = "The racquet_df is missing a required column: keyword_text"
        logger.error(msg)
        raise ValueError(msg)

    if "racquet_id" not in racquet_df:
        msg = "The racquet_df is missing a required column: racquet_id"
        logger.error(msg)
        raise ValueError(msg)

    racquet_ids = racquet_df["racquet_id"].tolist()
    keyword_texts = racquet_df["keyword_text"].tolist()

    return racquet_ids, keyword_texts


def instantiate_and_index_bm25(corpus: tuple[list[str], list[str]]) -> bm25s.BM25:
    """Builds a BM25 retriever indexed on keyword_text, with racquet_id set as the
    corpus lookup so that retrieval returns racquet_id values directly rather than
    raw keyword text.

    Note: corpus= on the underlying bm25s.BM25 object is racquet_ids, not keyword_text.
    This means retriever.retrieve() returns racquet_id values, not the text that was
    actually scored against.

    Args:
        corpus (tuple[list[str], list[str]]): Tuple of lists with the first list being a list of
        racquet_id values and the second list being a list of their corresponding keyword_text
        values.

    Raises:
        AssertionError: Raised if length of racquet_id list and length of keyword_text list are
        not equal (indicates mismatch between ids and keyword text).

    Returns:
        bm25s.BM25: A fitted BM25 retriever whose corpus is racquet_id values, indexed on the
        tokenized keyword_text values.
    """

    racquet_ids = corpus[0]
    keyword_texts = corpus[1]

    if len(racquet_ids) != len(keyword_texts):
        msg = f"Critical length mismatch. Racquet ids list is length {len(racquet_ids)} while keyword texts list is {len(keyword_texts)}."
        logger.error(msg)
        raise AssertionError(msg)

    retriever = bm25s.BM25(corpus=racquet_ids)
    retriever.index(bm25s.tokenize(keyword_texts))

    return retriever


def bm25_search(query: str, retriever: bm25s.BM25) -> list[str]:
    if retriever.corpus is None:
        msg = (
            "Retriever corpus returning None. This means the retreiver was not intialized correctly."
            "Rerun `instantiate_and_index_bm25()`."
        )
        logger.error(msg)
        raise ValueError(msg)

    k = len(retriever.corpus)

    sorted_ids, scores = retriever.retrieve(
        bm25s.tokenize(query), k=k
    )  # Leaving scores unused in case it becomes useful later

    return sorted_ids[
        0
    ]  # Results is always a nested list so need to index in one layer
