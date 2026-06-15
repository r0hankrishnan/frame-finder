from abc import ABC, abstractmethod

import anthropic
from pydantic import BaseModel
import pandas as pd

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
    
    Keep each rewritten description to 2-4 sentences. If a description contains no usable feel or performance content, leave it empty.
    
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

def distill_descriptions(racquets_df: pd.DataFrame, llm_adapter: LLMAdapter) -> list[dict]: 
    """Takes in the cleaned racquet dataset and returns a list of dicts with each racquet's
    distilled description. 

    Args:
        racquets_df (pd.DataFrame): DataFrame of racquets
        llm_adapter (LLMAdapter): Apadater class (should be interchangeable to allow for testing different providers)

    Returns:
        list[dict]: List of dicts where each dict is one row from racquets_df with keys racquet_id and distilled_description
    """
    ...