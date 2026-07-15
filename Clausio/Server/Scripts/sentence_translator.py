from __future__ import annotations

import os
import time
from typing import List, Dict

try:
    from ollama import chat
except Exception:
    chat = None


DEFAULT_MODEL = os.getenv("OLLAMA_TRANSLATION_MODEL", "translategemma")
DEFAULT_TEMPERATURE = 0
MAX_RETRIES = 3
RETRY_SLEEP_SECONDS = 2.0


def _normalize_sentence(text: str) -> str:
    return (text or "").strip()


def _empty_result(sentences: List[str]) -> List[Dict[str, str]]:
    return [
        {
            "sentence_id": i + 1,
            "japanese": sentence,
            "english_translation": "",
        }
        for i, sentence in enumerate(sentences)
    ]


def _extract_message_content(response) -> str:
    if response is None:
        return ""

    try:
        content = response["message"]["content"]
        if isinstance(content, str):
            return content.strip()
    except Exception:
        pass

    try:
        content = response.message.content
        if isinstance(content, str):
            return content.strip()
    except Exception:
        pass

    return ""


def translate_one_sentence(
    sentence: str,
    *,
    model: str = DEFAULT_MODEL,
) -> str:
    sentence = _normalize_sentence(sentence)
    if not sentence:
        return ""

    if chat is None:
        print("[WARN] Ollama Python library is not installed. Run: pip install ollama")
        return ""

    last_error = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = chat(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a Japanese-to-English translator. Return only the English translation."
                    },
                    {
                        "role": "user",
                        "content": f"To English: {sentence}"
                    },
                ],
                options={"temperature": DEFAULT_TEMPERATURE},
            )

            text = _extract_message_content(response)
            if text:
                return text

            raise ValueError("Ollama returned empty content")

        except Exception as e:
            last_error = e
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_SLEEP_SECONDS * attempt)

    print(f"[WARN] Failed to translate sentence after {MAX_RETRIES} attempts: {last_error}")
    return ""


def translate_sentences_to_english(
    sentences: List[str],
    *,
    model: str = DEFAULT_MODEL,
) -> List[Dict[str, str]]:
    normalized = [_normalize_sentence(s) for s in sentences if _normalize_sentence(s)]

    if not normalized:
        return []

    results = []
    for i, sentence in enumerate(normalized):
        english = translate_one_sentence(sentence, model=model)
        results.append(
            {
                "sentence_id": i + 1,
                "japanese": sentence,
                "english_translation": english,
            }
        )

    return results


if __name__ == "__main__":
    sample_sentences = [
        "わたしはパンが大好きだ。"
    ]
    result = translate_sentences_to_english(sample_sentences)
    print(result)
