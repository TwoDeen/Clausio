from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class CorpusTopic:
    id: str
    title: str
    link: str
    source: str
    metadata: dict = field(default_factory=dict)


@dataclass
class CorpusItem:
    id: str
    title: str
    link: str
    sentences: list[str]
    furigana: dict[str, str] = field(default_factory=dict)
    source: str = ""
    metadata: dict = field(default_factory=dict)


class CorpusProvider(ABC):
    SOURCE_ID: str = ""
    REQUIRES_VPN: bool = False

    @abstractmethod
    def fetch_topics(self) -> list[CorpusTopic]:
        """
        Return all available topics for this corpus.
        No JLPT filtering should happen here.
        """
        raise NotImplementedError

    @abstractmethod
    def fetch_sentences(self, topic: CorpusTopic) -> CorpusItem:
        """
        Resolve a topic into its sentence payload.

        This should work both when `topic.metadata` is populated
        and when the caller only provides a stub topic with:
        - id
        - title
        - link
        - source
        """
        raise NotImplementedError

    def is_available(self) -> bool:
        return True