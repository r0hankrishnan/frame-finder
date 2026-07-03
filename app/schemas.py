""""Defines schemas used for requests and response values"""

from pydantic import BaseModel, Field
from frame_finder.engine import ParsingStatus

class SearchRequest(BaseModel):
    query: str = Field(description="Raw query string recieved from user", min_length=1, max_length=500)
    skip_parse: bool = Field(default=False, description="Whether or not to skip LLM parsing")

class RacquetCard(BaseModel):
    racquet_id: str = Field(description="Unique product ID of racquet")
    racquet_rank: int = Field(description="Rank of racquet in RRF results")
    racquet_name: str = Field(description="Name of racquet")
    racquet_url: str = Field(description="URL of racquet listing page on TW website")
    racquet_img: str = Field(description="URL of TW racquet image")
    racquet_rating: float | None = Field(default=None, description="Rating score of racquet")
    racquet_rating_count: int | None = Field(default=None, description="Total number of ratings")
    racquet_price: float = Field(description="Price of racquet")
    racquet_description: str | None = Field(default=None, description="TW marketing copy for racquet")
    racquet_match_score: int = Field(default=0, description="The percentage of the top score a given racquet achieves.")

class SearchResponse(BaseModel):
    search_id: str = Field(description="Unique ID identifying a user's search")
    parsing_status: ParsingStatus = Field(description="Enum field that indicates whether query was parsed with LLM")
    results: list[RacquetCard] = Field(description="List of pydantic objects that contain metadata for insertion into frontend racquet card")

class FeedbackRequest(BaseModel):
    search_id: str = Field(description="The ID of the active search being displayed")
    racquet_id: str = Field(description="The racquet_id of the particular racquet the user liked.")
    liked: bool = Field(description="Whether the user 'liked' (true) or 'unliked' (false) the racquet")