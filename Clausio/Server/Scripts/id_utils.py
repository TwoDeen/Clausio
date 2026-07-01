from __future__ import annotations


def safe_id(raw: str) -> str:
    return (
        (raw or "")
        .strip()
        .replace("/", "_")
        .replace("\\", "_")
        .replace("..", "_")
        .replace("?", "_")
        .replace("&", "_")
        .replace("=", "_")
        .replace(":", "_")
        .replace(".", "_")
    )[:200]
