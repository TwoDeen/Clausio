import sys
import os
import json
import re

try:
    from clausify import decompose_into_clauses_fallback
    from complete_jlpt_analyzer import analyze_sentence_grammar
except ImportError as e:
    print(f"Error: Missing dependency script. {e}", file=sys.stderr)
    print("Please ensure 'clausify.py' and 'complete_jlpt_analyzer.py' are in this root folder.", file=sys.stderr)
    sys.exit(1)

# ─── Sudachi byte-limit guard ────────────────────────────────────────────────
MAX_SUDACHI_BYTES = 45_000


def _utf8_len(text: str) -> int:
    return len(text.encode("utf-8"))


def _chunk_text_for_sudachi(text: str, max_bytes: int = MAX_SUDACHI_BYTES) -> list:
    """Split text into chunks that are each safely under Sudachi's byte limit."""
    text = text.strip()
    if not text:
        return []
    if _utf8_len(text) <= max_bytes:
        return [text]

    # First try splitting on sentence-ending punctuation
    pieces = [p.strip() for p in re.split(r'(?<=[。！？])', text) if p.strip()]

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

    # Hard character-count fallback for any chunk still too large
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
            final_chunks.append(chunk[start:end])
            start = end

    return [c for c in final_chunks if c.strip()]
# ─────────────────────────────────────────────────────────────────────────────


def _katakana_to_hiragana(text: str) -> str:
    return "".join(
        chr(ord(char) - 0x60) if 0x30A1 <= ord(char) <= 0x30F6 else char
        for char in text
    )


def _extract_reading(token) -> str:
    """Try every available reading source on a GiNZa token; return '' on failure."""
    reading = ""

    if token.tag_ and "," in token.tag_:
        features = token.tag_.split(",")
        if len(features) >= 7 and features[6] != "*":
            reading = features[6]

    if not reading:
        if hasattr(token._, "reading") and token._.reading:
            reading = token._.reading
        elif hasattr(token._, "sudachi_morph") and token._.sudachi_morph:
            try:
                reading = token._.sudachi_morph.reading()
            except Exception:
                pass

    if not reading and token.morph and token.morph.get("Reading"):
        reading_list = token.morph.get("Reading")
        if reading_list:
            reading = reading_list[0]

    return reading


def _kana_for_clause(clause_text: str, full_doc, start_bound: int, end_bound: int, nlp) -> str:
    """
    Build a hiragana reading for clause_text using the pre-tokenised full_doc.
    Falls back to a fresh nlp() call on the clause if the full_doc yields no readings.
    """
    kana_tokens = []
    for token in full_doc:
        token_start = token.idx
        token_end = token_start + len(token.text)
        if token_start >= start_bound and token_end <= end_bound:
            reading = _extract_reading(token)
            kana_tokens.append(_katakana_to_hiragana(reading) if reading else token.text)

    kana_reading = "".join(kana_tokens) if kana_tokens else clause_text

    # Fallback: if reading == raw text, re-tokenise just the clause
    if kana_reading == clause_text and _utf8_len(clause_text) <= MAX_SUDACHI_BYTES:
        fallback_doc = nlp(clause_text)
        fresh_tokens = []
        for t in fallback_doc:
            r = _extract_reading(t)
            fresh_tokens.append(_katakana_to_hiragana(r) if r else t.text)
        kana_reading = "".join(fresh_tokens)

    return kana_reading


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC API
# ─────────────────────────────────────────────────────────────────────────────

def build_puzzle_json(raw_txt_path: str, target_level: str, output_dir: str) -> dict:
    import spacy

    config = {
        "components": {
            "compound_splitter": {
                "split_mode": "C",
            }
        }
    }

    try:
        nlp = spacy.load("ja_ginza", config=config)
    except Exception as nlp_err:
        print(f"Error loading GiNZa pipeline: {nlp_err}", file=sys.stderr)
        return {}

    target_level = target_level.upper().strip()

    # --- STEP 1: READ AND SEGMENT ---
    with open(raw_txt_path, "r", encoding="utf-8") as f:
        raw_content = f.read()

    lines = [line.strip() for line in raw_content.splitlines() if line.strip()]
    cleaned_lines = []
    for line in lines:
        if any(line.startswith(prefix) for prefix in [
            "Title:", "Author:", "Source URL:", "---",
            "RESTAURANT", "西洋料理店", "WILDCAT HOUSE", "山猫軒",
        ]):
            continue
        cleaned_lines.append(line)

    # Join with newline so paragraph breaks survive as natural split points
    combined_raw_text = "\n".join(cleaned_lines)

    raw_sentences = [
        s.strip()
        for s in re.split(r'(?<=[。！？])', combined_raw_text)
        if s.strip()
    ]

    # Apply Sudachi byte-limit chunking to every candidate sentence
    safe_sentences = []
    for s in raw_sentences:
        safe_sentences.extend(_chunk_text_for_sudachi(s))

    filtered_sentences = [s for s in safe_sentences if len(s) >= 8]

    selected_sentences = filtered_sentences[:5]
    while len(selected_sentences) < 5:
        selected_sentences.append("立派な一軒の西洋造りの家がありました。")

    level_hierarchy = {"N5": 1, "N4": 2, "N3": 3, "N2": 4, "N1": 5}
    reverse_hierarchy = {1: "N5", 2: "N4", 3: "N3", 4: "N2", 5: "N1"}
    highest_weight_encountered = 1

    puzzle_grid = []

    print("\n--- Processing Matrix Grid Chunks Incremental Loop ---")

    # --- STEP 2: LOOP AND DECOMPOSE INTO COLUMNS ---
    for row_idx, sentence_text in enumerate(selected_sentences):
        sentence_id = row_idx + 1

        # Hard guard — should never trigger after chunking, but keeps us safe
        if _utf8_len(sentence_text) > MAX_SUDACHI_BYTES:
            print(f" [SKIP] Row {sentence_id} still too long after chunking "
                  f"({_utf8_len(sentence_text)} bytes), skipping.")
            continue

        full_sentence_doc = nlp(sentence_text)

        detected_level, _ = analyze_sentence_grammar(full_sentence_doc)
        current_weight = level_hierarchy.get(detected_level, 1)
        if current_weight > highest_weight_encountered:
            highest_weight_encountered = current_weight

        clauses = decompose_into_clauses_fallback(sentence_text)
        clauses = clauses[:5]
        while len(clauses) < 5:
            clauses.append("")

        print(f" -> Line #{sentence_id} sliced into 5 game puzzle matrix columns.")

        current_char_offset = 0

        for col_idx, clause_text in enumerate(clauses):
            clause_len = len(clause_text)
            start_bound = current_char_offset
            end_bound = start_bound + clause_len

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
            current_char_offset += clause_len

    # --- STEP 3: ASSEMBLE PAYLOAD ---
    game_payload = {
        "target_level_requested": target_level,
        "highest_grammar_level_encountered": reverse_hierarchy[highest_weight_encountered],
        "passage_extraction_strategy": "Incremental On-The-Fly Tokenization Slicing",
        "total_grid_clauses": len(puzzle_grid),
        "puzzle_solution_flow": {
            "description": "To solve, rebuild the story line by line from Row 1 to Row 5, joining Columns 1-5 in order.",
            "ordered_sentence_ids": [i + 1 for i in range(len(selected_sentences))],
        },
        "grid_matrix": puzzle_grid,
    }

    try:
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
    import spacy

    config = {
        "components": {
            "compound_splitter": {
                "split_mode": "C",
            }
        }
    }

    try:
        nlp = spacy.load("ja_ginza", config=config)
    except Exception as e:
        print(f"Error loading GiNZa in news module: {e}", file=sys.stderr)
        nlp = None

    target_level = target_level.upper().strip()
    puzzle_grid = []

    level_hierarchy = {"N5": 1, "N4": 2, "N3": 3, "N2": 4, "N1": 5}
    reverse_hierarchy = {1: "N5", 2: "N4", 3: "N3", 4: "N2", 5: "N1"}
    highest_weight_encountered = 1

    for row_idx, sentence_text in enumerate(five_sentences_list):
        sentence_id = row_idx + 1

        print(f"\n[DEBUG] Processing Sentence {sentence_id}: {sentence_text[:50]}...")
        print(f"[DEBUG] GiNZa NLP loaded: {nlp is not None}")

        detected_level = "N5"
        if nlp:
            if _utf8_len(sentence_text) > MAX_SUDACHI_BYTES:
                print(f"[WARN] Sentence {sentence_id} too long for Sudachi "
                      f"({_utf8_len(sentence_text)} bytes), using N5 fallback.")
            else:
                doc = nlp(sentence_text)
                detected_level, _ = analyze_sentence_grammar(doc)
                print(f"[DEBUG] Detected grammar level: {detected_level}")

        current_weight = level_hierarchy.get(detected_level, 1)
        if current_weight > highest_weight_encountered:
            highest_weight_encountered = current_weight

        clauses = decompose_into_clauses_fallback(sentence_text)
        clauses = clauses[:5]
        while len(clauses) < 5:
            clauses.append("")

        for col_idx, clause_text in enumerate(clauses):
            clause_furigana = clause_text
            for kanji in sorted(furigana_dict.keys(), key=len, reverse=True):
                if kanji in clause_furigana:
                    clause_furigana = clause_furigana.replace(kanji, furigana_dict[kanji])

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
        "highest_grammar_level_encountered": reverse_hierarchy[highest_weight_encountered],
        "passage_extraction_strategy": "Preserved Sequential News Matrix Layout",
        "total_grid_clauses": len(puzzle_grid),
        "puzzle_solution_flow": {
            "description": "To solve, rebuild the story line by line from Row 1 to Row 5, joining Columns 1-5 in order.",
            "ordered_sentence_ids": [1, 2, 3, 4, 5],
        },
        "grid_matrix": puzzle_grid,
    }

    return game_payload
