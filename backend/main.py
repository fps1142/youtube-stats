import os
import csv
import io
from fastapi import FastAPI, HTTPException, Response, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from backend.youtube_fetcher import YouTubeCommentFetcher
from backend.stats_calculator import calculate_statistics

app = FastAPI(title="YouTube Price Guess Analytics", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# キャッシュ無効化ミドルウェア（開発時・ブラウザ更新の確実性向上）
@app.middleware("http")
async def add_no_cache_header(request: Request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

fetcher = YouTubeCommentFetcher()

class AnalyzeRequest(BaseModel):
    url: str
    max_comments: Optional[int] = 2000
    correct_price: Optional[float] = None

class RecomputeQuizRequest(BaseModel):
    comments: List[Dict[str, Any]]
    correct_price: float

@app.post("/api/analyze")
async def analyze_url(req: AnalyzeRequest):
    if not req.url:
        raise HTTPException(status_code=400, detail="URLを入力してください")
    
    try:
        data = fetcher.fetch_post_or_video_data(req.url, max_comments=req.max_comments or 2000)
        stats = calculate_statistics(data["comments"], correct_price=req.correct_price)
        
        return {
            "success": True,
            "metadata": data["metadata"],
            "target_type": data["target_type"],
            "target_id": data["target_id"],
            "stats": stats
        }
    except Exception as e:
        print("Analyze error:", e)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/recompute-quiz")
async def recompute_quiz(req: RecomputeQuizRequest):
    try:
        stats = calculate_statistics(req.comments, correct_price=req.correct_price)
        return {
            "success": True,
            "quiz_result": stats["quiz_result"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health")
async def health_check():
    return {"status": "ok"}

# 静的ファイルの配信
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
