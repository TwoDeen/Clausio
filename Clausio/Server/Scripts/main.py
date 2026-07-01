import glob
import json
import os
import tempfile

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

try:
    from generate_grid_puzzle import build_puzzle_json, build_puzzle_from_news_tokens
    LIVE_MODE = True
except (Exception, SystemExit):
    LIVE_MODE = False

from corpus_providers import get_all_providers, get_provider

app = FastAPI(title="Clausio API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PRECOMPUTED_DIR = os.path.join(BASE_DIR, "precomputed")
NEWS_PRE_DIR = os.path.join(PRECOMPUTED_DIR, "news")
STORIES_PRE_DIR = os.path.join(PRECOMPUTED_DIR, "stories")
CORPUS_PRE_DIR = os.path.join(PRECOMPUTED_DIR, "corpus")
STORIES_SRC_DIR = os.path.join(BASE_DIR, "Stories")
CACHE_DIR = os.environ.get("CACHE_DIR", os.path.join(tempfile.gettempdir(), "ClausioCache"))

for d in (NEWS_PRE_DIR, STORIES_PRE_DIR, CORPUS_PRE_DIR, CACHE_DIR):
    os.makedirs(d, exist_ok=True)


class PuzzleRequest(BaseModel):
    file_path: str
    level: str


class NewsPuzzleRequest(BaseModel):
    news_id: str
    summary_html: str = ""
    level: str


class CorpusPuzzleRequest(BaseModel):
    source: str
    topic_id: str
    level: str


def _load(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _save(path: str, payload: dict):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def _story_name(file_path: str) -> str:
    return os.path.basename(file_path).replace(".txt", "")


def _safe_id(raw: str) -> str:
    return raw.replace("/", "_").replace(":", "_").replace(".", "_")[:200]


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

    if not os.path.exists(STORIES_SRC_DIR):
        return {"stories": []}

    found = glob.glob(os.path.join(STORIES_SRC_DIR, "**", "*.txt"), recursive=True)
    return {
        "stories": [
            {
                "name": os.path.basename(p).replace(".txt", ""),
                "relative_path": os.path.basename(p).replace(".txt", ""),
            }
            for p in sorted(found)
        ]
    }


@app.post("/api/puzzle/generate")
def fetch_story_puzzle(request: PuzzleRequest):
    level = request.level.upper().strip()
    story_name = _story_name(request.file_path)

    pre_path = os.path.join(STORIES_PRE_DIR, f"{story_name}_{level}.json")
    if os.path.exists(pre_path):
        return _load(pre_path)

    if LIVE_MODE:
        src_path = (
            request.file_path
            if os.path.exists(request.file_path)
            else os.path.join(STORIES_SRC_DIR, "miyazawa_kenji_stories", f"{story_name}.txt")
        )

        if not os.path.exists(src_path):
            raise HTTPException(status_code=404, detail=f"Source file not found: {story_name}")

        cache_path = os.path.join(CACHE_DIR, f"{story_name}_{level}_5x5_puzzle.json")
        if os.path.exists(cache_path):
            return _load(cache_path)

        payload = build_puzzle_json(src_path, level, CACHE_DIR)
        if not payload:
            raise HTTPException(status_code=500, detail="Puzzle generation returned empty payload.")

        _save(cache_path, payload)
        return payload

    raise HTTPException(
        status_code=404,
        detail=f"No precomputed puzzle for '{story_name}' at {level}.",
    )


@app.get("/api/corpus/sources")
def corpus_sources():
    sources = []

    for p in get_all_providers():
        entry = {
            "id": p.SOURCE_ID,
            "requires_vpn": p.REQUIRES_VPN,
            "available": p.is_available(),
        }

        if hasattr(p, "SUPPORTED_LEVELS"):
            try:
                entry["supports"] = sorted(list(p.SUPPORTED_LEVELS))
            except Exception:
                pass

        sources.append(entry)

    return {"sources": sources}


@app.get("/api/corpus/topics")
def get_corpus_topics(source: str, level: str = "N4"):
    source = source.strip().lower()
    level = level.upper().strip()
    index_path = os.path.join(PRECOMPUTED_DIR, "corpus_index.json")

    if not os.path.exists(index_path):
        raise HTTPException(
            status_code=404,
            detail="corpus_index.json not found. Run weekly_precompute.py"
        )

    index = _load(index_path)

    # weekly_precompute.py writes:
    # corpus_index[source][detected_level] = [ ... ]
    topics = index.get(source, {}).get(level, [])

    return {"status": "success", "topics": topics}


@app.post("/api/corpus/puzzle/generate")
def fetch_corpus_puzzle(request: CorpusPuzzleRequest):
    source = request.source.strip().lower()
    level = request.level.upper().strip()
    topic_id = request.topic_id

    pre_path = os.path.join(CORPUS_PRE_DIR, source, f"{_safe_id(topic_id)}.json")
    if os.path.exists(pre_path):
        return _load(pre_path)

    if not LIVE_MODE:
        raise HTTPException(
            status_code=404,
            detail="Precomputed puzzle not found and live mode is unavailable."
        )

    provider = get_provider(source)
    if not provider:
        raise HTTPException(status_code=404, detail=f"Unknown source: {source}")

    stub_topic = None
    for t in provider.fetch_topics():
        if t.id == topic_id or _safe_id(t.id) == _safe_id(topic_id):
            stub_topic = t
            break

    if stub_topic is None:
        raise HTTPException(status_code=404, detail=f"Topic not found: {topic_id}")

    if source == "aozora":
        src_path = stub_topic.metadata["file_path"]
        payload = build_puzzle_json(src_path, level, CACHE_DIR)
        if not payload:
            raise HTTPException(status_code=500, detail="Failed to generate Aozora puzzle.")
        return payload

    item = provider.fetch_sentences(stub_topic)
    if len(item.sentences) < 5:
        raise HTTPException(status_code=500, detail="Not enough valid Japanese sentences found.")

    payload = build_puzzle_from_news_tokens(item.sentences[:5], item.furigana, level)
    return payload
