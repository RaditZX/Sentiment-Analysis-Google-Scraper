
import os
import json
from typing import List, Dict, Set
from datetime import datetime
from dotenv import load_dotenv
from apify_client import ApifyClient
from service.ReviewCleaner import ReviewCleaner
from config import APIFY_TOKEN

class ReviewScraper:
    """Scraper untuk review Honda AHASS dari Google Maps dengan tracking duplikat"""
    
    def __init__(self, apify_token: str = None, cache_file: str = "scraped_reviews.json"):
        self.token = apify_token or APIFY_TOKEN
        if not self.token:
            raise ValueError("APIFY_API_TOKEN required")
        self.client = ApifyClient(self.token)
        self.cache_file = cache_file
        self.scraped_review_ids = self._load_cache()
    
    def _load_cache(self) -> Dict[str, Set[str]]:
        """Load previously scraped review IDs from cache file"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Convert lists back to sets for each place_id
                    return {k: set(v) for k, v in data.items()}
            except Exception as e:
                print(f"Error loading cache: {e}")
                return {}
        return {}
    
    def _save_cache(self):
        """Save scraped review IDs to cache file"""
        try:
            # Convert sets to lists for JSON serialization
            data = {k: list(v) for k, v in self.scraped_review_ids.items()}
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving cache: {e}")
    
    def _get_review_id(self, review: Dict) -> str:
        """Generate unique ID for a review"""
        # Use combination of reviewer ID and timestamp for uniqueness
        reviewer_id = review.get('reviewerId', '')
        published_at = review.get('publishedAtDate', '')
        text = review.get('text', '')[:50]  # First 50 chars as additional identifier
        
        return f"{reviewer_id}_{published_at}_{hash(text)}"
    
    def _filter_new_reviews(self, reviews: List[Dict], place_id: str) -> List[Dict]:
        """Filter out reviews that have been scraped before"""
        if place_id not in self.scraped_review_ids:
            self.scraped_review_ids[place_id] = set()
        
        new_reviews = []
        existing_ids = self.scraped_review_ids[place_id]
        
        for review in reviews:
            review_id = self._get_review_id(review)
            if review_id not in existing_ids:
                new_reviews.append(review)
                existing_ids.add(review_id)
        
        return new_reviews
    
    def scrape_location(
        self,
        place_url: str,
        max_reviews: int = 50,
        language: str = "id",
        sort_by: str = "newest",
        skip_duplicates: bool = True
    ) -> Dict:
        """
        Scrape reviews dari lokasi Honda AHASS
        
        Args:
            place_url: URL Google Maps location
            max_reviews: Maximum number of reviews to fetch
            language: Language code (default: "id")
            sort_by: Sort order ("newest", "mostRelevant", "highestRanking", "lowestRanking")
            skip_duplicates: If True, filter out previously scraped reviews
        
        Returns:
            Dict containing location info, new reviews, and stats
        """
        
        run_input = {
            "startUrls": [{"url": place_url}],
            "maxReviews": max_reviews,
            "language": language,
            "sortBy": sort_by,
            "includeHistogram": True,
            "includeOpeningHours": True,
            "includePeopleAlsoSearch": False,
        }
        
        try:
            run = self.client.actor("nwua9Gu5YrADL7ZDj").call(run_input=run_input)
            dataset_items = list(self.client.dataset(run["defaultDatasetId"]).iterate_items())
            
            if not dataset_items:
                return {"success": False, "error": "No data found"}
            
            location_data = dataset_items[0]
            place_id = location_data.get("placeId")
            reviews = location_data.get("reviews", [])
            
            # Filter duplicates if enabled
            new_reviews = reviews
            duplicate_count = 0
            
            if skip_duplicates and place_id:
                original_count = len(reviews)
                new_reviews = self._filter_new_reviews(reviews, place_id)
                duplicate_count = original_count - len(new_reviews)
                
                # Save cache after filtering
                self._save_cache()
            
            # Clean reviews
            cleaning_result = ReviewCleaner.filter_reviews(new_reviews)
            
            return {
                "success": True,
                "location": {
                    "name": location_data.get("title"),
                    "address": location_data.get("address"),
                    "rating": location_data.get("totalScore"),
                    "reviews_count": location_data.get("reviewsCount"),
                    "category": location_data.get("categoryName"),
                    "phone": location_data.get("phone"),
                    "website": location_data.get("website"),
                    "location": location_data.get("location"),
                    "place_id": place_id,
                },
                "reviews": cleaning_result["valid_reviews"],
                "cleaning_stats": cleaning_result["stats"],
                "scraping_stats": {
                    "raw_reviews_fetched": len(reviews),
                    "duplicates_filtered": duplicate_count,
                    "new_reviews_found": len(new_reviews),
                    "total_scraped_for_location": len(self.scraped_review_ids.get(place_id, set()))
                }
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def reset_cache_for_location(self, place_id: str):
        """Reset cached reviews for a specific location"""
        if place_id in self.scraped_review_ids:
            del self.scraped_review_ids[place_id]
            self._save_cache()
            return True
        return False
    
    def reset_all_cache(self):
        """Reset all cached reviews"""
        self.scraped_review_ids = {}
        self._save_cache()
    
    def get_cached_review_count(self, place_id: str) -> int:
        """Get count of cached reviews for a location"""
        return len(self.scraped_review_ids.get(place_id, set()))