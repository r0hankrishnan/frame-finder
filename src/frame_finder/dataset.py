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
