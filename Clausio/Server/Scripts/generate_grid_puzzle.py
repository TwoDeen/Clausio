import sys
import os
import json
import re
from typing import List, Dict, Optional

try:
    from clausify import decompose_into_clauses_fallback
    from complete_jlpt_analyzer import analyze_sentence_grammar
except ImportError as e:
    print(f"Error: Missing dependency script. {e}", file=sys.stderr)
    print(
        "Please ensure 'clausify.py' and 'complete_jlpt_analyzer.py' are in this root folder.",
        file=sys.stderr,
    )
    sys.exit(1)


MAX_SUDACHI_BYTES = 45_000
LEVEL_HIERARCHY = {"N5": 1, "N4": 2, "N3": 3, "N2": 4, "N1": 5}
REVERSE_HIERARCHY = {1: "N5", 2: "N4", 3: "N3", 4: "N2", 5: "N1"}

_NLP = None


def _utf8_len(text: str) -> int:
    return len(text.encode("utf-8"))


def _get_nlp():
    global _NLP
    if _NLP is not None:
        return _NLP

    try:
        import spacy
    except Exception as e:
        print(f"Error importing spaCy: {e}", file=sys.stderr)
        return None

    config = {
        "components": {
            "compound_splitter": {
                "split_mode": "C",
            }
        }
    }

    try:
        _NLP = spacy.load("ja_ginza", config=config)
    except Exception as e:
        print(f"Error loading GiNZa pipeline: {e}", file=sys.stderr)
        _NLP = None

    return _NLP


def _chunk_text_for_sudachi(text: str, max_bytes: int = MAX_SUDACHI_BYTES) -> List[str]:
    text = text.strip()
    if not text:
        return []

    if _utf8_len(text) <= max_bytes:
        return [text]

    pieces = [p.strip() for p in re.split(r"(?<=[。！？])", text) if p.strip()]

    chunks = []
    current = ""

    for piece in pieces:
        candidate = current + piece
        if current and _utf8_len(candidate) > max_bytes:
            chunks.append(current)
            current = piece
        else:
            current = candidate

    if current:
        chunks.append(current)

    final_chunks = []
    for chunk in chunks:
        if _utf8_len(chunk) <= max_bytes:
            final_chunks.append(chunk)
            continue

        start = 0
        while start < len(chunk):
            end = start
            current_bytes = 0
            while end < len(chunk):
                char_bytes = len(chunk[end].encode("utf-8"))
                if current_bytes + char_bytes > max_bytes:
                    break
                current_bytes += char_bytes
                end += 1

            piece = chunk[start:end].strip()
            if piece:
                final_chunks.append(piece)

            if end == start:
                end += 1
            start = end

    return [c for c in final_chunks if c.strip()]


def _katakana_to_hiragana(text: str) -> str:
    return "".join(
        chr(ord(char) - 0x60) if 0x30A1 <= ord(char) <= 0x30F6 else char
        for char in text
    )


def _extract_reading(token) -> str:
    reading = ""

    try:
        if token.tag_ and "," in token.tag_:
            features = token.tag_.split(",")
            if len(features) >= 8 and features[7] != "*":
                reading = features[7]
            elif len(features) >= 7 and features[6] != "*":
                reading = features[6]
    except Exception:
        pass

    if not reading:
        try:
            if hasattr(token._, "reading") and token._.reading:
                reading = token._.reading
        except Exception:
            pass

    if not reading:
        try:
            if hasattr(token._, "sudachi_morph") and token._.sudachi_morph:
                reading = token._.sudachi_morph.reading()
        except Exception:
            pass

    if not reading:
        try:
            if token.morph and token.morph.get("Reading"):
                reading_list = token.morph.get("Reading")
                if reading_list:
                    reading = reading_list[0]
        except Exception:
            pass

    return reading or ""


def _reading_or_surface(token) -> str:
    reading = _extract_reading(token)
    return _katakana_to_hiragana(reading) if reading else token.text


def _safe_detect_level(doc) -> str:
    try:
        detected_level, _ = analyze_sentence_grammar(doc)
        detected_level = str(detected_level).upper().strip()
        return detected_level if detected_level in LEVEL_HIERARCHY else "N5"
    except Exception:
        return "N5"


def _normalize_clauses(sentence_text: str) -> List[str]:
    try:
        clauses = decompose_into_clauses_fallback(sentence_text)
    except Exception:
        clauses = []

    if not clauses:
        clauses = [sentence_text]

    clauses = clauses[:5]
    while len(clauses) < 5:
        clauses.append("")

    return clauses


def _clause_bounds_from_sentence(sentence_text: str, clauses: List[str]) -> List[tuple[int, int]]:
    bounds = []
    cursor = 0

    for clause in clauses:
        if not clause:
            bounds.append((cursor, cursor))
            continue

        idx = sentence_text.find(clause, cursor)
        if idx == -1:
            idx = cursor

        start = idx
        end = start + len(clause)
        bounds.append((start, end))
        cursor = end

    return bounds


def _kana_for_clause(clause_text: str, full_doc, start_bound: int, end_bound: int, nlp) -> str:
    if not clause_text:
        return ""

    kana_tokens = []
    for token in full_doc:
        token_start = token.idx
        token_end = token_start + len(token.text)
        if token_start >= start_bound and token_end <= end_bound:
            kana_tokens.append(_reading_or_surface(token))

    kana_reading = "".join(kana_tokens).strip() if kana_tokens else clause_text

    if kana_reading == clause_text and _utf8_len(clause_text) <= MAX_SUDACHI_BYTES and nlp is not None:
        try:
            fallback_doc = nlp(clause_text)
            fresh_tokens = [_reading_or_surface(t) for t in fallback_doc]
            fallback_reading = "".join(fresh_tokens).strip()
            if fallback_reading:
                kana_reading = fallback_reading
        except Exception:
            pass

    return kana_reading


def _sentence_furigana_from_doc(sentence_text: str, nlp) -> Optional[str]:
    if nlp is None or not sentence_text or _utf8_len(sentence_text) > MAX_SUDACHI_BYTES:
        return None

    try:
        doc = nlp(sentence_text)
        parts = [_reading_or_surface(t) for t in doc]
        return "".join(parts)
    except Exception:
        return None


def _dictionary_furigana_replace(text: str, furigana_dict: Dict[str, str]) -> str:
    if not text:
        return ""

    out = text
    for kanji in sorted(furigana_dict.keys(), key=len, reverse=True):
        reading = furigana_dict.get(kanji)
        if not reading:
            continue
        if kanji in out:
            out = out.replace(kanji, reading)
    return out


def _news_clause_furigana(clause_text: str, furigana_dict: Dict[str, str], nlp) -> str:
    if not clause_text:
        return ""

    by_doc = _sentence_furigana_from_doc(clause_text, nlp)
    if by_doc and by_doc != clause_text:
        return by_doc

    return _dictionary_furigana_replace(clause_text, furigana_dict)


def _clean_source_lines(raw_content: str) -> List[str]:
    lines = [line.strip() for line in raw_content.splitlines() if line.strip()]
    cleaned_lines = []

    skip_prefixes = [
        "Title:",
        "Author:",
        "Source URL:",
        "---",
        "RESTAURANT",
        "西洋料理店",
        "WILDCAT HOUSE",
        "山猫軒",
    ]

    for line in lines:
        if any(line.startswith(prefix) for prefix in skip_prefixes):
            continue
        cleaned_lines.append(line)

    return cleaned_lines


def _select_five_sentences_from_text(raw_content: str) -> List[str]:
    cleaned_lines = _clean_source_lines(raw_content)
    combined_raw_text = "\n".join(cleaned_lines)

    raw_sentences = [
        s.strip()
        for s in re.split(r"(?<=[。！？])", combined_raw_text)
        if s.strip()
    ]

    safe_sentences = []
    for s in raw_sentences:
        safe_sentences.extend(_chunk_text_for_sudachi(s))

    filtered_sentences = [s for s in safe_sentences if len(s) >= 8]

    #selected_sentences = filtered_sentences[:5]
    #while len(selected_sentences) < 5:
    #    selected_sentences.append("立派な一軒の西洋造りの家がありました。")

    selected_sentences = filtered_sentences[:5]
    if len(selected_sentences) < 5:
       raise ValueError(
           f"Only found {len(selected_sentences)} usable sentences; need 5."
       )
    return selected_sentences


def build_puzzle_json(raw_txt_path: str, target_level: str, output_dir: str) -> dict:
    nlp = _get_nlp()
    if nlp is None:
        return {}

    target_level = target_level.upper().strip()

    with open(raw_txt_path, "r", encoding="utf-8") as f:
        raw_content = f.read()

    #selected_sentences = _select_five_sentences_from_text(raw_content)
    try:
        selected_sentences = _select_five_sentences_from_text(raw_content)
    except ValueError as e:
        print(f"[ERR] {e}", file=sys.stderr)
        return {}

    highest_weight_encountered = 1
    puzzle_grid = []

    print("\n--- Processing Matrix Grid Chunks Incremental Loop ---")

    for row_idx, sentence_text in enumerate(selected_sentences):
        sentence_id = row_idx + 1

        if _utf8_len(sentence_text) > MAX_SUDACHI_BYTES:
            print(
                f" [SKIP] Row {sentence_id} still too long after chunking "
                f"({_utf8_len(sentence_text)} bytes), skipping."
            )
            continue

        try:
            full_sentence_doc = nlp(sentence_text)
        except Exception as e:
            print(f" [ERR] NLP failed on row {sentence_id}: {e}")
            continue

        detected_level = _safe_detect_level(full_sentence_doc)
        current_weight = LEVEL_HIERARCHY.get(detected_level, 1)
        if current_weight > highest_weight_encountered:
            highest_weight_encountered = current_weight

        clauses = _normalize_clauses(sentence_text)
        bounds = _clause_bounds_from_sentence(sentence_text, clauses)

        print(f" -> Line #{sentence_id} sliced into 5 game puzzle matrix columns.")

        for col_idx, clause_text in enumerate(clauses):
            start_bound, end_bound = bounds[col_idx]
            kana_reading = _kana_for_clause(
                clause_text, full_sentence_doc, start_bound, end_bound, nlp
            )

            clause_node = {
                "clause_id": (row_idx * 5) + col_idx + 1,
                "grid_coordinates": {
                    "row": row_idx + 1,
                    "column": col_idx + 1,
                },
                "parent_sentence_id": sentence_id,
                "clause_text": clause_text,
                "furigana": kana_reading,
                "sentence_individual_grammar_level": detected_level,
            }
            puzzle_grid.append(clause_node)

    game_payload = {
        "target_level_requested": target_level,
        "highest_grammar_level_encountered": REVERSE_HIERARCHY[highest_weight_encountered],
        "passage_extraction_strategy": "Incremental On-The-Fly Tokenization Slicing",
        "total_grid_clauses": len(puzzle_grid),
        "puzzle_solution_flow": {
            "description": "To solve, rebuild the story line by line from Row 1 to Row 5, joining Columns 1-5 in order.",
            "ordered_sentence_ids": [i + 1 for i in range(len(selected_sentences))],
        },
        "grid_matrix": puzzle_grid,
    }

    try:
        os.makedirs(output_dir, exist_ok=True)
        base_id = os.path.basename(raw_txt_path).replace(".txt", "")
        debug_output_path = os.path.join(output_dir, f"{base_id}_incremental_debug.json")
        with open(debug_output_path, "w", encoding="utf-8") as dbg_out:
            json.dump(game_payload, dbg_out, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Skipped saving debug artifact: {e}")

    return game_payload


def build_puzzle_from_news_tokens(
    five_sentences_list: list,
    furigana_dict: dict,
    target_level: str,
) -> dict:
    nlp = _get_nlp()
    target_level = target_level.upper().strip()
    puzzle_grid = []

    highest_weight_encountered = 1


    normalized_sentences = list(five_sentences_list[:5])
    if len(normalized_sentences) < 5:
      raise ValueError(
          f"Only received {len(normalized_sentences)} news sentences; need 5."
      )

    #normalized_sentences = list(five_sentences_list[:5])
    #while len(normalized_sentences) < 5:
    #    normalized_sentences.append("")

    for row_idx, sentence_text in enumerate(normalized_sentences):
        sentence_id = row_idx + 1

        print(f"\n[DEBUG] Processing Sentence {sentence_id}: {sentence_text[:50]}...")
        print(f"[DEBUG] GiNZa NLP loaded: {nlp is not None}")

        detected_level = "N5"
        if nlp and sentence_text and _utf8_len(sentence_text) <= MAX_SUDACHI_BYTES:
            try:
                doc = nlp(sentence_text)
                detected_level = _safe_detect_level(doc)
                print(f"[DEBUG] Detected grammar level: {detected_level}")
            except Exception as e:
                print(f"[WARN] NLP failed for sentence {sentence_id}: {e}")
        elif sentence_text and _utf8_len(sentence_text) > MAX_SUDACHI_BYTES:
            print(
                f"[WARN] Sentence {sentence_id} too long for Sudachi "
                f"({_utf8_len(sentence_text)} bytes), using N5 fallback."
            )

        current_weight = LEVEL_HIERARCHY.get(detected_level, 1)
        if current_weight > highest_weight_encountered:
            highest_weight_encountered = current_weight

        clauses = _normalize_clauses(sentence_text)

        for col_idx, clause_text in enumerate(clauses):
            clause_furigana = _news_clause_furigana(clause_text, furigana_dict or {}, nlp)

            clause_node = {
                "clause_id": (row_idx * 5) + col_idx + 1,
                "grid_coordinates": {
                    "row": row_idx + 1,
                    "column": col_idx + 1,
                },
                "parent_sentence_id": sentence_id,
                "clause_text": clause_text,
                "furigana": clause_furigana,
                "sentence_individual_grammar_level": detected_level,
            }
            puzzle_grid.append(clause_node)

    game_payload = {
        "target_level_requested": target_level,
        "highest_grammar_level_encountered": REVERSE_HIERARCHY[highest_weight_encountered],
        "passage_extraction_strategy": "Preserved Sequential News Matrix Layout",
        "total_grid_clauses": len(puzzle_grid),
        "puzzle_solution_flow": {
            "description": "To solve, rebuild the story line by line from Row 1 to Row 5, joining Columns 1-5 in order.",
            "ordered_sentence_ids": [1, 2, 3, 4, 5],
        },
        "grid_matrix": puzzle_grid,
    }

    return game_payload
