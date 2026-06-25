"""
main.py  —  Render deployment (read-only, no GiNZA)
====================================================
Serves precomputed puzzle JSONs committed to the repository.
No NLP, no scraping, no heavy dependencies → runs on Render free tier.

To refresh content: run weekly_precompute.py locally and push.
"""

import glob
import json
import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Clausio API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR        = os.path.dirname(os.path.abspath(__file__))
PRECOMPUTED_DIR = os.path.join(BASE_DIR, "precomputed")
NEWS_DIR        = os.path.join(PRECOMPUTED_DIR, "news")
STORIES_PRE_DIR = os.path.join(PRECOMPUTED_DIR, "stories")
STORIES_SRC_DIR = os.path.join(BASE_DIR, "Stories")

print(f"--> Clausio API (static mode)")
print(f"--> Precomputed content: {PRECOMPUTED_DIR}")


# ── Request models ────────────────────────────────────────────────────────────

class PuzzleRequest(BaseModel):
    file_path: str
    level: str

class NewsPuzzleRequest(BaseModel):
    news_id: str
    summary_html: str
    level: str


# ── Helpers ───────────────────────────────────────────────────────────────────

def _load_json(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _story_name(file_path: str) -> str:
    """Extract bare story name from any path format the iOS client sends."""
    return os.path.basename(file_path).replace(".txt", "")


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/api/stories")
def list_available_stories():
    """Returns story list from precomputed index (unique names, no level suffix)."""
    index_path = os.path.join(PRECOMPUTED_DIR, "stories_index.json")

    if os.path.exists(index_path):
        index = _load_json(index_path)
        # Deduplicate: one entry per story name regardless of how many levels exist
        seen, stories = set(), []
        for entry in index:
            if entry["name"] not in seen:
                seen.add(entry["name"])
                stories.append({
                    "name":          entry["name"],
                    "relative_path": entry["name"],   # iOS uses this as file_path
                })
        return {"stories": stories}

    # Fallback: scan committed .txt files (no precomputed index yet)
    if not os.path.exists(STORIES_SRC_DIR):
        return {"stories": []}
    found = glob.glob(os.path.join(STORIES_SRC_DIR, "**", "*.txt"), recursive=True)
    return {"stories": [
        {"name": os.path.basename(p).replace(".txt", ""),
         "relative_path": os.path.basename(p).replace(".txt", "")}
        for p in found
    ]}


@app.get("/api/news/topics")
def get_news_topics(level: str = "N4"):
    """Returns precomputed article list for the requested JLPT level."""
    index_path = os.path.join(PRECOMPUTED_DIR, "news_index.json")
    if not os.path.exists(index_path):
        raise HTTPException(
            status_code=503,
            detail="News index not available. Run weekly_precompute.py locally and push."
        )

    index  = _load_json(index_path)
    level  = level.upper().strip()
    topics = index.get(level, [])

    return {
        "status": "success",
        "topics": [
            {
                "id":           t["id"],
                "title":        t["title"],
                "link":         t.get("link", ""),
                "summary_html": "",
            }
            for t in topics
        ],
    }


@app.post("/api/puzzle/generate")
def fetch_story_puzzle(request: PuzzleRequest):
    """Serves a precomputed story puzzle JSON."""
    level      = request.level.upper().strip()
    story_name = _story_name(request.file_path)
    path       = os.path.join(STORIES_PRE_DIR, f"{story_name}_{level}.json")

    if not os.path.exists(path):
        raise HTTPException(
            status_code=404,
            detail=f"No precomputed puzzle for '{story_name}' at {level}. "
                   f"Run: python weekly_precompute.py --stories"
        )
    return _load_json(path)


@app.post("/api/news/puzzle/generate")
def fetch_news_puzzle(request: NewsPuzzleRequest):
    """Serves a precomputed news puzzle JSON by its precomputed file key."""
    path = os.path.join(NEWS_DIR, f"{request.news_id}.json")

    if not os.path.exists(path):
        raise HTTPException(
            status_code=404,
            detail=f"No precomputed puzzle for article '{request.news_id}'. "
                   f"Run: python weekly_precompute.py"
        )
    return _load_json(path)


@app.get("/api/debug/scrape")
def debug_info(url: str = ""):
    """On static deployment, shows what precomputed content is available."""
    news_index_path = os.path.join(PRECOMPUTED_DIR, "news_index.json")
    summary = {"mode": "static (precomputed)", "url_param_ignored": url}

    if os.path.exists(news_index_path):
        index = _load_json(news_index_path)
        summary["articles_by_level"] = {k: len(v) for k, v in index.items()}
    else:
        summary["news_index"] = "not found — run weekly_precompute.py"

    return summary


@app.post("/api/cache/clear")
def clear_cache():
    """No-op on static deployment (cache lives in Git, cleared by weekly_precompute.py)."""
    return {"status": "success", "detail": "Static deployment — no server-side cache to clear."}
