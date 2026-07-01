from __future__ import annotations

import csv
import os

from .base import CorpusItem, CorpusProvider, CorpusTopic

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_WJT_FILE = os.path.join(_PROJECT_ROOT, "Sources", "WJTSentDil", "sentences.tsv")

_BATCH_SIZE = 5
_MAX_BATCHES = 40


class WJTSentDilProvider(CorpusProvider):
    SOURCE_ID = "wjt_sentdil"
    REQUIRES_VPN = False

    def is_available(self) -> bool:
        return os.path.isfile(_WJT_FILE)

    def fetch_topics(self) -> list[CorpusTopic]:
        all_sentences = _load_all_sentences()
        topics: list[CorpusTopic] = []

        limit = min(len(all_sentences), _BATCH_SIZE * _MAX_BATCHES)

        for start in range(0, limit, _BATCH_SIZE):
            end = start + _BATCH_SIZE - 1
            if end >= len(all_sentences):
                break

            topic_id = f"wjt_rows_{start}_{end}"
            batch = all_sentences[start : end + 1]

            topics.append(
                CorpusTopic(
                    id=topic_id,
                    title=f"WJT Sentences {start + 1}-{end + 1}",
                    link="",
                    source=self.SOURCE_ID,
                    metadata={
                        "sentences": batch,
                        "start": start,
                        "end": end,
                    },
                )
            )

        return topics

    def fetch_sentences(self, topic: CorpusTopic) -> CorpusItem:
        sentences = topic.metadata.get("sentences", [])

        if not sentences:
            start, end = _parse_row_bounds(topic.id)
            if start is None or end is None:
                raise ValueError(
                    "WJTSentDilProvider: cannot reconstruct sentences from "
                    f"topic id '{topic.id}'. Expected format: wjt_rows_{{start}}_{{end}}"
                )

            all_sentences = _load_all_sentences()
            sentences = all_sentences[start : end + 1]

        if not sentences:
            raise ValueError(
                f"WJTSentDilProvider: no sentences resolved for topic '{topic.id}'."
            )

        return CorpusItem(
            id=topic.id,
            title=topic.title or topic.id,
            link="",
            sentences=sentences,
            furigana={},
            source=self.SOURCE_ID,
            metadata={},
        )


def _load_all_sentences() -> list[str]:
    sentences: list[str] = []

    with open(_WJT_FILE, encoding="utf-8") as f:
        reader = csv.reader(f, delimiter="\t")
        for row in reader:
            if not row:
                continue

            sent = row[0].strip()
            if sent and (sent.endswith("。") or sent.endswith("｡")):
                sentences.append(sent)

    return sentences


def _parse_row_bounds(topic_id: str):
    prefix = "wjt_rows_"
    if not topic_id.startswith(prefix):
        return None, None

    rest = topic_id[len(prefix) :]
    parts = rest.split("_")
    if len(parts) != 2:
        return None, None

    try:
        return int(parts[0]), int(parts[1])
    except ValueError:
        return None, None