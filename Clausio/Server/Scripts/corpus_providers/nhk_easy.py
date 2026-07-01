from __future__ import annotations

from .base import CorpusItem, CorpusProvider, CorpusTopic
from news_service import _fetch_nhk_easy_topics, _scrape_nhk_easy


class NHKEasyProvider(CorpusProvider):
    SOURCE_ID = "nhk_easy"
    REQUIRES_VPN = False

    def fetch_topics(self) -> list[CorpusTopic]:
        raw = _fetch_nhk_easy_topics()
        topics: list[CorpusTopic] = []

        for t in raw:
            url = t.get("link", "") or t.get("id", "")
            if not url:
                continue

            topics.append(
                CorpusTopic(
                    id=url,
                    title=t.get("title", "Untitled"),
                    link=url,
                    source=self.SOURCE_ID,
                    metadata={},
                )
            )

        return topics

    def fetch_sentences(self, topic: CorpusTopic) -> CorpusItem:
        url = topic.link or topic.id
        if not url.startswith("http"):
            raise ValueError(f"NHKEasyProvider expected HTTP URL, got: '{url}'")

        sentences, furigana = _scrape_nhk_easy(url)

        return CorpusItem(
            id=topic.id,
            title=topic.title or url,
            link=url,
            sentences=sentences,
            furigana=furigana,
            source=self.SOURCE_ID,
            metadata={"scraped_url": url},
        )