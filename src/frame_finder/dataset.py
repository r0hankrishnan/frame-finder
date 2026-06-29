"""Module to combine cleaned data with distilled descriptions."""

import logging

import pandas as pd

logger = logging.getLogger(__name__)


def merge_racquet_data(
    cleaned_df: pd.DataFrame, distilled_df: pd.DataFrame
) -> pd.DataFrame:
    """Merges cleaned racquet specs with distilled descriptions on racquet_id.

    Args:
        cleaned_df (pd.DataFrame): The cleaned dataframe containing all racquet features.
        distilled_df (pd.DataFrame): The dataframe containing the distilled racquet descriptions and their corresponding racquet_id values.

    Raises:
        ValueError: Raises if there is a length mismatch after merging (indicates rows were dropped)

    Returns:
        pd.DataFrame: Dataframe of all racquets, their features, and their corresponding distilled description.
    """
    merged = cleaned_df.merge(
        distilled_df, on="racquet_id", how="inner", validate="one_to_one"
    )

    if len(merged) != len(cleaned_df):
        msg = f"Merge dropped rows: cleaned_df had {len(cleaned_df)} rows, merged has {len(merged)}."
        logger.error(msg)
        raise ValueError(msg)

    return merged


def create_keyword_text(merged_df: pd.DataFrame) -> pd.DataFrame:
    """Creates a keyword_text column by concatenating racquet_name, the three
    small categorical spec fields, and distilled_description. This column is
    the corpus text indexed by BM25 for lexical search.

    Must run after distillation output has been merged into racquet_df, since
    distilled_description is a required input column.

    Args:
        racquet_df (pd.DataFrame): DataFrame that must already contain
        racquet_name, racquet_power_level, racquet_stroke_style,
        racquet_swing_speed, and distilled_description columns.

    Raises:
        ValueError: Raised if any required column is missing.

    Returns:
        pd.DataFrame: Copy of racquet_df with a new keyword_text column appended.
    """
    required_cols = [
        "racquet_name",
        "racquet_power_level",
        "racquet_stroke_style",
        "racquet_swing_speed",
        "distilled_description",
    ]

    missing = [col for col in required_cols if col not in merged_df.columns]

    if missing:
        msg = f"The merged_df is missing required column(s): {missing}"
        logger.error(msg)
        raise ValueError(msg)

    out = merged_df.copy()
    out["keyword_text"] = (
        out["racquet_name"].fillna("")
        + " "
        + out["racquet_power_level"].fillna("")
        + " "
        + out["racquet_stroke_style"].fillna("")
        + " "
        + out["racquet_swing_speed"].fillna("")
        + " "
        + out["distilled_description"].fillna("")
    )

    return out
