
import os
from datetime import datetime
from typing import Dict
from config import BACKEND_URL
from service.ReviewScraper import ReviewScraper
from connector.SentimentConnector import SentimentAnalysisConnector

class ScraperSentimentPipeline:
    """Complete pipeline: Scrape -> Clean -> Analyze"""
    
    def __init__(self, apify_token: str = None, backend_url: str = BACKEND_URL):
        self.scraper = ReviewScraper(apify_token)
        self.analyzer = SentimentAnalysisConnector(backend_url)
    
    def process_location(
        self,
        place_url: str,
        max_reviews: int = 50,
        analyze: bool = True
    ) -> Dict:
        """Process single Honda AHASS location"""
        
        # Step 1: Scrape and clean reviews
        scrape_result = self.scraper.scrape_location(place_url, max_reviews)
        
        if not scrape_result["success"]:
            return scrape_result
        
        # Step 2: Analyze valid reviews
        if analyze and scrape_result.get("reviews"):
            analysis_result = self.analyzer.analyze_batch_reviews(
                scrape_result["reviews"],
                parallel=True
            )
            
            if analysis_result.get("success"):
                scrape_result["sentiment_analysis"] = analysis_result
                scrape_result["analyzed"] = True
            else:
                scrape_result["sentiment_analysis"] = {"error": analysis_result.get("error")}
                scrape_result["analyzed"] = False
        else:
            scrape_result["analyzed"] = False
        
        scrape_result["timestamp"] = datetime.now().isoformat()
        return scrape_result