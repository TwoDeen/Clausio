import os
import glob
import json
import tempfile  # 🔑 Native module to fetch the system temp directory
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from generate_grid_puzzle import build_puzzle_json

app = FastAPI(title="Clausio Game Engine API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🏢 GIT DIRECTORY (Read-Only Source Area)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STORIES_DIR = os.path.join(BASE_DIR, "Stories")

# 🧼 TEMPORARY AREA (Write/Cache Sandbox Area)
# Creates an isolated, persistent 'ClausioCache' folder within /var/folders/
CACHE_DIR = os.path.join(tempfile.gettempdir(), "ClausioCache")
os.makedirs(CACHE_DIR, exist_ok=True)

print(f"--> System initialized.")
print(f"--> [READ ONLY] Stories Path: {STORIES_DIR}")
print(f"--> [TEMP AREA] Cache Path:    {CACHE_DIR}")

class PuzzleRequest(BaseModel):
    file_path: str  
    level: str      

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

@app.post("/api/puzzle/generate")
def fetch_or_compile_puzzle(request: PuzzleRequest):
    target_level = request.level.upper().strip()
    file_path = request.file_path
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"Source file asset not found at path: {file_path}")
        
    base_file_id = os.path.basename(file_path).replace(".txt", "")
    
    # 🔑 Target the temporary directory away from Git
    cache_destination = os.path.join(CACHE_DIR, f"{base_file_id}_{target_level}_5x5_puzzle.json")
    
    if os.path.exists(cache_destination):
        print(f"--> [CACHE HIT]: Loading matrix directly from Temp Space: {cache_destination}")
        try:
            with open(cache_destination, "r", encoding="utf-8") as cached_f:
                return json.load(cached_f)
        except Exception as read_err:
            print(f"Warning: Failed reading cached JSON. Re-compiling. Error: {read_err}")

    print(f"--> [CACHE MISS]: Processing raw .txt document incrementally: {file_path}")
    try:
        # Pass the temp cache target down so helper modules write to the clean area
        generated_payload = build_puzzle_json(file_path, target_level, CACHE_DIR)
        
        if not generated_payload:
            raise HTTPException(status_code=500, detail="The matrix generation module returned an empty structural schema.")
            
        with open(cache_destination, "w", encoding="utf-8") as cache_out:
            json.dump(generated_payload, cache_out, ensure_ascii=False, indent=4)
            
        print(f"--> Success! Matrix puzzle written to temp space cache layout: {cache_destination}")
        return generated_payload
        
    except Exception as pipeline_crash:
        print(f"Pipeline processing encountered an unhandled exception: {pipeline_crash}")
        raise HTTPException(status_code=500, detail=f"Internal Engine Error processing text elements: {str(pipeline_crash)}")

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
