
from pydantic import BaseModel, HttpUrl
from typing import Optional, List, Dict

class ScrapeRequest(BaseModel):
    place_url: str
    max_reviews: int = 50
    language: str = "id"
    sort_by: str = "newest"
    analyze: bool = True