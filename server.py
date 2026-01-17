from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
import yaml
import os
from src.storage import Storage
from src.fetcher import RSSFetcher
from src.analyzer import ContentAnalyzer
from src.interface import QueryInterface

app = FastAPI()

# Initialize components
storage = Storage()
analyzer = ContentAnalyzer()
fetcher = RSSFetcher(storage=storage)
interface = QueryInterface(storage, analyzer)

# Models
class ChatRequest(BaseModel):
    message: str

class ConfigRequest(BaseModel):
    config: str

# Endpoints

@app.get("/api/articles")
def get_articles(limit: int = 50, relevance: Optional[str] = None, category: Optional[str] = None):
    return storage.get_articles(limit=limit, relevance=relevance, category=category)

@app.post("/api/chat")
def chat(request: ChatRequest):
    results = interface.handle_query(request.message)
    # Format results for the frontend (simplified for now, could be more structured)
    return {"response": interface.format_results(results), "articles": results}

@app.post("/api/ingest")
def ingest():
    try:
        articles = fetcher.fetch_all()
        count = 0
        for article in articles:
            analysis = analyzer.analyze_article(article)
            article.update(analysis)
            if storage.add_article(article):
                count += 1
        return {"status": "success", "new_articles": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
        return {"status": "success"}
    except yaml.YAMLError as e:
        raise HTTPException(status_code=400, detail=f"Invalid YAML: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Serve static files
app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
