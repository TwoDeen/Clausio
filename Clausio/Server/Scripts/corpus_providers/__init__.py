from __future__ import annotations

from .aozora import AozoraProvider
from .nhk_easy import NHKEasyProvider
from .nhk_general import NHKGeneralProvider
from .t15 import T15Provider
from .wjt_sentdil import WJTSentDilProvider
from .tadoku_scraper import TadokuProvider  # Added Tadoku import

_ALL_PROVIDERS = [
    NHKEasyProvider(),
    NHKGeneralProvider(),
    AozoraProvider(),
    T15Provider(),
    WJTSentDilProvider(),
    TadokuProvider(),  # Added Tadoku to the active list
]


def list_all_providers():
    return list(_ALL_PROVIDERS)


def get_all_providers():
    return list(_ALL_PROVIDERS)


def get_provider(source_id: str):
    source_id = source_id.strip().lower()
    return next((p for p in _ALL_PROVIDERS if p.SOURCE_ID == source_id), None)
