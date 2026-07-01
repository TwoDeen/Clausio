from __future__ import annotations

import csv, os
from .base import CorpusItem, CorpusProvider, CorpusTopic

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_T15_DIR      = os.path.join(_PROJECT_ROOT, "Sources", "T15")
_VALID_EXT    = (".txt", ".tsv", ".csv")


class T15Provider(CorpusProvider):
    SOURCE_ID    = "t15"
    REQUIRES_VPN = False

    def is_available(self) -> bool:
        return os.path.isdir(_T15_DIR) and _has_valid_files(_T15_DIR)

    def fetch_topics(self) -> list[CorpusTopic]:
        if not os.path.isdir(_T15_DIR):
            return []
        topics = []
        for full_path in _collect_files(_T15_DIR):
            rel_path = os.path.relpath(full_path, _T15_DIR)
            stem     = os.path.splitext(os.path.basename(full_path))[0]
            topics.append(CorpusTopic(
                id=f"t15::{rel_path}",
                title=stem.replace("_", " ").replace("-", " "),
                link="", source=self.SOURCE_ID,
                metadata={"file_path": full_path, "relative_path": rel_path},
            ))
        return topics

    def fetch_sentences(self, topic: CorpusTopic) -> CorpusItem:
        file_path = topic.metadata.get("file_path", "")
        if not file_path or not os.path.exists(file_path):
            file_path = _topic_id_to_path(topic.id)
        if not file_path or not os.path.exists(file_path):
            raise FileNotFoundError(f"T15: file not found for topic '{topic.id}'")
        ext = os.path.splitext(file_path)[1].lower()
        sentences = _read_tsv(file_path) if ext == ".tsv" \
               else _read_csv(file_path) if ext == ".csv" \
               else _read_txt(file_path)
        return CorpusItem(
            id=topic.id, title=topic.title, link="",
            sentences=sentences, furigana={}, source=self.SOURCE_ID,
            metadata={"file_path": file_path},
        )


def _collect_files(root: str) -> list[str]:
    result = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort()
        for fname in sorted(filenames):
            if fname.endswith(_VALID_EXT):
                result.append(os.path.join(dirpath, fname))
    return result

def _has_valid_files(root: str) -> bool:
    for _, _, files in os.walk(root):
        for f in files:
            if f.endswith(_VALID_EXT):
                return True
    return False

def _topic_id_to_path(topic_id: str) -> str:
    prefix = "t15::"
    if not topic_id.startswith(prefix):
        return ""
    return os.path.join(_T15_DIR, topic_id[len(prefix):])

def _read_txt(path: str) -> list[str]:
    with open(path, encoding="utf-8") as f:
        return [ln.strip() for ln in f if ln.strip()]

def _read_tsv(path: str) -> list[str]:
    with open(path, encoding="utf-8") as f:
        return [row[0].strip() for row in csv.reader(f, delimiter="\t") if row and row[0].strip()]

def _read_csv(path: str) -> list[str]:
    with open(path, encoding="utf-8") as f:
        return [row[0].strip() for row in csv.reader(f) if row and row[0].strip()]