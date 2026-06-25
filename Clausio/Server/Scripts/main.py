"""
main.py — Clausio API
=====================
Single file that works in two modes automatically:

  Render (free tier)   — serves precomputed JSONs committed to Git.
                         No GiNZA, no scraping, no heavy deps.

  Local (your Mac)     — falls back to live GiNZA generation when a
                         precomputed file is missing. Same endpoints,
                         same iOS client, no config changes needed.

Mode is detected at startup: if generate_grid_puzzle / news_service
can be imported (GiNZA installed) → LIVE_MODE = True, otherwise False.
"""

import glob
import json
import os
import tempfile

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ── Live pipeline (local only — Render never has these deps installed) ────────
try:
    from generate_grid_puzzle import build_puzzle_json, build_puzzle_from_news_tokens
    from news_service import fetch_nhk_news_topics, scrape_article_sentences_and_furigana
    LIVE_MODE = True
except (Exception, SystemExit):  # <-- ADDED SystemExit HERE
    LIVE_MODE = False
    
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
NEWS_PRE_DIR    = os.path.join(PRECOMPUTED_DIR, "news")
STORIES_PRE_DIR = os.path.join(PRECOMPUTED_DIR, "stories")
STORIES_SRC_DIR = os.path.join(BASE_DIR, "Stories")
CACHE_DIR       = os.environ.get("CACHE_DIR",
                    os.path.join(tempfile.gettempdir(), "ClausioCache"))

for d in (NEWS_PRE_DIR, STORIES_PRE_DIR, CACHE_DIR):
    os.makedirs(d, exist_ok=True)

print(f"--> Clausio API  |  {'live+precomputed' if LIVE_MODE else 'precomputed-only (Render)'}")
print(f"--> Precomputed  : {PRECOMPUTED_DIR}")
print(f"--> Stories src  : {STORIES_SRC_DIR}")


# ── Pydantic models ───────────────────────────────────────────────────────────

class PuzzleRequest(BaseModel):
    file_path: str
    level: str

class NewsPuzzleRequest(BaseModel):
    news_id: str
    summary_html: str
    level: str


# ── Helpers ───────────────────────────────────────────────────────────────────

def _load(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def _story_name(file_path: str) -> str:
    """Works whether iOS sends a bare name or a legacy full path."""
    return os.path.basename(file_path).replace(".txt", "")

def _safe_id(raw: str) -> str:
    return raw.replace("/", "_").replace(":", "_")[:200]


# ══════════════════════════════════════════════════════════════════════════════
# /api/stories
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/api/stories")
def list_available_stories():
    index_path = os.path.join(PRECOMPUTED_DIR, "stories_index.json")
    if os.path.exists(index_path):
        index = _load(index_path)
        seen, out = set(), []
        for entry in index:
            if entry["name"] not in seen:
                seen.add(entry["name"])
                out.append({"name": entry["name"], "relative_path": entry["name"]})
        return {"stories": out}

    # Fallback: scan committed .txt source files
    if not os.path.exists(STORIES_SRC_DIR):
        return {"stories": []}
    found = glob.glob(os.path.join(STORIES_SRC_DIR, "**", "*.txt"), recursive=True)
    return {"stories": [
        {"name":          os.path.basename(p).replace(".txt", ""),
         "relative_path": os.path.basename(p).replace(".txt", "")}
        for p in sorted(found)
    ]}


# ══════════════════════════════════════════════════════════════════════════════
# /api/news/topics
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/api/news/topics")
def get_news_topics(level: str = "N4"):
    level = level.upper().strip()
    index_path = os.path.join(PRECOMPUTED_DIR, "news_index.json")

    # ── Precomputed path (Render + local after weekly_precompute.py) ──────────
    if os.path.exists(index_path):
        index  = _load(index_path)
        topics = index.get(level, [])
        return {
            "status": "success",
            "topics": [{"id": t["id"], "title": t["title"],
                        "link": t.get("link", ""), "summary_html": ""}
                       for t in topics],
        }

    # ── Live RSS fallback (local only) ────────────────────────────────────────
    if LIVE_MODE:
        try:
            feeds = fetch_nhk_news_topics(level)
            return {"status": "success", "topics": feeds}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    raise HTTPException(
        status_code=503,
        detail="News index not available. Run: python weekly_precompute.py"
    )


# ══════════════════════════════════════════════════════════════════════════════
# /api/puzzle/generate   (Aozora stories)
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/api/puzzle/generate")
def fetch_story_puzzle(request: PuzzleRequest):
    level      = request.level.upper().strip()
    story_name = _story_name(request.file_path)

    # ── Precomputed path ──────────────────────────────────────────────────────
    pre_path = os.path.join(STORIES_PRE_DIR, f"{story_name}_{level}.json")
    if os.path.exists(pre_path):
        return _load(pre_path)

    # ── Live GiNZA fallback (local only) ─────────────────────────────────────
    if LIVE_MODE:
        # Accept both bare name and legacy full path from iOS
        src_path = (request.file_path
                    if os.path.exists(request.file_path)
                    else os.path.join(STORIES_SRC_DIR, "miyazawa_kenji_stories",
                                      f"{story_name}.txt"))
        if not os.path.exists(src_path):
            raise HTTPException(status_code=404,
                                detail=f"Source file not found: {story_name}")

        cache_path = os.path.join(CACHE_DIR, f"{story_name}_{level}_5x5_puzzle.json")
        if os.path.exists(cache_path):
            return _load(cache_path)

        payload = build_puzzle_json(src_path, level, CACHE_DIR)
        if not payload:
            raise HTTPException(status_code=500, detail="Puzzle generation returned empty payload.")
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        return payload

    raise HTTPException(
        status_code=404,
        detail=f"No precomputed puzzle for '{story_name}' at {level}. "
               f"Run: python weekly_precompute.py --stories"
    )


# ══════════════════════════════════════════════════════════════════════════════
# /api/news/puzzle/generate
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/api/news/puzzle/generate")
def fetch_news_puzzle(request: NewsPuzzleRequest):
    news_id      = request.news_id
    target_level = request.level.upper().strip()

    # ── Precomputed path (news_id IS the file key when served from index) ─────
    pre_path = os.path.join(NEWS_PRE_DIR, f"{news_id}.json")
    if os.path.exists(pre_path):
        return _load(pre_path)

    # ── Live fallback: news_id is a raw URL (local, topics served from RSS) ───
    if LIVE_MODE and news_id.startswith("http"):
        safe_id    = _safe_id(news_id)
        cache_path = os.path.join(CACHE_DIR,
                                  f"news_{safe_id}_{target_level}_5x5_puzzle.json")
        if os.path.exists(cache_path):
            return _load(cache_path)

        try:
            sentences, furigana = scrape_article_sentences_and_furigana(news_id)
            if len(sentences) < 5:
                raise ValueError("Not enough valid Japanese sentences found.")
            payload = build_puzzle_from_news_tokens(sentences, furigana, target_level)
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            return payload
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    raise HTTPException(
        status_code=404,
        detail=f"No precomputed puzzle for '{news_id}'. "
               f"Run: python weekly_precompute.py"
    )


# ══════════════════════════════════════════════════════════════════════════════
# Utility
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/api/debug/scrape")
def debug_info(url: str = ""):
    index_path = os.path.join(PRECOMPUTED_DIR, "news_index.json")
    info = {"mode": "live+precomputed" if LIVE_MODE else "precomputed-only"}
    if os.path.exists(index_path):
        idx = _load(index_path)
        info["articles_by_level"] = {k: len(v) for k, v in idx.items()}
    if LIVE_MODE and url.startswith("http"):
        sentences, furigana = scrape_article_sentences_and_furigana(url)
        info["scraped_sentences"] = sentences
        info["furigana_count"]    = len(furigana)
    return info


@app.post("/api/cache/clear")
def clear_cache():
    purged = 0
    for f in glob.glob(os.path.join(CACHE_DIR, "*.json")):
        os.remove(f)
        purged += 1
    return {"status": "success",
            "detail": f"Cleared {purged} files from live cache. "
                      f"Precomputed/ lives in Git — run weekly_precompute.py to refresh."}
