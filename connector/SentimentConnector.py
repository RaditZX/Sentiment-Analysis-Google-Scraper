import requests
from typing import List, Dict
import uuid
import os
from dotenv import load_dotenv
load_dotenv()
from config import BACKEND_URL


class SentimentAnalysisConnector:
    """Connector untuk backend sentiment analysis"""
    
    def __init__(self, backend_url: str = BACKEND_URL):
        self.backend_url = backend_url.rstrip('/')
    
    def format_review_for_analysis(self, review: Dict) -> Dict:
        """Format Apify review untuk backend sentiment analysis"""
        review_text = review.get("text") or review.get("reviewText") or ""
        
        return {
            "id": review.get("reviewId") or review.get("id", str(uuid.uuid4())),
            "full_review": review_text,
            "rating": review.get("stars") or review.get("rating", 3),
            "reviewer_name": review.get("name"),
            "review_date": review.get("publishedAtDate") or review.get("publishAt"),
            "likes": review.get("likesCount", 0),
        }
    
    def analyze_batch_reviews(self, reviews: List[Dict], parallel: bool = True) -> Dict:
        """Analyze multiple reviews"""
        formatted_reviews = [
            self.format_review_for_analysis(rev) for rev in reviews
        ]
        
        payload = {
            "reviews": formatted_reviews,
            "parallel_processing": parallel
        }
        
        try:
            print(f"{payload}")
            response = requests.post(
                f"{self.backend_url}/api/smart-batch-analyze?is_google=true",
                json=payload,
                timeout=300
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"success": False, "error": str(e)}