"""
Honda AHASS Review Scraper API + Sentiment Analysis
FastAPI Backend for React Dashboard Integration

Installation:
pip install fastapi uvicorn apify-client requests python-dotenv pydantic

Run:
uvicorn main:app --reload --host 0.0.0.0 --port 8080
"""

import os
import time
from dotenv import load_dotenv
from apify_client import ApifyClient
from typing import List, Dict, Optional
from datetime import datetime
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import uuid
from pipeline.ScraperSentimentPipeline import ScraperSentimentPipeline
from service.ReviewCleaner import ReviewCleaner
from interface.ScrapeRequest import ScrapeRequest
from interface.MultipleScrapeRequest import MultipleScrapeRequest




load_dotenv()


# ============================================
# FastAPI App
# ============================================

app = FastAPI(
    title="Google Scraper + Sentiment Analysis API",
    description="API for scraping and analyzing Google reviews",
    version="1.0.0"
)

# CORS Configuration for React Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Job storage for async processing
jobs_storage = {}

# ============================================
# API Endpoints
# ============================================

@app.get("/")
async def root():
    """API Health Check"""
    return {
        "service": "Honda AHASS Review API",
        "status": "running",
        "version": "1.0.0",
        "endpoints": {
            "scrape": "/api/scrape",
            "scrape_multiple": "/api/scrape-multiple",
            "scrape_async": "/api/scrape-async",
            "job_status": "/api/job/{job_id}"
        }
    }

@app.post("/api/scrape")
async def scrape_location(request: ScrapeRequest):
    """
    Scrape single Honda AHASS location (Synchronous)
    Reviews are automatically cleaned before analysis
    """
    try:
        pipeline = ScraperSentimentPipeline()
        result = pipeline.process_location(
            place_url=request.place_url,
            max_reviews=request.max_reviews,
            analyze=request.analyze
        )
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/scrape-async")
async def scrape_location_async(request: ScrapeRequest, background_tasks: BackgroundTasks):
    """
    Scrape single location (Asynchronous)
    Returns job_id immediately, check status with /api/job/{job_id}
    """
    job_id = str(uuid.uuid4())
    
    jobs_storage[job_id] = {
        "status": "processing",
        "created_at": datetime.now().isoformat(),
        "progress": {"stage": "scraping", "percentage": 0}
    }
    
    background_tasks.add_task(process_scrape_job, job_id, request)
    
    return {
        "job_id": job_id,
        "status": "processing",
        "message": "Job started. Check status at /api/job/{job_id}"
    }

@app.post("/api/scrape-multiple")
async def scrape_multiple_locations(request: MultipleScrapeRequest):
    """
    Scrape multiple Honda AHASS locations
    All reviews are cleaned before analysis
    """
    try:
        pipeline = ScraperSentimentPipeline()
        results = []
        
        for idx, url in enumerate(request.place_urls, 1):
            result = pipeline.process_location(
                place_url=url,
                max_reviews=request.max_reviews_per_location,
                analyze=request.analyze
            )
            results.append(result)
            
            # Rate limiting
            if idx < len(request.place_urls):
                time.sleep(5)
        
        return {
            "success": True,
            "total_locations": len(request.place_urls),
            "results": results,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/job/{job_id}")
async def get_job_status(job_id: str):
    """Check status of async job"""
    if job_id not in jobs_storage:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return jobs_storage[job_id]

@app.post("/api/clean-reviews")
async def clean_reviews_endpoint(reviews: List[Dict]):
    """
    Standalone endpoint to clean reviews
    Useful for testing or manual cleaning
    """
    try:
        result = ReviewCleaner.filter_reviews(reviews)
        return {
            "success": True,
            "valid_reviews": result["valid_reviews"],
            "stats": result["stats"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stats")
async def get_stats():
    """Get API usage statistics"""
    return {
        "active_jobs": len([j for j in jobs_storage.values() if j["status"] == "processing"]),
        "completed_jobs": len([j for j in jobs_storage.values() if j["status"] == "completed"]),
        "failed_jobs": len([j for j in jobs_storage.values() if j["status"] == "failed"]),
        "total_jobs": len(jobs_storage)
    }

# ============================================
# Background Task Functions
# ============================================

def process_scrape_job(job_id: str, request: ScrapeRequest):
    """Background task for async scraping"""
    try:
        jobs_storage[job_id]["progress"] = {"stage": "scraping", "percentage": 30}
        
        pipeline = ScraperSentimentPipeline()
        result = pipeline.process_location(
            place_url=request.place_url,
            max_reviews=request.max_reviews,
            analyze=request.analyze
        )
        
        if result["success"]:
            jobs_storage[job_id]["progress"] = {"stage": "completed", "percentage": 100}
            jobs_storage[job_id]["status"] = "completed"
            jobs_storage[job_id]["result"] = result
        else:
            jobs_storage[job_id]["status"] = "failed"
            jobs_storage[job_id]["error"] = result.get("error")
            
    except Exception as e:
        jobs_storage[job_id]["status"] = "failed"
        jobs_storage[job_id]["error"] = str(e)

# ============================================
# Run Server
# ============================================

if __name__ == "__main__":
    import uvicorn
    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║   Honda AHASS Review API Server                         ║
    ║   FastAPI Backend for React Dashboard                   ║
    ╚═══════════════════════════════════════════════════════════╝
    
    🚀 Starting server...
    📡 API will be available at: http://localhost:8080
    📚 Interactive docs at: http://localhost:8080/docs
    🔧 ReDoc at: http://localhost:8080/redoc
    """)
    
    uvicorn.run(app, host="0.0.0.0", port=8080)