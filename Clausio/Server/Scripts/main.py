import os
import glob
import json
import tempfile  
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# 🚀 CONSOLIDATED IMPORTS: All your custom module dependencies in one place
from generate_grid_puzzle import build_puzzle_json, build_puzzle_from_news_tokens
from news_service import fetch_nhk_news_topics, parse_ruby_html_into_sentences

app = FastAPI(title="Clausio Game Engine API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- SYSTEM DIRECTORY SETUP ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STORIES_DIR = os.path.join(BASE_DIR, "Stories")

CACHE_DIR = os.path.join(tempfile.gettempdir(), "ClausioCache")
os.makedirs(CACHE_DIR, exist_ok=True)

print(f"--> System initialized.")
print(f"--> [READ ONLY] Stories Path: {STORIES_DIR}")
print(f"--> [TEMP AREA] Cache Path:    {CACHE_DIR}")


# --- PYDANTIC MODELS ---
class PuzzleRequest(BaseModel):
    file_path: str  
    level: str      

class NewsPuzzleRequest(BaseModel):
    news_id: str
    summary_html: str  
    level: str


# --- API ROUTING ENDPOINTS ---

@app.get("/api/stories")
def list_available_stories():
    """Scans the Git-safe Stories directory root recursively for raw un-tagged .txt files."""
    if not os.path.exists(STORIES_DIR):
        return {"stories": []}
        
    search_pattern = os.path.join(STORIES_DIR, "**", "*.txt")
    found_files = glob.glob(search_pattern, recursive=True)
    
    stories_payload = []
    for path in found_files:
        display_name = os.path.basename(path).replace(".txt", "")
        stories_payload.append({
            "name": display_name,
            "relative_path": path
        })
        
    return {"stories": stories_payload}


@app.get("/api/news/topics")
def get_news_topics():
    """Fetches real-time headlines from NHK Web Easy for the SwiftUI selector screen."""
    try:
        news_feeds = fetch_nhk_news_topics()
        return {"status": "success", "topics": news_feeds}
    except Exception as e:
        print(f"RSS Fetch Error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch RSS feed: {str(e)}")

@app.post("/api/news/puzzle/generate")
def fetch_or_compile_news_puzzle(request: NewsPuzzleRequest):
    target_level = request.level.upper().strip()
    
    # 🚀 THE FIX: Replace slashes and colons so the OS doesn't think this is a folder path!
    safe_news_id = request.news_id.replace("/", "_").replace(":", "_")
    
    # Use the safe ID to build the file path
    cache_destination = os.path.join(CACHE_DIR, f"news_{safe_news_id}_{target_level}_5x5_puzzle.json")
    
    if os.path.exists(cache_destination):
        try:
            with open(cache_destination, "r", encoding="utf-8") as cached_f:
                return json.load(cached_f)
        except Exception:
            pass

    try:
        # 1. Break raw RSS string block down into 5 distinct token sentence matrices
        sentence_rows_tokens = parse_ruby_html_into_sentences(request.summary_html)
        
        # 2. Build the sequential matrix payload with original order intact
        generated_payload = build_puzzle_from_news_tokens(sentence_rows_tokens, target_level)
        
        # 3. Save the cache out to disk
        with open(cache_destination, "w", encoding="utf-8") as cache_out:
            json.dump(generated_payload, cache_out, ensure_ascii=False, indent=4)
            
        return generated_payload
        
    except Exception as err:
        print(f"News Pipeline Crash: {err}")
        raise HTTPException(status_code=500, detail=f"Failed constructing sequential puzzle: {str(err)}")

@app.post("/api/news/puzzle/generate")
def fetch_or_compile_news_puzzle(request: NewsPuzzleRequest):
    target_level = request.level.upper().strip()
    cache_destination = os.path.join(CACHE_DIR, f"news_{request.news_id}_{target_level}_5x5_puzzle.json")
    
    if os.path.exists(cache_destination):
        try:
            with open(cache_destination, "r", encoding="utf-8") as cached_f:
                return json.load(cached_f)
        except Exception:
            pass

    try:
        # 1. Break raw RSS string block down into 5 distinct token sentence matrices
        sentence_rows_tokens = parse_ruby_html_into_sentences(request.summary_html)
        
        # 2. Build the sequential matrix payload with original order intact
        generated_payload = build_puzzle_from_news_tokens(sentence_rows_tokens, target_level)
        
        # 3. Save the cache out to disk
        with open(cache_destination, "w", encoding="utf-8") as cache_out:
            json.dump(generated_payload, cache_out, ensure_ascii=False, indent=4)
            
        return generated_payload
        
    except Exception as err:
        print(f"News Pipeline Crash: {err}") # Added explicit terminal logging
        raise HTTPException(status_code=500, detail=f"Failed constructing sequential puzzle: {str(err)}")


@app.post("/api/cache/clear")
def clear_engine_cache():
    try:
        purged_count = 0
        cache_files = glob.glob(os.path.join(CACHE_DIR, "*.json"))
        for file in cache_files:
            os.remove(file)
            purged_count += 1
        return {"status": "success", "detail": f"Cache cleared. Evicted {purged_count} files from temp area."}
    except Exception as err:
        raise HTTPException(status_code=500, detail=f"Failed clearing temporary directory: {str(err)}")
