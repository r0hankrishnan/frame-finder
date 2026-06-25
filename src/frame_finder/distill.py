import time
import csv
import logging
from pathlib import Path

from frame_finder.adapters import LLMAdapter

import pandas as pd
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class DistilledDescriptionItem(BaseModel):
    racquet_id: str = Field(description = "The id of the racquet.")
    distilled_description: str = Field(description = "The concise, feel-focused rewritten racquet description.")
    
class DistilledDescriptionBatch(BaseModel):
    descriptions: list[DistilledDescriptionItem] = Field(description = "An object containing a racquet_id and its corresponding rewritten description.")
        
def build_batch_prompts(racquets_df: pd.DataFrame, batch_size: int = 10) -> list[tuple[str, set[str]]]:
    """Takes in the cleaned racquet dataset and returns a list of paired prompts and expected racquet_ids 
    of size batch_size.
    Args:
        racquets_df (pd.DataFrame): DataFrame of racquets
        batch_size (int): Default to 10. Size to batch df.

    Returns:
        list[tuple[str, set[str]]]: List of pairs of prompt and racquet_id sets for each batch from racquet_df.
    
    """
    base_prompt = ("""You are helping build a semantic search tool for tennis racquets. Your job is to rewrite each racquet description into a concise, feel-focused summary that captures how the racquet actually plays.
    
    For each racquet, rewrite the description to focus only on:
        - Power level, control, and spin
        - How it feels on contact (stiff, plush, muted, crisp, etc.)
        - Maneuverability and stability
        - Who it suits (player level, style, swing speed)
        - Arm-friendliness if mentioned
        
    Accuracy is critical. Only include information explicitly stated in the original description. Do not infer, extrapolate, or invent characteristics. If arm-friendliness is not mentioned, do not include it. If power level is not described, do not guess.
    
    Keep each rewritten description to 2-4 sentences. If a description contains no usable feel or performance content, return an empty string for that racquet's distilled_description field.
    
    Here are the racquets to process:""")
        
    batch_groups: list[tuple[str, set[str]]] = []
    
    for start in range (0, len(racquets_df), batch_size):
        chunk = racquets_df.iloc[start: start + batch_size][["racquet_id", "racquet_description"]]
        
        batch_text = ""
        
        for _, row in chunk.iterrows():
            batch_text += f"racquet_id: {row["racquet_id"]}\nracquet_description: {row["racquet_description"]}\n\n"
        
        batch_prompt: str = base_prompt + "\n\n" + batch_text
        batch_racquet_ids: set[str] = set(chunk["racquet_id"])
        
        batch_group: tuple[str, set[str]] = (batch_prompt, batch_racquet_ids)
        batch_groups.append(batch_group)
        
    return batch_groups

def distill_descriptions(racquets_df: pd.DataFrame, llm_adapter: LLMAdapter, output_format: type[DistilledDescriptionBatch], 
                         partial_save_path: Path, batch_size: int = 10) -> list[DistilledDescriptionItem]: 
    """Takes in the cleaned racquet dataset and returns a list of dicts with each racquet's
    distilled description. 

    Args:
        racquets_df (pd.DataFrame): DataFrame of racquets
        llm_adapter (LLMAdapter): Apadater class (should be interchangeable to allow for testing different providers)
        partial_save_path (Path): Path to save partial runs to.
        batch_size (int): Default to 10. Parameter to pass to `build_batch_prompts`

    Returns:
        list[dict]: List of dicts where each dict is one row from racquets_df with keys racquet_id and distilled_description
    """
    
    batched_groups = build_batch_prompts(racquets_df=racquets_df, batch_size=batch_size)
    distilled_desc_items = []
    
    # Add retry logic
    for batch_num, (prompt, expected_ids) in enumerate(batched_groups, start=1):
        logger.info(f"Processing batch {batch_num} / {len(batched_groups)}...")
        
        for i in range(0,3): # Tries 3 times, breaks if fails 3 times
            try:
                distilled_batch = llm_adapter.complete(prompt=prompt, output_format=output_format) # Get distilled descs
                distilled_descs = distilled_batch.descriptions
                
                returned_ids = set(item.racquet_id for item in distilled_descs) # Check length + racquet_ids
                
                if expected_ids != returned_ids or len(expected_ids) != len(distilled_descs):
                    msg = f"Batch {batch_num} mismatch. Expected {len(expected_ids)} unique IDs {expected_ids}, got {len(distilled_descs)} items with IDs {returned_ids}."
                    logger.error(msg)
                    raise ValueError(msg)
          
            except Exception as e:
                if i < 2:
                    time.sleep(2 ** (i + 1))
                    continue
                
                else:
                    _save_partial(items=distilled_desc_items, path=partial_save_path)
                    
                    logger.error(f"Failed on batch {batch_num} after 3 attempts: {e}")
                    raise Exception(f"Pipeline failed on batch {batch_num}. Partial results saved to {partial_save_path}.") 
                     
            else:
                # Unpack into top-level list
                distilled_desc_items.extend(distilled_descs)
                time.sleep(1)
                break
    
    if len(distilled_desc_items) != len(racquets_df):
        _save_partial(items=distilled_desc_items, path=partial_save_path)
        msg = f"Row count mismatch: input had {len(racquets_df)} rows but got {len(distilled_desc_items)}."
        logger.error(msg)
        raise AssertionError(msg)
    
    return distilled_desc_items


def _save_partial(items: list[DistilledDescriptionItem], path: Path) -> None:
    with open(path / "partially_distilled_descs.csv", "w", newline="") as f:
        fieldnames = ["racquet_id", "distilled_description"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for item in items:
            writer.writerow(item.model_dump())