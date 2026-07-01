from __future__ import annotations
from id_utils import safe_id

import json
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


BASE_DIR = Path(__file__).resolve().parent
PRECOMPUTED_DIR = BASE_DIR / "precomputed"
NEWS_PRE_DIR = PRECOMPUTED_DIR / "news"
STORIES_PRE_DIR = PRECOMPUTED_DIR / "stories"
CORPUS_PRE_DIR = PRECOMPUTED_DIR / "corpus"

REQUIRED_INDEX_FILES = [
    PRECOMPUTED_DIR / "stories_index.json",
    PRECOMPUTED_DIR / "news_index.json",
    PRECOMPUTED_DIR / "corpus_index.json",
]

VALID_LEVELS = {"N5", "N4", "N3", "N2", "N1"}


def _load_json(path: Path):
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _normalize_level(level: str) -> str:
    normalized = (level or "").upper().strip()
    if normalized not in VALID_LEVELS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid level '{level}'. Expected one of: N5, N4, N3, N2, N1.",
        )
    return normalized


def _story_name(file_path: str) -> str:
    return os.path.basename(file_path).replace(".txt", "").strip()


def _require_precomputed_startup() -> None:
    missing = [str(p) for p in REQUIRED_INDEX_FILES if not p.exists()]
    if missing:
        raise RuntimeError(
            "Missing required precomputed files. "
            "Run weekly_precompute.py before starting the API. "
            f"Missing: {', '.join(missing)}"
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    _require_precomputed_startup()
    yield


app = FastAPI(title="Clausio API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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


@app.get("/api/stories")
def list_available_stories():
    index_path = PRECOMPUTED_DIR / "stories_index.json"
    index = _load_json(index_path)

    seen = set()
    stories = []

    for entry in index:
        name = entry.get("name", "").strip()
        if not name or name in seen:
            continue
        seen.add(name)
        stories.append(
            {
                "name": name,
                "relative_path": name,
            }
        )

    return {"stories": stories}


@app.get("/api/news/topics")
def get_news_topics(level: str = "N4"):
    normalized_level = _normalize_level(level)
    index_path = PRECOMPUTED_DIR / "news_index.json"
    index = _load_json(index_path)
    topics = index.get(normalized_level, [])

    return {
        "status": "success",
        "topics": [
            {
                "id": t["id"],
                "title": t["title"],
                "link": t.get("link", ""),
                "summary_html": "",
            }
            for t in topics
        ],
    }


@app.post("/api/puzzle/generate")
def fetch_story_puzzle(request: PuzzleRequest):
    level = _normalize_level(request.level)
    story_name = _story_name(request.file_path)
    path = STORIES_PRE_DIR / f"{story_name}_{level}.json"

    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail=(
                f"No precomputed story puzzle for '{story_name}' at level '{level}'. "
                "Run weekly_precompute.py and redeploy."
            ),
        )

    return _load_json(path)


@app.post("/api/news/puzzle/generate")
def fetch_news_puzzle(request: NewsPuzzleRequest):
    _normalize_level(request.level)
    path = NEWS_PRE_DIR / f"{safe_id(request.news_id)}.json"

    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail=(
                f"No precomputed news puzzle for article '{request.news_id}'. "
                "Run weekly_precompute.py and redeploy."
            ),
        )

    return _load_json(path)


@app.get("/api/corpus/sources")
def corpus_sources():
    index_path = PRECOMPUTED_DIR / "corpus_index.json"
    index = _load_json(index_path)

    sources = []
    for source, by_level in sorted(index.items()):
        supports = sorted(
            [level for level, items in by_level.items() if items],
            key=lambda x: ["N5", "N4", "N3", "N2", "N1"].index(x),
        )
        sources.append(
            {
                "id": source,
                "supports": supports,
                "requires_vpn": source == "nhk_general",
                "available": True,
            }
        )

    return {"sources": sources}


@app.get("/api/corpus/topics")
def get_corpus_topics(source: str, level: str = "N4"):
    normalized_level = _normalize_level(level)
    normalized_source = (source or "").strip()

    index_path = PRECOMPUTED_DIR / "corpus_index.json"
    index = _load_json(index_path)

    if normalized_source not in index:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown corpus source '{normalized_source}'.",
        )

    topics = index.get(normalized_source, {}).get(normalized_level, [])

    return {
        "status": "success",
        "topics": topics,
    }


@app.post("/api/corpus/puzzle/generate")
def fetch_corpus_puzzle(request: CorpusPuzzleRequest):
    _normalize_level(request.level)
    source = (request.source or "").strip()
    topic_id = (request.topic_id or "").strip()

    if not source:
        raise HTTPException(status_code=400, detail="source is required.")
    if not topic_id:
        raise HTTPException(status_code=400, detail="topic_id is required.")

    path = CORPUS_PRE_DIR / source / f"{safe_id(topic_id)}.json"

    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail=(
                f"No precomputed corpus puzzle for source='{source}', topic_id='{topic_id}'. "
                "Run weekly_precompute.py and redeploy."
            ),
        )

    return _load_json(path)

@app.get("/api/debug/file-check")
def debug_file_check(source: str, topic_id: str):
    safe = safe_id(topic_id)
    path = CORPUS_PRE_DIR / source / f"{safe}.json"
    return {
        "source": source,
        "topic_id": topic_id,
        "safe_id": safe,
        "computed_path": str(path),
        "exists": path.exists(),
    }

@app.get("/api/debug/scrape")
def debug_info(url: str = ""):
    summary = {
        "mode": "static-precomputed-only",
        "url_param_ignored": url,
    }

    stories_index_path = PRECOMPUTED_DIR / "stories_index.json"
    news_index_path = PRECOMPUTED_DIR / "news_index.json"
    corpus_index_path = PRECOMPUTED_DIR / "corpus_index.json"

    if stories_index_path.exists():
        stories_index = _load_json(stories_index_path)
        summary["stories_count"] = len(stories_index)

    if news_index_path.exists():
        news_index = _load_json(news_index_path)
        summary["articles_by_level"] = {
            level: len(items) for level, items in news_index.items()
        }

    if corpus_index_path.exists():
        corpus_index = _load_json(corpus_index_path)
        summary["corpus_sources"] = {
            source: {level: len(items) for level, items in levels.items()}
            for source, levels in corpus_index.items()
        }

    return summary


@app.post("/api/cache/clear")
def clear_cache():
    return {
        "status": "success",
        "detail": "Static precomputed deployment — no server-side cache to clear.",
    }
