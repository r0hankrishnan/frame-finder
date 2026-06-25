from abc import ABC, abstractmethod
from typing import TypeVar
import logging

import anthropic
from google import genai
from pydantic import BaseModel

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

class LLMAdapter(ABC):
    @abstractmethod
    def complete(self, prompt: str, output_format: type[T]) -> T:
        pass
    
class AnthropicAdapter(LLMAdapter):
    def __init__(self):
        self.client = anthropic.Anthropic()
        
    def complete(self, prompt: str, output_format: type[T]) -> T:
        """Generate a structured output from a given prompt and output_format.
        
        Args:
            prompt (str):Prompt passed to LLM
            output_format (type[T]): Pydantic model defining output format
            
        Returns: 
            T: Defined BaseModel format of output (depends on output_format parameter). 
        
        """
        message = self.client.messages.parse(
            model="claude-haiku-4-5-20251001", 
            max_tokens=4096, 
            messages=[{"role": "user", "content": prompt,}],
            output_format=output_format,
            )
        
        if message.parsed_output is None:
            logger.error("API call returned None. Something went wrong.")

        assert message.parsed_output is not None, "API call returned None. Something went wrong."
        return message.parsed_output
    
class GeminiAdapter(LLMAdapter):
    def __init__(self):
        self.client = genai.Client()

    def complete(self, prompt: str, output_format: type[T]) -> T:
        """Generate a structured output from a given prompt and output format.

        Args:
            prompt (str): Prompt passed to LLM. 
            output_format (type[T]): Pydantic model defining output format. 

        Returns:
            T: Defined BaseModel format of output (depends on output_format parameter).
        """
        
        response = self.client.models.generate_content(
            model="gemini-3.5-flash",
            contents=prompt,
            config=genai.types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=output_format,
            ),
        )

        if response.parsed is None:
            logger.error("API call returned None. Something went wrong.")

        assert response.parsed is not None, "API call returned None. Something went wrong."
        assert isinstance(response.parsed, output_format), (
            f"Expected {output_format.__name__}, got {type(response.parsed).__name__}."
            )
        return response.parsed