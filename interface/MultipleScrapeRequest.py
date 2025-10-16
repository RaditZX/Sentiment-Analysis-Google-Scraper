
from pydantic import BaseModel, HttpUrl
from typing import List

class MultipleScrapeRequest(BaseModel):
    place_urls: List[str]
    max_reviews_per_location: int = 50
    analyze: bool = True