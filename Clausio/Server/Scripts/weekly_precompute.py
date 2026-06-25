"""
weekly_precompute.py
====================
Run locally every week to refresh puzzle content and push to Render.

Usage:
    python weekly_precompute.py              # news only
    python weekly_precompute.py --stories    # news + all story files
    python weekly_precompute.py --no-push    # generate only, skip git push

What it does:
    1. Fetches NHK topics for all 5 JLPT levels (Easy for N5/N4, Regular for N3-N1)
    2. Scrapes each article and generates a puzzle JSON via GiNZA
    3. Builds a news_index.json the Render server reads for /api/news/topics
    4. Optionally generates story JSONs from Stories/*.txt
    5. Commits precomputed/ and pushes — Render auto-deploys in ~30s
"""

import argparse
import glob
import json
import os
import subprocess
import sys
from datetime import datetime

# ── Local pipeline imports (GiNZA required) ───────────────────────────────────
try:
    from news_service import fetch_nhk_news_topics, scrape_article_sentences_and_furigana
    from generate_grid_puzzle import build_puzzle_from_news_tokens, build_puzzle_json
except ImportError as e:
    sys.exit(f"Missing local dependency: {e}\nRun: pip install -r requirements_local.txt")

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR          = os.path.dirname(os.path.abspath(__file__))
PRECOMPUTED_DIR   = os.path.join(BASE_DIR, "precomputed")
NEWS_DIR          = os.path.join(PRECOMPUTED_DIR, "news")
STORIES_PRE_DIR   = os.path.join(PRECOMPUTED_DIR, "stories")
STORIES_SRC_DIR   = os.path.join(BASE_DIR, "Stories")

os.makedirs(NEWS_DIR,        exist_ok=True)
os.makedirs(STORIES_PRE_DIR, exist_ok=True)

# ── Config ────────────────────────────────────────────────────────────────────
LEVELS             = ["N5", "N4", "N3", "N2", "N1"]
ARTICLES_PER_LEVEL = 10   # how many articles to keep per level

# ══════════════════════════════════════════════════════════════════════════════
# News precomputation
# ══════════════════════════════════════════════════════════════════════════════

def _file_key(level: str, url: str) -> str:
    """Stable, filesystem-safe key for a given level + article URL."""
    safe = url.replace("/", "_").replace(":", "_").replace(".", "_")
    return f"{level}_{safe}"[:200]   # cap at 200 chars to avoid filesystem limits


def precompute_news() -> dict:
    news_index = {level: [] for level in LEVELS}

    for level in LEVELS:
        print(f"\n── {level} ──────────────────────────────────────────────")
        try:
            topics = fetch_nhk_news_topics(level)
        except Exception as e:
            print(f"  [ERR] RSS fetch failed: {e}")
            continue

        success = 0
        for topic in topics:
            if success >= ARTICLES_PER_LEVEL:
                break

            url   = topic.get("link", "")
            title = topic.get("title", "Untitled")
            if not url:
                continue

            key         = _file_key(level, url)
            output_path = os.path.join(NEWS_DIR, f"{key}.json")

            # Re-use existing JSON (skip network + GiNZA work)
            if os.path.exists(output_path):
                news_index[level].append({"id": key, "title": title, "link": url})
                success += 1
                print(f"  [CACHED]  {title[:60]}")
                continue

            try:
                sentences, furigana = scrape_article_sentences_and_furigana(url)
                if len(sentences) < 5:
                    print(f"  [SKIP]    Not enough sentences — {url}")
                    continue

                payload = build_puzzle_from_news_tokens(sentences, furigana, level)

                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(payload, f, ensure_ascii=False, indent=2)

                news_index[level].append({"id": key, "title": title, "link": url})
                success += 1
                print(f"  [OK]      {title[:60]}")

            except Exception as e:
                print(f"  [ERR]     {url[:60]}: {e}")

        print(f"  → {success} articles ready for {level}")

    index_path = os.path.join(PRECOMPUTED_DIR, "news_index.json")
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(news_index, f, ensure_ascii=False, indent=2)

    total = sum(len(v) for v in news_index.values())
    print(f"\n✅ news_index.json written — {total} articles across all levels")
    return news_index


# ══════════════════════════════════════════════════════════════════════════════
# Story precomputation (run once; skips already-generated files)
# ══════════════════════════════════════════════════════════════════════════════

def precompute_stories() -> list:
    txt_files = glob.glob(os.path.join(STORIES_SRC_DIR, "**", "*.txt"), recursive=True)
    if not txt_files:
        print("No .txt files found in Stories/")
        return []

    stories_index = []
    print(f"\n── Stories ({len(txt_files)} source files × {len(LEVELS)} levels) ──────")

    for txt_path in txt_files:
        name = os.path.basename(txt_path).replace(".txt", "")
        for level in LEVELS:
            output_path = os.path.join(STORIES_PRE_DIR, f"{name}_{level}.json")

            if os.path.exists(output_path):
                stories_index.append({"name": name, "level": level, "id": f"{name}_{level}"})
                print(f"  [CACHED]  {name} @ {level}")
                continue

            try:
                payload = build_puzzle_json(txt_path, level, STORIES_PRE_DIR)
                if not payload:
                    print(f"  [SKIP]    {name} @ {level} — empty payload")
                    continue
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(payload, f, ensure_ascii=False, indent=2)
                stories_index.append({"name": name, "level": level, "id": f"{name}_{level}"})
                print(f"  [OK]      {name} @ {level}")
            except Exception as e:
                print(f"  [ERR]     {name} @ {level}: {e}")

    index_path = os.path.join(PRECOMPUTED_DIR, "stories_index.json")
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(stories_index, f, ensure_ascii=False, indent=2)

    print(f"\n✅ stories_index.json written — {len(stories_index)} entries")
    return stories_index


# ══════════════════════════════════════════════════════════════════════════════
# Git push
# ══════════════════════════════════════════════════════════════════════════════

def git_push():
    week = datetime.now().strftime("%Y-W%W")
    print(f"\n── Git push ─────────────────────────────────────────────")

    steps = [
        (["git", "add",    "precomputed/"],           "Stage precomputed/"),
        (["git", "commit", "-m", f"precompute: {week}"], "Commit"),
        (["git", "push"],                              "Push to GitHub"),
    ]

    for cmd, label in steps:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=BASE_DIR)
        if result.returncode != 0:
            # "nothing to commit" is not a real error
            if "nothing to commit" in result.stdout + result.stderr:
                print(f"  [SKIP]  {label} — nothing changed")
            else:
                print(f"  [WARN]  {label}: {result.stderr.strip()}")
        else:
            print(f"  [OK]    {label}")

    print("\n🚀 Render will auto-deploy in ~30 seconds.")


# ══════════════════════════════════════════════════════════════════════════════
# Entry point
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Clausio weekly precompute")
    parser.add_argument("--stories",  action="store_true", help="Also regenerate story puzzles")
    parser.add_argument("--no-push",  action="store_true", help="Skip git push")
    args = parser.parse_args()

    print("=" * 60)
    print(f"  Clausio Precompute — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)

    precompute_news()

    if args.stories:
        precompute_stories()

    if not args.no_push:
        git_push()
    else:
        print("\n[--no-push] Skipping git push.")
