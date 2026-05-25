from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
import csv
import io
import sqlite3
import yaml
import os
from src.storage import Storage
from src.fetcher import RSSFetcher
from src.analyzer import ContentAnalyzer
from src.interface import QueryInterface
from apscheduler.schedulers.background import BackgroundScheduler
import logging
from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Suppress noisy logs from libraries
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("google_genai").setLevel(logging.WARNING)

# Locks for ingestion
ingest_lock = False

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    logger.info("Initializing background scheduler...")
    scheduler.start()
    update_scheduler_from_config()
    yield
    # Shutdown logic
    logger.info("Shutting down background scheduler...")
    scheduler.shutdown(wait=False)

app = FastAPI(lifespan=lifespan)

# Initialize components
storage = Storage()
analyzer = ContentAnalyzer()
fetcher = RSSFetcher(storage=storage)
interface = QueryInterface(storage, analyzer)

# Scheduler (initialized here, started in lifespan)
scheduler = BackgroundScheduler()

def scheduled_ingest():
    global ingest_lock
    if ingest_lock:
        logger.info("Scheduled ingestion skipped: Ingestion already in progress.")
        return
    
    ingest_lock = True
    logger.info("Starting scheduled ingestion...")
    try:
        with open("config.yaml", "r") as f:
            config = yaml.safe_load(f)
        pull_limit = config.get('scheduling', {}).get('pull_limit', 20)
        
        articles = fetcher.fetch_all()
        count = 0
        
        # Parallel analysis
        to_analyze = articles[:pull_limit]
        with ThreadPoolExecutor(max_workers=5) as executor:
            # We use a map to process articles in parallel
            # We need to wrap the logic to merge results
            def process_article(art):
                analysis = analyzer.analyze_article(art)
                relevance = analysis.get("relevance_score", "").lower()
                usefulness = analysis.get("usefulness", "").lower()
                
                if relevance == "low":
                    return None
                    
                art.update(analysis)
                return art

            analyzed_articles = list(executor.map(process_article, to_analyze))

        for article in analyzed_articles:
            if article is not None and storage.add_article(article):
                count += 1
        logger.info(f"Scheduled ingestion complete. {count} new articles.")
    except Exception as e:
        logger.error(f"Error in scheduled ingestion: {e}")
    finally:
        ingest_lock = False

def update_scheduler_from_config():
    with open("config.yaml", "r") as f:
        config = yaml.safe_load(f)
    
    # Remove existing ingest job if it exists
    if scheduler.get_job('scheduled_ingest'):
        scheduler.remove_job('scheduled_ingest')
    
    schedule_config = config.get('scheduling', {})
    if schedule_config.get('enabled', False):
        interval_hours = schedule_config.get('interval_hours', 2)
        scheduler.add_job(scheduled_ingest, 'interval', hours=interval_hours, id='scheduled_ingest')
        logger.info(f"Scheduled ingestion enabled. Interval: {interval_hours} hours.")
    else:
        logger.info("Scheduled ingestion is disabled.")

# Initial scheduler setup (config reading only)
# scheduler.start() is now in lifespan

# Models
class ChatRequest(BaseModel):
    message: str

class ConfigRequest(BaseModel):
    config: str

# Endpoints

@app.get("/api/articles")
def get_articles(
    limit: int = 50, 
    relevance: Optional[str] = None, 
    category: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    return storage.get_articles(
        limit=limit, 
        relevance=relevance, 
        category=category, 
        start_date=start_date, 
        end_date=end_date
    )

@app.get("/api/categories")
def get_categories():
    return storage.get_unique_categories()

@app.get("/api/export/csv")
def export_csv(limit: Optional[int] = None):
    conn = sqlite3.connect(storage.db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    query = 'SELECT * FROM articles ORDER BY created_at DESC'
    if limit is not None:
        query += f' LIMIT {int(limit)}'

    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        raise HTTPException(status_code=404, detail="No data available to export")

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=rows[0].keys())
    writer.writeheader()
    for row in rows:
        writer.writerow(dict(row))
    output.seek(0)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=articles_export.csv"}
    )

@app.delete("/api/articles/{article_id}")
def delete_article(article_id: int):
    if storage.delete_article(article_id):
        return {"status": "success"}
    else:
        raise HTTPException(status_code=404, detail="Article not found")

@app.delete("/api/articles")
def delete_all_articles():
    count = storage.delete_all_articles()
    return {"status": "success", "deleted_count": count}

@app.post("/api/chat")
def chat(request: ChatRequest):
    results = interface.handle_query(request.message)
    # Format results for the frontend (simplified for now, could be more structured)
    return {"response": interface.format_results(results), "articles": results}

@app.post("/api/ingest")
def ingest():
    global ingest_lock
    if ingest_lock:
        return {"status": "busy", "message": "Ingestion already in progress"}
        
    ingest_lock = True
    try:
        # Manual ingest also respects config pull_limit for speed
        with open("config.yaml", "r") as f:
            config = yaml.safe_load(f)
        pull_limit = config.get('scheduling', {}).get('pull_limit', 10)

        articles = fetcher.fetch_all()
        count = 0
        
        # Parallel analysis
        to_analyze = articles[:pull_limit]
        with ThreadPoolExecutor(max_workers=5) as executor:
            def process_article(art):
                analysis = analyzer.analyze_article(art)
                relevance = analysis.get("relevance_score", "").lower()
                usefulness = analysis.get("usefulness", "").lower()
                
                if relevance == "low":
                    return None
                    
                art.update(analysis)
                return art

            analyzed_articles = list(executor.map(process_article, to_analyze))

        for article in analyzed_articles:
            if article is not None and storage.add_article(article):
                count += 1
        return {"status": "success", "new_articles": count}
    except Exception as e:
        logger.error(f"Manual ingestion error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        ingest_lock = False

@app.get("/api/config")
def get_config():
    with open("config.yaml", "r") as f:
        return {"config": f.read()}

@app.post("/api/config")
def update_config(request: ConfigRequest):
    try:
        # Validate YAML
        yaml.safe_load(request.config)
        with open("config.yaml", "w") as f:
            f.write(request.config)
        # Reload components to apply config changes
        global fetcher, analyzer
        fetcher = RSSFetcher(storage=storage)
        analyzer = ContentAnalyzer()
        # Update scheduler with new config
        update_scheduler_from_config()
        return {"status": "success"}
    except yaml.YAMLError as e:
        raise HTTPException(status_code=400, detail=f"Invalid YAML: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Serve static files
app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    print("\n" + "="*50)
    print("🚀 Media Intel Agent Web UI is starting!")
    print(f"👉 Access the dashboard at: http://localhost:8000")
    print("="*50 + "\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)

