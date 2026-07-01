from __future__ import annotations

import glob
import os

from .base import CorpusItem, CorpusProvider, CorpusTopic

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_STORIES_SRC = os.path.join(_PROJECT_ROOT, "Stories")


class AozoraProvider(CorpusProvider):
    SOURCE_ID = "aozora"
    REQUIRES_VPN = False

    def is_available(self) -> bool:
        return os.path.isdir(_STORIES_SRC) and bool(
            glob.glob(os.path.join(_STORIES_SRC, "**", "*.txt"), recursive=True)
        )

    def fetch_topics(self) -> list[CorpusTopic]:
        txt_files = sorted(
            glob.glob(os.path.join(_STORIES_SRC, "**", "*.txt"), recursive=True)
        )

        topics: list[CorpusTopic] = []
        for path in txt_files:
            name = os.path.basename(path).replace(".txt", "")
            topics.append(
                CorpusTopic(
                    id=name,
                    title=name.replace("_", " ").title(),
                    link="",
                    source=self.SOURCE_ID,
                    metadata={"file_path": path, "story_name": name},
                )
            )

        return topics

    def fetch_sentences(self, topic: CorpusTopic) -> CorpusItem:
        file_path = topic.metadata.get("file_path", "")
        if not file_path or not os.path.exists(file_path):
            story_name = topic.id
            file_path = _find_story_file(story_name)

        if not file_path or not os.path.exists(file_path):
            raise FileNotFoundError(
                f"Aozora source file not found for topic id '{topic.id}'. "
                f"Searched in: {_STORIES_SRC}"
            )

        sentences = _read_sentences(file_path)
        return CorpusItem(
            id=topic.id,
            title=topic.title or topic.id,
            link="",
            sentences=sentences,
            furigana={},
            source=self.SOURCE_ID,
            metadata={"file_path": file_path},
        )


def _find_story_file(story_name: str) -> str:
    pattern = os.path.join(_STORIES_SRC, "**", f"{story_name}.txt")
    matches = glob.glob(pattern, recursive=True)
    return matches[0] if matches else ""


def _read_sentences(file_path: str) -> list[str]:
    with open(file_path, encoding="utf-8") as f:
        raw = f.read()

    sentences = []
    for chunk in raw.replace("\n", "").split("。"):
        chunk = chunk.strip()
        if chunk:
            sentences.append(chunk + "。")
    return sentences