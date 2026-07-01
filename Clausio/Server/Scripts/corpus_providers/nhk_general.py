from __future__ import annotations

import urllib.request

from .base import CorpusItem, CorpusProvider, CorpusTopic
from news_service import _fetch_nhk_regular_topics, _scrape_nhk_regular

_NHK_REGULAR_RSS = "https://www3.nhk.or.jp/rss/news/cat0.xml"
_AVAILABILITY_TIMEOUT = 6


class NHKGeneralProvider(CorpusProvider):
    SOURCE_ID = "nhk_general"
    REQUIRES_VPN = True

    def is_available(self) -> bool:
        try:
            req = urllib.request.Request(
                _NHK_REGULAR_RSS,
                headers={"User-Agent": "Mozilla/5.0"},
            )
            with urllib.request.urlopen(req, timeout=_AVAILABILITY_TIMEOUT) as r:
                return r.status == 200
        except Exception:
            return False

    def fetch_topics(self) -> list[CorpusTopic]:
        raw = _fetch_nhk_regular_topics()
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
            raise ValueError(
                f"NHKGeneralProvider expected an HTTP URL as topic id, got: '{url}'"
            )

        sentences, furigana = _scrape_nhk_regular(url)

        return CorpusItem(
            id=topic.id,
            title=topic.title or url,
            link=url,
            sentences=sentences,
            furigana=furigana,
            source=self.SOURCE_ID,
            metadata={"scraped_url": url},
        )