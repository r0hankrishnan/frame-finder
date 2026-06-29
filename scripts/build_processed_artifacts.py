from pathlib import Path

import pandas as pd

from frame_finder.dataset import merge_racquet_data, create_keyword_text
from frame_finder.embed import (
    instantiate_embedding_model,
    create_corpus,
    embed_corpus,
    save_embeddings,
)
from frame_finder.config import EMBEDDING_MODEL_NAME

if __name__ == "__main__":
    PROJECT_ROOT = Path(__file__).resolve().parents[1]

    DATA_DIR = PROJECT_ROOT / "data"
    INTERIM_DIR = DATA_DIR / "interim"
    PROCESSED_DIR = DATA_DIR / "processed"

    CLEANED_RACQUET_DATA_PATH = INTERIM_DIR / "racquets_cleaned_2026_06_24.csv"
    DISTILLED_DESCRIPTIONS_PATH = INTERIM_DIR / "distilled_descriptions_2026_06_24.csv"

    cleaned_racquets_df = pd.read_csv(CLEANED_RACQUET_DATA_PATH)
    distilled_descriptions_df = pd.read_csv(DISTILLED_DESCRIPTIONS_PATH)

    merged_df = merge_racquet_data(
        cleaned_df=cleaned_racquets_df, distilled_df=distilled_descriptions_df
    )
    final_df = create_keyword_text(merged_df=merged_df)

    model = instantiate_embedding_model(model_name=EMBEDDING_MODEL_NAME)
    embedding_tuple = create_corpus(racquet_df=final_df)
    ids_and_embeddings_tuple = embed_corpus(
        corpus=embedding_tuple, embedding_model=model
    )

    save_embeddings(
        path=PROCESSED_DIR / "embedding_artifacts.npz",
        corpus_tuple=ids_and_embeddings_tuple,
    )
    final_df.to_csv(PROCESSED_DIR / "racquet_data_artifact.csv")
