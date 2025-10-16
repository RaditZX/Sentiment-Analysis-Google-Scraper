
from typing import List, Dict
from datetime import datetime



class ReviewCleaner:
    """Clean and validate reviews before sentiment analysis"""
    
    @staticmethod
    def is_valid_review(review: Dict) -> bool:
        """
        Check if review has valid text content
        Returns False if:
        - No text field
        - Empty text
        - Text is only whitespace
        - Text is too short (< 3 characters)
        """
        text = review.get("text") or review.get("reviewText") or ""
        text = text.strip()
        
        # Minimum length for meaningful review
        return len(text) >= 3
    
    @staticmethod
    def clean_review_text(text: str) -> str:
        """Clean review text"""
        if not text:
            return ""
        
        # Remove excessive whitespace
        text = " ".join(text.split())
        
        # Remove common artifacts
        text = text.replace("(Translated by Google)", "")
        text = text.replace("(Original)", "")
        
        return text.strip()
    
    @staticmethod
    def has_only_images(review: Dict) -> bool:
        """Check if review only contains images without text"""
        has_images = bool(review.get("reviewImageUrls") or review.get("photos"))
        text = review.get("text") or review.get("reviewText") or ""
        has_valid_text = len(text.strip()) >= 3
        
        return has_images and not has_valid_text
    
    @classmethod
    def filter_reviews(cls, reviews: List[Dict]) -> Dict:
        """
        Filter reviews and return valid ones + statistics
        """
        valid_reviews = []
        filtered_stats = {
            "total": len(reviews),
            "valid": 0,
            "no_text": 0,
            "only_images": 0,
            "too_short": 0
        }
        
        for review in reviews:
            # Check if only images
            if cls.has_only_images(review):
                filtered_stats["only_images"] += 1
                continue
            
            # Check if valid text exists
            text = review.get("text") or review.get("reviewText") or ""
            text = text.strip()
            
            if not text:
                filtered_stats["no_text"] += 1
                continue
            
            if len(text) < 3:
                filtered_stats["too_short"] += 1
                continue
            
            # Clean the text
            review["text"] = cls.clean_review_text(text)
            valid_reviews.append(review)
            filtered_stats["valid"] += 1
        
        return {
            "valid_reviews": valid_reviews,
            "stats": filtered_stats
        }
