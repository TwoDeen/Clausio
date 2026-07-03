from __future__ import annotations

import glob
import json
import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PRECOMPUTED_DIR = os.path.join(BASE_DIR, "precomputed")
NEWS_PRE_DIR = os.path.join(PRECOMPUTED_DIR, "news")
STORIES_PRE_DIR = os.path.join(PRECOMPUTED_DIR, "stories")
CORPUS_PRE_DIR = os.path.join(PRECOMPUTED_DIR, "corpus")
STORIES_SRC_DIR = os.path.join(BASE_DIR, "Stories")

for d in (PRECOMPUTED_DIR, NEWS_PRE_DIR, STORIES_PRE_DIR, CORPUS_PRE_DIR):
    os.makedirs(d, exist_ok=True)

LEVELS = ["N5", "N4", "N3", "N2", "N1"]


app = FastAPI(title="Clausio API")
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


def _load(path: str):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _story_name(file_path: str) -> str:
    return os.path.basename(file_path).replace(".txt", "")


def _safe_id(raw: str) -> str:
    return raw.replace("/", "_").replace(":", "_").replace(".", "_")[:200]


def _normalize_level(level: str) -> str:
    normalized = str(level).upper().strip()
    if normalized not in LEVELS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid level: {level}. Expected one of {LEVELS}",
        )
    return normalized


def _load_corpus_index() -> dict:
    index_path = os.path.join(PRECOMPUTED_DIR, "corpus_index.json")
    if not os.path.exists(index_path):
        raise HTTPException(
            status_code=404,
            detail="corpus_index.json not found. Run weekly_precompute.py",
        )
    return _load(index_path)


def _flatten_topics_for_level(source_index, requested_level: str) -> list[dict]:
    if not isinstance(source_index, dict):
        return []

    requested_level = requested_level.upper().strip()
    out: list[dict] = []

    direct_bucket = source_index.get(requested_level, [])
    if isinstance(direct_bucket, list):
        for item in direct_bucket:
            if isinstance(item, dict):
                out.append(item)

    if out:
        return out

    for _, items in source_index.items():
        if not isinstance(items, list):
            continue

        for item in items:
            if not isinstance(item, dict):
                continue

            item_target = str(item.get("target_level", "")).upper().strip()
            item_detected = str(item.get("detected_level", "")).upper().strip()

            if item_target == requested_level or item_detected == requested_level:
                out.append(item)

    return out


def _find_topic_entry(index: dict, source: str, topic_id: str) -> dict | None:
    source_index = index.get(source, {})
    if not isinstance(source_index, dict):
        return None

    requested_safe = _safe_id(topic_id)

    for items in source_index.values():
        if not isinstance(items, list):
            continue

        for item in items:
            if not isinstance(item, dict):
                continue

            item_id = str(item.get("id", ""))
            item_safe = str(item.get("safe_id", _safe_id(item_id)))

            if item_id == topic_id or item_safe == topic_id or item_safe == requested_safe:
                return item

    return None


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "mode": "precomputed-only",
    }


@app.get("/api/stories")
def list_available_stories():
    index_path = os.path.join(PRECOMPUTED_DIR, "stories_index.json")
    if not os.path.exists(index_path):
        return {"stories": []}

    index = _load(index_path)
    seen, out = set(), []

    for entry in index:
        name = entry.get("name")
        if not name or name in seen:
            continue
        seen.add(name)
        out.append({"name": name, "relative_path": name})

    return {"stories": out}

@app.post("/api/puzzle/generate")
def fetch_story_puzzle(request: PuzzleRequest):
    level = _normalize_level(request.level)
    story_name = _story_name(request.file_path)

    pre_path = os.path.join(STORIES_PRE_DIR, f"{story_name}_{level}.json")
    if os.path.exists(pre_path):
        return _load(pre_path)

    raise HTTPException(
        status_code=404,
        detail=f"No precomputed puzzle for '{story_name}' at {level}.",
    )


@app.get("/api/corpus/sources")
def corpus_sources():
    index = _load_corpus_index()

    sources = []
    for source_id, buckets in sorted(index.items()):
        supports = []
        if isinstance(buckets, dict):
            supports = [lvl for lvl in LEVELS if lvl in buckets]

        sources.append(
            {
                "id": source_id,
                "supports": supports,
                "requires_vpn": False,
                "available": True,
            }
        )

    return {"sources": sources}


@app.get("/api/corpus/topics")
def get_corpus_topics(source: str, level: str = "N4"):
    level = _normalize_level(level)
    index = _load_corpus_index()

    source_index = index.get(source)
    if source_index is None:
        return {
            "status": "success",
            "source": source,
            "requested_level": level,
            "topics": [],
        }

    topics = _flatten_topics_for_level(source_index, level)

    return {
        "status": "success",
        "source": source,
        "requested_level": level,
        "topics": topics,
    }


@app.post("/api/corpus/puzzle/generate")
def fetch_corpus_puzzle(request: CorpusPuzzleRequest):
    source = request.source
    _normalize_level(request.level)
    topic_id = request.topic_id
    safe_topic_id = _safe_id(topic_id)

    pre_path_candidates = [
        os.path.join(CORPUS_PRE_DIR, source, f"{topic_id}.json"),
        os.path.join(CORPUS_PRE_DIR, source, f"{safe_topic_id}.json"),
    ]

    for pre_path in pre_path_candidates:
        if os.path.exists(pre_path):
            return _load(pre_path)

    index = _load_corpus_index()
    topic_entry = _find_topic_entry(index, source, topic_id)
    if topic_entry:
        indexed_safe = str(topic_entry.get("safe_id", safe_topic_id))
        indexed_path = os.path.join(CORPUS_PRE_DIR, source, f"{indexed_safe}.json")
        if os.path.exists(indexed_path):
            return _load(indexed_path)

    raise HTTPException(
        status_code=404,
        detail=f"No precomputed corpus puzzle found for source='{source}' topic_id='{topic_id}'.",
    )
