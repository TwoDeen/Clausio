import json
import re
from pathlib import Path

import pytest

from clausify_alt import decompose_into_clauses_fallback

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "clausify_sentences.json"

BAD_EXACT_STARTS = (
    "の", "を", "に", "へ", "で", "も",
    "は", "が", "から", "まで", "より",
    "ぐらい", "くらい", "ごろ", "ころ",
)

BAD_MULTI_STARTS = (
    "、", "。", "！", "？",
    "ので", "のに",
)

ALLOWED_T_PREFIXES = (
    "とても",
    "と言",
    "とい",
    "という",
    "っていう",
)

FINAL_PREDICATE_ENDINGS = (
    "ました。", "ます。", "でした。", "です。",
    "した。", "する。", "いた。", "いる。",
    "だ。", "だった。", "ない。", "なかった。"
)


def load_fixture_data():
    with open(FIXTURE_PATH, encoding="utf-8") as f:
        return json.load(f)


SENTENCES = load_fixture_data()


def normalize(text: str) -> str:
    return re.sub(r"\s+", "", text)


def reconstruct(clauses) -> str:
    return "".join(clauses)


def clause_pairs(clauses):
    for i in range(len(clauses) - 1):
        yield clauses[i], clauses[i + 1]


@pytest.mark.parametrize("item", SENTENCES, ids=lambda x: x["id"])
def test_returns_exactly_five_clauses(item):
    clauses = decompose_into_clauses_fallback(item["sentence"])
    assert len(clauses) == 5


@pytest.mark.parametrize("item", SENTENCES, ids=lambda x: x["id"])
def test_all_clauses_are_nonempty(item):
    clauses = decompose_into_clauses_fallback(item["sentence"])
    assert all(c.strip() for c in clauses)


@pytest.mark.parametrize("item", SENTENCES, ids=lambda x: x["id"])
def test_reconstructs_original_sentence(item):
    clauses = decompose_into_clauses_fallback(item["sentence"])
    assert reconstruct(clauses) == normalize(item["sentence"])


@pytest.mark.parametrize("item", SENTENCES, ids=lambda x: x["id"])
def test_no_clause_starts_with_bad_fragment(item):
    expectations = item.get("expectations", {})
    if not expectations.get("no_bad_starts", False):
        pytest.skip("Not enabled for this fixture")

    clauses = decompose_into_clauses_fallback(item["sentence"])

    for clause in clauses[1:]:
        if clause.startswith(ALLOWED_T_PREFIXES):
            continue

        assert not clause.startswith(BAD_MULTI_STARTS), (
            f"{item['id']} produced bad clause start: {clause}"
        )

        assert clause not in BAD_EXACT_STARTS, (
            f"{item['id']} produced bad clause start: {clause}"
        )


@pytest.mark.parametrize("item", SENTENCES, ids=lambda x: x["id"])
def test_prefer_comma_boundary_when_requested(item):
    expectations = item.get("expectations", {})
    if not expectations.get("prefer_comma_boundary", False):
        pytest.skip("Not enabled for this fixture")

    clauses = decompose_into_clauses_fallback(item["sentence"])

    assert any(c.endswith("、") for c in clauses), (
        f"{item['id']} should prefer at least one comma-ending clause: {clauses}"
    )


@pytest.mark.parametrize("item", SENTENCES, ids=lambda x: x["id"])
def test_final_predicate_last_when_requested(item):
    expectations = item.get("expectations", {})
    if not expectations.get("prefer_final_predicate_last", False):
        pytest.skip("Not enabled for this fixture")

    clauses = decompose_into_clauses_fallback(item["sentence"])
    assert clauses[-1].endswith(FINAL_PREDICATE_ENDINGS), (
        f"{item['id']} should keep final predicate in last clause: {clauses[-1]}"
    )


@pytest.mark.parametrize("item", SENTENCES, ids=lambda x: x["id"])
def test_forbid_split_patterns(item):
    expectations = item.get("expectations", {})
    patterns = expectations.get("forbid_split_patterns", [])
    if not patterns:
        pytest.skip("No forbidden split patterns")

    clauses = decompose_into_clauses_fallback(item["sentence"])

    split_markers = []
    for left, right in clause_pairs(clauses):
        split_markers.append(f"{left}|{right}")

    joined = "\n".join(split_markers)

    for pattern in patterns:
        assert pattern not in joined, (
            f"{item['id']} matched forbidden split pattern '{pattern}':\n{joined}"
        )


@pytest.mark.parametrize(
    "item",
    [x for x in SENTENCES if "exact" in x.get("expectations", {})],
    ids=lambda x: x["id"]
)
def test_exact_regressions(item):
    clauses = decompose_into_clauses_fallback(item["sentence"])
    expected = item["expectations"]["exact"]
    assert clauses == expected


def test_fixture_file_has_unique_ids():
    ids = [item["id"] for item in SENTENCES]
    assert len(ids) == len(set(ids)), "Fixture IDs must be unique"


def test_fixture_file_sentences_nonempty():
    for item in SENTENCES:
        assert item["sentence"].strip(), f"Empty sentence in fixture {item['id']}"


def test_fixture_file_levels_valid():
    valid = {"N5", "N4", "N3", "N2", "N1"}
    for item in SENTENCES:
        assert item["level"] in valid, f"Invalid level in fixture {item['id']}"


@pytest.mark.parametrize("item", SENTENCES, ids=lambda x: x["id"])
def test_sentence_text_is_normalizable(item):
    normalized = normalize(item["sentence"])
    assert normalized, f"{item['id']} normalized to empty string"
