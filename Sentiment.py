# Sentiment Analysis Backend - GitHub Models API with MySQL
"""
Installation:
pip install fastapi uvicorn azure-ai-inference python-dotenv mysql-connector-python
"""

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional, Dict, Any
from datetime import datetime
import os
from dotenv import load_dotenv
import asyncio
# GitHub Models API
from azure.ai.inference import ChatCompletionsClient
from azure.core.credentials import AzureKeyCredential
# Local Database Manager
from service.DatabaseManager import DatabaseManager
from service.SentimentAnalyzer import GitHubModelsSentimentAnalyzer, client
from config import GITHUB_TOKEN, GITHUB_ENDPOINT, GITHUB_MODEL, DB_CONFIG

load_dotenv()

# ============================================
# Configuration
# ============================================

app = FastAPI(
    title="Sentiment Analysis API - GitHub Models + MySQL",
    description="AI-powered sentiment analysis using GitHub Models with MySQL persistence",
    version="3.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    DatabaseManager.init_database()

@app.get("/")
def root():
    return {
        "message": "Sentiment Analysis API - GitHub Models + MySQL",
        "version": "3.0.0",
        "model": GITHUB_MODEL,
        "github_token_set": bool(GITHUB_TOKEN),
        "client_initialized": client is not None,
        "database_configured": bool(DB_CONFIG),
        "endpoints": {
            "single": "POST /api/analyze",
            "batch": "POST /api/batch-analyze",
            "smart_batch": "POST /api/smart-batch-analyze (skips analyzed)",
            "get_analysis": "GET /api/analysis/{review_id}",
            "get_all": "GET /api/analyses",
            "statistics": "GET /api/statistics",
            "health": "GET /health"
        }
    }

@app.get("/health")
def health():
    conn = DatabaseManager.get_connection()
    db_healthy = conn is not None
    if conn:
        conn.close()
    
    return {
        "status": "healthy" if db_healthy else "degraded",
        "github_models_available": client is not None,
        "database_available": db_healthy,
        "fallback_available": True,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/get-all-sentiment-analysis")
def get_all_sentiment_analysis(
    review_id: Optional[str] = Query(None),
    sentiment_filter: Optional[str] = Query(None),
    limit: int = Query(100, ge=1),
    offset: int = Query(0, ge=0),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None)
):
    results = DatabaseManager.get_all_analyses(
        limit=limit,
        offset=offset,
        sentiment_filter=sentiment_filter,
        start_date=start_date,
        end_date=end_date
    )

    return {
        "success": True,
        **results["summary"],
        "results": results["results"]
    }



    
@app.post("/api/smart-batch-analyze")
async def smart_batch_analyze(data: dict, is_google: bool = Query(False, description="Whether the reviews come from Google")):
    """
    Smart batch analyze - checks DB first, only analyzes unanalyzed reviews
    
    Body: {
        "reviews": [
            {"id": "R1", "full_review": "...", "rating": 5},
            {"id": "R2", "full_review": "...", "rating": 3}
        ],
        "parallel_processing": true,
        "force_reanalyze": false
    }
    """
    try:
        start_time = datetime.now()
        reviews = data.get("reviews", [])
        parallel = data.get("parallel_processing", True)
        force_reanalyze = data.get("force_reanalyze", False)


        if not reviews:
            return {"success": False, "error": "reviews array required"}


        results = []
        skipped = []
        errors = []
        
        # Check which reviews need analysis
        reviews_to_analyze = []
        for idx, rev in enumerate(reviews):
            review_id = rev.get("id", f"REV{idx+1:03d}")
            review_text = rev.get("full_review", "")
            
            if not review_text:
                continue
            
            # Check if already analyzed
            if not force_reanalyze and DatabaseManager.is_analyzed(review_id, review_text):
                existing = DatabaseManager.get_analysis(review_id)
                if existing:
                    existing['from_cache'] = True
                    results.append(existing)
                    skipped.append({"id": review_id, "reason": "already_analyzed"})
                    continue
            
            reviews_to_analyze.append({
                "review": review_text,
                "rating": rev.get("rating", 3),
                "id": review_id,
                "reviewer_name": rev.get("reviewer_name"),
                "review_at": rev.get("review_date")
            })
        
        print(reviews_to_analyze)

        # Analyze new reviews
        if reviews_to_analyze:
            if parallel:
                tasks = [
                    GitHubModelsSentimentAnalyzer.analyze_with_github(
                        rev["review"],
                        rev["rating"],
                        rev["id"],
                        rev["reviewer_name"],
                        rev["review_at"],
                        is_google=is_google
                    )
                    for rev in reviews_to_analyze
                ]
                
                completed = await asyncio.gather(*tasks, return_exceptions=True)
                
                for idx, result in enumerate(completed):
                    if isinstance(result, Exception):
                        errors.append({"index": idx, "error": str(result)})
                    else:
                        # Save to database
                        db_saved = DatabaseManager.save_analysis(result)
                        result['saved_to_db'] = db_saved
                        result['from_cache'] = False
                        results.append(result)
            else:
                for rev in reviews_to_analyze:
                    try:
                        result = await GitHubModelsSentimentAnalyzer.analyze_with_github(
                            rev["review"],
                            rev["rating"],
                            rev["id"],
                            rev["reviewer_name"],
                            rev["review_at"],
                            is_google=is_google
                        )
                        # Save to database
                        db_saved = DatabaseManager.save_analysis(result)
                        result['saved_to_db'] = db_saved
                        result['from_cache'] = False
                        results.append(result)
                    except Exception as e:
                        errors.append({"id": rev["id"], "error": str(e)})

        total_time = (datetime.now() - start_time).total_seconds() * 1000

        return {
            "success": True,
            "total_reviews": len(reviews),
            "processed": len(results),
            "newly_analyzed": len(reviews_to_analyze),
            "from_cache": len(skipped),
            "failed": len(errors),
            "processing_time_total_ms": round(total_time, 2),
            "results": results,
            "skipped": skipped if skipped else None,
            "errors": errors if errors else None
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
    

@app.post("/api/smart-batch-analyze-auto")
async def smart_batch_analyze_auto(
    limit: int = 5,
    is_google: bool = Query(False, description="Whether the reviews come from Google")
):
    """
    Smart batch analyze - fetches reviews from database and analyzes only unanalyzed ones.
    Query params:
        limit: number of reviews to fetch from DB (default 5)
        is_google: whether the reviews come from Google
    """
    try:
        start_time = datetime.now()
        
        # Ambil reviews dari database
        reviews = DatabaseManager.get_testimoni(limit=limit)
        if not reviews:
            return {"success": False, "error": "No reviews found in database."}

        results = []
        skipped = []
        errors = []
        reviews_to_analyze = []

        # Filter reviews yang perlu dianalisis
        for idx, rev in enumerate(reviews):
            review_id = rev.get("id", f"REV{idx+1:03d}")  # tambahkan id jika tidak ada
            review_text = rev.get("ulasan", "")
            rating = rev.get("rating", 3)

            if not review_text:
                continue

            # Cek apakah sudah dianalisis
            if DatabaseManager.is_analyzed(review_id, review_text):
                existing = DatabaseManager.get_analysis(review_id)
                if existing:
                    existing['from_cache'] = True
                    results.append(existing)
                    skipped.append({"id": review_id, "reason": "already_analyzed"})
                    continue

            reviews_to_analyze.append({
                "review": review_text,
                "rating": rating,
                "id": review_id
            })

        print("Reviews to analyze:", reviews_to_analyze)

        # Analisis review baru
        if reviews_to_analyze:
            tasks = [
                GitHubModelsSentimentAnalyzer.analyze_with_github(
                    rev["review"],
                    rev["rating"],
                    rev["id"],
                    reviewer_name=rev.get("reviewer_name"),
                    review_at=rev.get("review_at"),
                    is_google=is_google
                )
                for rev in reviews_to_analyze
            ]

            completed = await asyncio.gather(*tasks, return_exceptions=True)

            for idx, result in enumerate(completed):
                if isinstance(result, Exception):
                    errors.append({"index": idx, "error": str(result)})
                else:
                    db_saved = DatabaseManager.save_analysis(result)
                    result['saved_to_db'] = db_saved
                    result['from_cache'] = False
                    results.append(result)

        total_time = (datetime.now() - start_time).total_seconds() * 1000

        return {
            "success": True,
            "total_reviews": len(reviews),
            "processed": len(results),
            "newly_analyzed": len(reviews_to_analyze),
            "from_cache": len(skipped),
            "failed": len(errors),
            "processing_time_total_ms": round(total_time, 2),
            "results": results,
            "skipped": skipped if skipped else None,
            "errors": errors if errors else None
        }

    except Exception as e:
        return {"success": False, "error": str(e)}



# ============================================
# Run Server
# ============================================

if __name__ == "__main__":
    import uvicorn

    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║   Sentiment Analysis API - GitHub Models                 ║
    ╚═══════════════════════════════════════════════════════════╝
    
    📦 Installation:
       pip install fastapi uvicorn azure-ai-inference python-dotenv
    
    🔑 Setup .env file:
       GITHUB_TOKEN=your_github_token_here
       # atau
       OPENAI_API_KEY=your_github_token_here
    
    🚀 Server: http://localhost:8000
    📚 Docs: http://localhost:8000/docs
    
    ✅ GitHub Models API Support
    ✅ Auto Fallback ke Rule-Based
    ✅ Batch Processing Ready
    """)
    database_ready = DatabaseManager.init_database()
    if not database_ready:
        print("❌ Database not ready. Check DB configuration in .env")


    uvicorn.run("Sentiment:app", host="0.0.0.0", port=8000, reload=True)