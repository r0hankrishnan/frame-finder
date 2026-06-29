"""Module to create vector embeddings from corpus of racquet descriptions."""

import logging
from pathlib import Path

import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)


def instantiate_embedding_model(model_name: str) -> SentenceTransformer:
    logger.info(f"Instantiating {model_name}...")
    model = SentenceTransformer(model_name)
    logger.info(f"{model_name} instantiated!")
    return model


def create_corpus(racquet_df: pd.DataFrame) -> tuple[list[str], list[str]]:
    """Creates a 'corpus' of ids and distilled descriptions by creating a tuple
    of a list of racquet_id values and a list of their corresponding distilled_description
    values.

    Args:
        racquet_df (pd.DataFrame): The DataFrame to pull the id and description columns from.

    Raises:
        ValueError: Raised if DataFrame does not have racquet_id or distilled_description columns.

    Returns:
        tuple[list[str], list[str]]: A tuple of a list of racquet_id values and a list of their corresponding
        distilled_description values.
    """
    if "distilled_description" not in racquet_df:
        msg = "The racquet_df is missing a required column: distilled_description"
        logger.error(msg)
        raise ValueError(msg)

    if "racquet_id" not in racquet_df:
        msg = "The racquet_df is missing a required column: racquet_id"
        logger.error(msg)
        raise ValueError(msg)

    racquet_ids = racquet_df["racquet_id"].tolist()
    distilled_descriptions = racquet_df["distilled_description"].tolist()

    return racquet_ids, distilled_descriptions


def embed_corpus(
    corpus: tuple[list[str], list[str]], embedding_model: SentenceTransformer
) -> tuple[list[str], np.ndarray]:
    """Embeds distilled descriptions into an np.ndarray and returns a tuple
    of a list of racquet_id values and their corresponding embedding vectors
    in a np.ndarray.

    Args:
        corpus (tuple[list[str], list[str]]): Tuple of lists with the first list being a list of racquet_id values
        and the second list being a list of their corresponding distilled_description values.
        embedding_model (SentenceTransformer): The embedding model object instantiated by `instantiate_embedding_model()`.

    Raises:
        AssertionError: Raised if length of racquet_id list and length of distilled_description list are not equal (indicates mismatch
        between ids and descriptions).

    Returns:
        tuple[list[str], np.ndarray]: Tuple of list of racquet_id values and an np.ndarray of the embedding vectors of their
        corresponding distilled descriptions.
    """
    id_corpus = corpus[0]
    text_corpus = corpus[1]

    if len(id_corpus) != len(text_corpus):
        msg = (
            f"Critical length mismatch. Both lists must be the same length. "
            f"Got racquet_id list as length {len(id_corpus)} and distilled_description list as length {len(text_corpus)}."
        )
        logger.error(msg)
        raise AssertionError(msg)

    corpus_embeddings = embedding_model.encode(text_corpus, convert_to_numpy=True)

    return id_corpus, corpus_embeddings


def save_embeddings(
    path: Path | str, corpus_tuple: tuple[list[str], np.ndarray]
) -> None:
    """Saves a joint `.npz` file with two arrays. One array contains the racquet_id values. The other
    array contains the embedding vectors corresponding to the ids.

    Args:
        path (Path | str): Path to save embeddings
        embedding_corpus (tuple[list[str], np.ndarray]): Tuple containing racquet_id list and np.ndarray of embedded distilled_descriptions.

    Raises:
        AssertionError: Raised if length of racquet_id list and 0th dimension of embedding array are not equal (indicates mismatch
        between ids and descriptions).
    """
    racquet_ids = corpus_tuple[0]
    corpus_embeddings = corpus_tuple[1]

    if len(racquet_ids) != corpus_embeddings.shape[0]:
        msg = (
            f"Critical length mismatch. Both lists must be the same length. "
            f"Got racquet_id list as length {len(racquet_ids)} and distilled_description list as length {corpus_embeddings.shape[0]}."
        )
        logger.error(msg)
        raise AssertionError(msg)

    np.savez(
        path,
        racquet_ids=np.array(racquet_ids),
        embeddings=corpus_embeddings,
    )


def load_embeddings(path_to_embeddings: Path | str) -> tuple[np.ndarray, np.ndarray]:
    ids_and_embeddings = np.load(path_to_embeddings)
    ids = ids_and_embeddings["racquet_ids"]
    embeddings = ids_and_embeddings["embeddings"]

    return ids, embeddings


def embed_query(query: str, embedding_model: SentenceTransformer) -> np.ndarray:
    query_embedding = embedding_model.encode(query, convert_to_numpy=True)

    return query_embedding


def semantic_search(
    query_embedding: np.ndarray,
    racquet_ids: list[str] | np.ndarray,
    corpus_embeddings: np.ndarray,
) -> list[str]:
    if query_embedding.shape[0] != corpus_embeddings.shape[1]:
        msg = "Lengths of query and corpus embeddings do not match. Make sure to use the same embedding model for both parts."
        logger.error(msg)
        raise ValueError(msg)

    if isinstance(racquet_ids, np.ndarray):
        racquet_ids = racquet_ids.tolist()

    if len(racquet_ids) != corpus_embeddings.shape[0]:
        msg = (
            f"Critical length mismatch. Both lists must be the same length. "
            f"Got racquet_id list as length {len(racquet_ids)} and distilled_description list as length {corpus_embeddings.shape[0]}."
        )
        logger.error(msg)
        raise AssertionError(msg)

    similarity_vector = cosine_similarity(
        X=query_embedding.reshape(1, -1), Y=corpus_embeddings
    )[
        0
    ]  # shape: (1, corpus_embeddings.shape[0])
    sorted_indices = np.argsort(similarity_vector)[::-1]

    return [
        racquet_ids[int(idx)] for idx in sorted_indices
    ]  # added int() to satisfy type checker --> confirms that idx is an int index value
