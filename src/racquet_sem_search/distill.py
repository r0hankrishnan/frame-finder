import time
import csv
import logging
from abc import ABC, abstractmethod
from pathlib import Path

import anthropic
import pandas as pd
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class DistilledDescriptionItem(BaseModel):
    racquet_id: str
    distilled_description: str
    
class DistilledDescriptionBatch(BaseModel):
    descriptions: list[DistilledDescriptionItem]

class LLMAdapter(ABC):
    @abstractmethod
    def complete(self, prompt: str) -> list[DistilledDescriptionItem]:
        pass
    
class AnthropicAdapter(LLMAdapter):
    def __init__(self):
        self.client = anthropic.Anthropic()
        
    def complete(self, prompt: str) -> list[DistilledDescriptionItem]:
        """Generate a strucutred output completion from a given prompt.

        Args:
            prompt (str): Prompt (created from build_batch_prompt)

        Returns:
            list[DistilledDescriptionItem]: List of DistilledDescriptionItem objects. Each object should have
            racquet_id and distilled_description. 
        """
        message = self.client.messages.parse(
            model="claude-haiku-4-5-20251001", 
            max_tokens=4096, 
            messages=[{"role": "user", "content": prompt,}],
            output_format=DistilledDescriptionBatch,
            )
        
        content = message.parsed_output.descriptions
        
        return content
    

def build_batch_prompts(racquets_df: pd.DataFrame, batch_size: int = 10) -> list[str]:
    """Takes in the cleaned racquet dataset and returns a list of prompts of size batch_size.
    Args:
        racquets_df (pd.DataFrame): DataFrame of racquets
        batch_size (int): Default to 10. Size to batch df.

    Returns:
        list[str]: List of strings where each string is the prompt for a batch from racquets_df. 
    
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
        
    batch_prompts = []
    
    for start in range (0, len(racquets_df), batch_size):
        chunk = racquets_df.iloc[start: start + batch_size][["racquet_id", "racquet_description"]]
        
        batch_text = ""
        
        for _, row in chunk.iterrows():
            batch_text += f"racquet_id: {row["racquet_id"]}\nracquet_description: {row["racquet_description"]}\n\n"
        
        batch_prompt = base_prompt + "\n\n" + batch_text
        batch_prompts.append(batch_prompt)
        
    return batch_prompts

def distill_descriptions(racquets_df: pd.DataFrame, llm_adapter: LLMAdapter, 
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
    
    batched_prompts = build_batch_prompts(racquets_df=racquets_df, batch_size=batch_size)
    distilled_desc_items = []
    
    # Add retry logic
    for batch_num, prompt in enumerate(batched_prompts, start=1):
        logger.info(f"Processing batch {batch_num} / {len(batched_prompts)}...")
        for i in range(0,3): # Tries 3 times, breaks if fails 3 times
            try:
                distilled_descs = llm_adapter.complete(prompt=prompt) # Get distilled descs
                
            except Exception as e:
                if i < 2:
                    time.sleep(2 ** (i + 1))
                    continue
                
                else:
                    with open(partial_save_path / "partially_distilled_descs.csv", "w", newline="") as f:
                        fieldnames = ["racquet_id", "distilled_description"]
                        writer = csv.DictWriter(f, fieldnames=fieldnames)

                        writer.writeheader()
                        for item in distilled_desc_items:
                            writer.writerow(item.model_dump())
                    
                    logger.error(f"Failed on batch {batch_num} after 3 attempts: {e}")
                    raise Exception(f"Pipeline failed on batch {batch_num}. Partial results saved to {partial_save_path}.") 
                     
            else:
                # Unpack into top-level list
                distilled_desc_items.extend(distilled_descs)
                time.sleep(1)
                break
    
    if len(distilled_desc_items) != len(racquets_df):
        msg = f"Row count mismatch: input had {len(racquets_df)} rows but got {len(distilled_desc_items)}."
        logger.error(msg)
        raise AssertionError(msg)
    
    return distilled_desc_items
        