from __future__ import annotations

from id_utils import safe_id

import argparse
import faulthandler
import glob
import json
import os
import shutil
import signal
import traceback

from corpus_providers import list_all_providers, get_provider
from generate_grid_puzzle import build_puzzle_json, build_puzzle_from_news_tokens


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PRECOMPUTED_DIR = os.path.join(BASE_DIR, "precomputed")
CORPUS_PRE_DIR = os.path.join(PRECOMPUTED_DIR, "corpus")
STORIES_PRE_DIR = os.path.join(PRECOMPUTED_DIR, "stories")
NEWS_PRE_DIR = os.path.join(PRECOMPUTED_DIR, "news")
CACHE_DIR = os.path.join(BASE_DIR, "_precompute_cache")

LEVELS = ["N5", "N4", "N3", "N2", "N1"]

for d in (PRECOMPUTED_DIR, CORPUS_PRE_DIR, STORIES_PRE_DIR, NEWS_PRE_DIR, CACHE_DIR):
    os.makedirs(d, exist_ok=True)


def _setup_fault_handler(timeout_seconds: int = 120) -> None:
    try:
        faulthandler.enable()
        faulthandler.register(signal.SIGUSR1)
        faulthandler.dump_traceback_later(timeout_seconds, repeat=False)
    except Exception as e:
        print(f"[WARN] Failed to enable faulthandler: {e}", flush=True)


def _cancel_fault_handler() -> None:
    try:
        faulthandler.cancel_dump_traceback_later()
    except Exception:
        pass


def _save(path: str, payload) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def _load(path: str):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _corpus_json_path(source: str, topic_id: str) -> str:
    return os.path.join(CORPUS_PRE_DIR, source, f"{safe_id(topic_id)}.json")


def _attach_corpus_ref(
    payload: dict,
    *,
    source: str,
    topic_id: str,
    title: str | None = None,
    link: str | None = None,
    file_path: str | None = None,
) -> dict:
    payload = dict(payload)
    safe_topic_id = safe_id(topic_id)

    payload["corpus_ref"] = {
        "source": source,
        "topic_id": topic_id,
        "safe_topic_id": safe_topic_id,
        "corpus_json_id": f"{source}/{safe_topic_id}",
        "corpus_json_path": f"precomputed/corpus/{source}/{safe_topic_id}.json",
        "title": title,
        "link": link,
        "file_path": file_path,
    }
    return payload


def _detected_level_from_payload(payload: dict) -> str:
    level = payload.get("highest_grammar_level_encountered", "N5")
    level = str(level).upper().strip()
    return level if level in LEVELS else "N5"


def _refresh_stories_index() -> None:
    stories_index = []

    for p in glob.glob(os.path.join(STORIES_PRE_DIR, "*.json")):
        name = os.path.basename(p)
        if not name.endswith(".json"):
            continue

        stem = name[:-5]
        parts = stem.rsplit("_", 1)
        if len(parts) != 2:
            continue

        story_name, level = parts
        if level not in LEVELS:
            continue

        stories_index.append({"name": story_name, "level": level})

    _save(os.path.join(PRECOMPUTED_DIR, "stories_index.json"), stories_index)


def _clean_all_generated() -> None:
    print("Cleaning all generated precomputed outputs...", flush=True)

    for path in (CORPUS_PRE_DIR, STORIES_PRE_DIR, NEWS_PRE_DIR):
        if os.path.exists(path):
            shutil.rmtree(path)

    for path in (
        os.path.join(PRECOMPUTED_DIR, "corpus_index.json"),
        os.path.join(PRECOMPUTED_DIR, "stories_index.json"),
    ):
        if os.path.exists(path):
            os.remove(path)

    for d in (PRECOMPUTED_DIR, CORPUS_PRE_DIR, STORIES_PRE_DIR, NEWS_PRE_DIR):
        os.makedirs(d, exist_ok=True)

    print("Clean complete.", flush=True)


def _clean_source_generated(source: str) -> None:
    print(f"Cleaning generated outputs for source: {source}", flush=True)

    source_dir = os.path.join(CORPUS_PRE_DIR, source)
    if os.path.exists(source_dir):
        shutil.rmtree(source_dir)

    if source == "aozora" and os.path.exists(STORIES_PRE_DIR):
        for p in glob.glob(os.path.join(STORIES_PRE_DIR, "*.json")):
            try:
                os.remove(p)
            except FileNotFoundError:
                pass

    os.makedirs(CORPUS_PRE_DIR, exist_ok=True)
    os.makedirs(os.path.join(CORPUS_PRE_DIR, source), exist_ok=True)
    os.makedirs(STORIES_PRE_DIR, exist_ok=True)
    os.makedirs(NEWS_PRE_DIR, exist_ok=True)

    print(f"Cleaned source: {source}", flush=True)


def precompute_all_corpora(
    limit_per_source=None,
    only_source: str | None = None,
    clean: bool = False,
    clean_source: str | None = None,
    target_level: str = "N5",
):
    target_level = str(target_level).upper().strip()
    if target_level not in LEVELS:
        raise SystemExit(f"Invalid target level: {target_level}. Expected one of {LEVELS}")

    if clean and clean_source:
        raise SystemExit("Use either --clean or --clean-source, not both.")

    if clean:
        _clean_all_generated()

    if clean_source:
        provider = get_provider(clean_source)
        if provider is None:
            raise SystemExit(f"Unknown source for --clean-source: {clean_source}")
        _clean_source_generated(clean_source)

    providers = list_all_providers()
    if only_source:
        provider = get_provider(only_source)
        if provider is None:
            raise SystemExit(f"Unknown source: {only_source}")
        providers = [provider]

    print(f"Found {len(providers)} corpus provider(s).", flush=True)
    print(f"Target generation level: {target_level}", flush=True)

    existing_corpus_index: dict[str, dict[str, list[dict]]] = {}
    corpus_index_path = os.path.join(PRECOMPUTED_DIR, "corpus_index.json")

    if os.path.exists(corpus_index_path) and not clean:
        try:
            existing_corpus_index = _load(corpus_index_path)
        except Exception:
            existing_corpus_index = {}

    if only_source:
        corpus_index = {
            k: v for k, v in existing_corpus_index.items() if k != only_source
        }
    elif clean_source:
        corpus_index = {
            k: v for k, v in existing_corpus_index.items() if k != clean_source
        }
    elif clean:
        corpus_index = {}
    else:
        corpus_index = existing_corpus_index

    for provider in providers:
        source = provider.SOURCE_ID
        print(f"\n=== Source: {source} ===", flush=True)

        if not provider.is_available():
            reason = (
                "VPN required / unavailable"
                if getattr(provider, "REQUIRES_VPN", False)
                else "source unavailable"
            )
            print(f" [SKIP] {reason}", flush=True)
            continue

        try:
            print(" Fetching topics...", flush=True)
            topics = provider.fetch_topics()
        except Exception as e:
            print(f" [ERR] fetch_topics failed: {e}", flush=True)
            traceback.print_exc()
            continue

        if limit_per_source is not None:
            topics = topics[:limit_per_source]

        print(f" Topics fetched: {len(topics)}", flush=True)

        source_entries: dict[str, list[dict]] = {}

        for i, topic in enumerate(topics, start=1):
            title_preview = (topic.title or "")[:80]
            print(f" [{i}/{len(topics)}] {title_preview}", flush=True)

            try:
                if source == "aozora":
                    file_path = topic.metadata.get("file_path", "")
                    if not file_path or not os.path.exists(file_path):
                        raise FileNotFoundError(
                            f"Aozora source file missing for topic '{topic.id}'"
                        )

                    payload = build_puzzle_json(file_path, target_level, CACHE_DIR)
                    if not payload:
                        raise ValueError("build_puzzle_json() returned empty payload")

                    payload = _attach_corpus_ref(
                        payload,
                        source=source,
                        topic_id=topic.id,
                        title=topic.title,
                        link=topic.link,
                        file_path=file_path,
                    )

                    detected_level = _detected_level_from_payload(payload)

                    legacy_story_path = os.path.join(
                        STORIES_PRE_DIR,
                        f"{topic.id}_{detected_level}.json",
                    )
                    _save(legacy_story_path, payload)

                    corpus_path = _corpus_json_path(source, topic.id)
                    _save(corpus_path, payload)

                else:
                    print("   Fetching sentences...", flush=True)
                    item = provider.fetch_sentences(topic)

                    if len(item.sentences) < 5:
                        print(f" [SKIP] only {len(item.sentences)} sentence(s)", flush=True)
                        continue

                    payload = build_puzzle_from_news_tokens(
                        item.sentences[:5],
                        item.furigana,
                        target_level,
                    )

                    if not payload:
                        raise ValueError(
                            "build_puzzle_from_news_tokens() returned empty payload"
                        )

                    payload = _attach_corpus_ref(
                        payload,
                        source=source,
                        topic_id=topic.id,
                        title=topic.title,
                        link=topic.link,
                        file_path=None,
                    )

                    detected_level = _detected_level_from_payload(payload)
                    corpus_path = _corpus_json_path(source, topic.id)
                    _save(corpus_path, payload)

                    if not os.path.exists(corpus_path):
                        raise FileNotFoundError(
                            f"Expected output file missing after save: {corpus_path}"
                        )

                source_entries.setdefault(detected_level, []).append(
                    {
                        "id": topic.id,
                        "title": topic.title,
                        "link": topic.link,
                        "detected_level": detected_level,
                        "target_level": target_level,
                        "safe_id": safe_id(topic.id),
                        "corpus_json_path": f"precomputed/corpus/{source}/{safe_id(topic.id)}.json",
                    }
                )

                print(f" [OK] target={target_level} detected={detected_level}", flush=True)

            except Exception as e:
                print(f" [ERR] {e}", flush=True)
                traceback.print_exc()

        corpus_index[source] = source_entries
        print(f" Completed source: {source}", flush=True)

    print("Saving corpus_index.json...", flush=True)
    _save(os.path.join(PRECOMPUTED_DIR, "corpus_index.json"), corpus_index)

    print("Refreshing stories_index.json...", flush=True)
    _refresh_stories_index()

    print("\nSaved corpus_index.json and refreshed stories_index.json", flush=True)
    print("precompute_all_corpora returned", flush=True)


if __name__ == "__main__":
    _setup_fault_handler(timeout_seconds=120)
    try:
        parser = argparse.ArgumentParser(description="Precompute Clausio corpus puzzles")
        parser.add_argument(
            "--limit-per-source",
            type=int,
            default=None,
            help="Limit topics per source for testing",
        )
        parser.add_argument(
            "--only-source",
            type=str,
            default=None,
            help="Run only one source, e.g. nhk_general",
        )
        parser.add_argument(
            "--clean",
            action="store_true",
            help="Delete all generated precomputed outputs before rebuilding",
        )
        parser.add_argument(
            "--clean-source",
            type=str,
            default=None,
            help="Delete generated outputs for one source before rebuilding it, e.g. nhk_easy",
        )
        parser.add_argument(
            "--target-level",
            type=str,
            default="N5",
            choices=LEVELS,
            help="Requested generation level to pass into puzzle builders",
        )

        args = parser.parse_args()

        precompute_all_corpora(
            limit_per_source=args.limit_per_source,
            only_source=args.only_source,
            clean=args.clean,
            clean_source=args.clean_source,
            target_level=args.target_level,
        )

        print("main completed", flush=True)

    finally:
        _cancel_fault_handler()
        print("shutdown complete", flush=True)
