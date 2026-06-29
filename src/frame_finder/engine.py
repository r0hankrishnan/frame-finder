"""Module holding RacquetSearchEngine class which orchestrates full hybrid search process"""

from pathlib import Path
from enum import Enum
from typing import NamedTuple
import logging

from frame_finder.bm25 import create_corpus, instantiate_and_index_bm25, bm25_search
from frame_finder.embed import (
    instantiate_embedding_model,
    load_embeddings,
    embed_query,
    semantic_search,
)
from frame_finder.parse_query import parse_query, ParsedQuery
from frame_finder.adapters import LLMAdapter

import pandas as pd
from pydantic import BaseModel
from bm25s import BM25
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class ParsingStatus(Enum):
    SUCCESS = "success"
    SKIPPED = "skipped"  # caller passed skip_parsing=True
    FAILED = "failed"  # parsing was attempted but raised an exception


class SearchResult(BaseModel):
    fused_result: list[tuple[str, float]]
    parsed_query: ParsedQuery | None
    parsing_status: ParsingStatus


class ResolvedQuery(NamedTuple):
    semantic_query: str
    keyword_query: str
    parsed_query: ParsedQuery | None
    parsing_status: ParsingStatus


class RacquetSearchEngine:
    def __init__(
        self, path_to_artifacts: Path | str, embedder_name: str, llm_adapter: LLMAdapter
    ):
        self.path_to_artifacts = (
            Path(path_to_artifacts)
            if not isinstance(path_to_artifacts, Path)
            else path_to_artifacts
        )
        self.llm_adapter = llm_adapter
        self.embedder_name = embedder_name
        self.embedder = None
        self.embedding_tuple = None
        self.bm25_tuple = None
        self.bm25_retriever = None
        self.racquet_df = pd.read_csv(
            self.path_to_artifacts / "racquet_data_artifact.csv"
        )

    def instantiate_embedder(self) -> None:
        """Instantiates the named embedding model using SentenceTransformers.

        Returns:
            None: No return value. Just sets self.embedder to the embedding model's instance.
        """
        if self.embedder is not None:
            logger.info(
                f"Embedder already instantiated with model: {self.embedder_name}"
            )
            return None

        self.embedder = instantiate_embedding_model(
            model_name=self.embedder_name
        )  # Logs message about instantiating already
        return None

    def load_embeddings(self) -> None:
        """Loads .npz file of embeddings, unpacks it into a tuple of np.ndarrays and
        sets the tuple as an attribute of the class instance.
        """
        self.embedding_tuple = load_embeddings(
            path_to_embeddings=self.path_to_artifacts / "embedding_artifacts.npz"
        )

    def create_bm25_tuple(self) -> None:
        """Takes stored racquet_df and creates a tuple of two lists.
        The first list is a list of racquet_id values. The second list is a list
        of corresponding `keyword_text` values.

        Returns:
            None: No return value. Just sets the tuple as an attribute of the class.
        """
        if self.bm25_tuple is not None:
            logger.info("Tuple already created")
            return None

        self.bm25_tuple = create_corpus(racquet_df=self.racquet_df)

    def instantiate_bm25(self) -> None:
        """Instantiates and indexes the bm25 retriever.
        Unpacks and uses self.bm25_tuple to set metadata corpus (`racquet_id`)
        and to index (`keyword_text`).

        Raises:
            ValueError: Raised if self.bm25_tuple is None which means you need to call `.create_bm25_tuple()` method.

        Returns:
            None: No return value. Just sets self.bm25_retriever to bm25 retriver instance.
        """
        if self.bm25_retriever is not None:
            logger.info("BM25 retriever already initialized and indexed.")
            return None

        if self.bm25_tuple is None:
            msg = (
                "self.bm25_tuple is None. Cannot instantiate retriever without corpus tuples. "
                "Please run `.create_bm25_tuple` method first and then try again."
            )
            logger.error(msg)
            raise ValueError(msg)

        self.bm25_retriever = instantiate_and_index_bm25(corpus=self.bm25_tuple)

    def setup(self) -> None:
        """Orchestration method to run the above setup methods in succession. Allows user to
        call one method rather than 4.

        Returns:
            None: Runs 4 internal setup functions in succession. No object returned.
        """
        # Step 1: Instantiate embedder
        self.instantiate_embedder()

        # Step 2: Load embeddings
        self.load_embeddings()

        # Step 3: Create BM25 tuple
        self.create_bm25_tuple()

        # Step 4: Instantiate and index BM25 retriever
        self.instantiate_bm25()

        return None

    def search(
        self, query: str, skip_parsing: bool = False
    ) -> SearchResult:  # list[tuple[str, float]]:
        """Orchestration that runs full hybrid search workflow given a user query string.
        First, tries to parse query with LLM (defaults to raw str if fails). Then, embeds
        the query with self.embedder and stores semantic search results. Then stores BM25
        search results. Then passes both to `reciprocal_rank_fusion()` method to get final
        rankings of racquet_id values and their corresponding scores. If the query parser
        returns an empty string for `keyword_query`, we only pass the semantic search results
        through to the reciprocal rank fusion step.

        Args:
            query (str): Raw text query entered by user, sanitized by FastAPI route, and passed to class instance.

        Raises:
            ValueError: Raised if self.embedder was not intialized. Call `.instantiate_embedder` first.
            ValueError: Raised if self.embedding_tuple does not exist. Call `.load_embeddings` first.
            ValueError: Raised if self.bm25_retriever was not intialized. Call `.instantiate_bm25` first.

        Returns:
            SearchResult: An object containing the RRF results as a list[tuple[str, float]], the parsed query (if used) as
            a ParsedQuery object (or None if not used), and an enum indicating whether the query parsing step was skipped, succeed, or failed.
        """
        # Instantiation checks -> will raise if they don't pass
        embedder, embedding_tuple, bm25_retriever = self._check_ready()

        resolved_query = self._resolve_query(
            query=query, skip_parsing=skip_parsing, llm_adapter=self.llm_adapter
        )

        semantic_query_embedding = embed_query(
            query=resolved_query.semantic_query, embedding_model=embedder
        )
        semantic_search_results = semantic_search(
            query_embedding=semantic_query_embedding,
            racquet_ids=embedding_tuple[0],
            corpus_embeddings=embedding_tuple[1],
        )

        if not (resolved_query.keyword_query).strip():
            fused_result = self._reciprocal_rank_fusion(semantic_search_results)
            return SearchResult(
                fused_result=fused_result,
                parsed_query=resolved_query.parsed_query,
                parsing_status=resolved_query.parsing_status,
            )

        bm25_search_results = bm25_search(
            query=resolved_query.keyword_query, retriever=bm25_retriever
        )
        fused_result = self._reciprocal_rank_fusion(
            semantic_search_results, bm25_search_results
        )

        return SearchResult(
            fused_result=fused_result,
            parsed_query=resolved_query.parsed_query,
            parsing_status=resolved_query.parsing_status,
        )

    def _resolve_query(
        self, query: str, skip_parsing: bool, llm_adapter: LLMAdapter
    ) -> ResolvedQuery:
        """Takes a raw query and resolves it to a ResolvedQuery object containing a semantic_query, keyword_query,
        parsed_query, and parsing_status. Takes into account skip_pasing flag and uses try/except block to catch
        failed LLM parsing and fallback to raw query string.

        Args:
            query (str): The received raw query string.
            skip_parsing (bool): Boolean flag from `.search()` method indicating whether or not to skip LLM parsing.
            llm_adapter (LLMAdapter): The LLM adapter to use.

        Returns:
            ResolvedQuery: A NamedTuple object with semantic_query (str), keyword_query (str),
            parsed_query (ParsedQuery | None), and parsing_status (ParsingStatus) fields. The parsed_query field is set to None when LLM parsing
            is skipped or fails.
        """
        if skip_parsing:
            return ResolvedQuery(
                semantic_query=query,
                keyword_query=query,
                parsed_query=None,
                parsing_status=ParsingStatus.SKIPPED,
            )

        else:
            try:
                parsed_query = parse_query(query=query, llm_adapter=llm_adapter)
                return ResolvedQuery(
                    semantic_query=parsed_query.semantic_query,
                    keyword_query=parsed_query.keyword_query,
                    parsed_query=parsed_query,
                    parsing_status=ParsingStatus.SUCCESS,
                )
            except Exception as e:
                logger.warning(
                    f"Query parsing failed, falling back to raw query for both semantic and keyword search: {e}"
                )
                return ResolvedQuery(
                    semantic_query=query,
                    keyword_query=query,
                    parsed_query=None,
                    parsing_status=ParsingStatus.FAILED,
                )

    def _check_ready(self) -> tuple[SentenceTransformer, tuple, BM25]:
        """Private helper that runs checks to make sure all
        necessary attributes are properly instantiated before search.

        Raises:
            ValueError: Raised if self.embedder was not intialized. Call `.instantiate_embedder` first.
            ValueError: Raised if self.embedding_tuple does not exist. Call `.load_embeddings` first.
            ValueError: Raised if self.bm25_retriever was not intialized. Call `.instantiate_bm25` first.

        Returns:
            None: Returns None. Only used to catch errors.
        """
        if self.embedder is None:
            msg = "No embedding model has been initialized. Please run `instantiate_embedder` method first and then try again."
            logger.error(msg)
            raise ValueError(msg)

        if self.embedding_tuple is None:
            msg = (
                "The racquet_id values and their corresponding vector embeddings have not been loaded and stored. "
                "Please run the `.load_embeddings` method and then try again."
            )
            logger.error(msg)
            raise ValueError(msg)

        if self.bm25_retriever is None:
            msg = "The BM25 retriever object has not been initialized. Please run the `instantiate_bm25` method and try again."
            logger.error(msg)
            raise ValueError(msg)

        return self.embedder, self.embedding_tuple, self.bm25_retriever

    @staticmethod
    def _reciprocal_rank_fusion(
        *ranked_id_lists: list[str], k: int = 60
    ) -> list[tuple[str, float]]:
        """Runs reciprocal rank fusion on any number of lists. Created by following canonical equation
        for RRF.

        Args:
            k (int, optional): Smoothing constant. Defaults to 60.

        Returns:
            list[tuple[str, float]]: A list of tuples where each tuple is a racquet_id, RRF score pair sorted from highest
            to lowest RRF score.
        """
        scores: dict[str, float] = {}

        for ranked_id_list in ranked_id_lists:
            for rank, racquet_id in enumerate(ranked_id_list, start=1):
                scores[racquet_id] = scores.get(racquet_id, 0.0) + (1 / (k + rank))

        return sorted(scores.items(), key=lambda item: item[1], reverse=True)
