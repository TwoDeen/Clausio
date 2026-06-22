import sys
import os
import json
import re

try:
    from clausify import decompose_into_clauses_fallback
except ImportError as e:
    print(f"Error: Missing dependency script. {e}", file=sys.stderr)
    print("Please ensure 'clausify.py' are in this root folder.", file=sys.stderr)
    sys.exit(1)

# 🔑 Injected output_dir target parameter to route file saving routines
def build_puzzle_json(raw_txt_path: str, target_level: str, output_dir: str) -> dict:
    """
    1. Reads a raw untagged .txt file.
    2. Tokenizes it into logical sentences.
    3. Decomposes sentences into exactly 25 clauses (5 each).
    4. Generates and returns a master 5x5 grid puzzle configuration dictionary.
    """
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
        print(f"Error loading GiNZa pipeline layout: {nlp_err}", file=sys.stderr)
        return {}
        
    target_level = target_level.upper().strip()

    # --- STEP 1: READ AND SEGMENT THE RAW TEXT ---
    with open(raw_txt_path, "r", encoding="utf-8") as f:
        raw_content = f.read()

    lines = [line.strip() for line in raw_content.splitlines() if line.strip()]
    cleaned_lines = []
    for line in lines:
        if any(line.startswith(prefix) for prefix in ["Title:", "Author:", "Source URL:", "---", "RESTAURANT", "西洋料理店", "WILDCAT HOUSE", "山猫軒"]):
            continue
        cleaned_lines.append(line)
    
    combined_raw_text = "".join(cleaned_lines)
    
    raw_sentences = [s + "」" if s.endswith("」") == False and s.count("「") > s.count("」") else s 
                     for s in re.split(r'(?<=。) | (?<=！)|(?<=？)|(?<=。)', combined_raw_text) if s.strip()]
    
    filtered_sentences = [s for s in raw_sentences if len(s) >= 8]

    selected_sentences = filtered_sentences[:5]
    if len(selected_sentences) < 5:
        while len(selected_sentences) < 5:
            selected_sentences.append("立派な一軒の西洋造りの家がありました。")

    puzzle_grid = []
    all_extracted_clauses = []

    print(f"\n--- Processing Matrix Grid Chunks Incremental Loop ---")

    # --- STEP 2: LOOP AND DECOMPOSE INTO COLUMNS ---
    for row_idx, sentence_text in enumerate(selected_sentences):
        sentence_id = row_idx + 1
        full_sentence_doc = nlp(sentence_text)

        clauses = decompose_into_clauses_fallback(sentence_text)
        print(f"  -> Line #{sentence_id} sliced into 5 game puzzle matrix columns.")

        current_char_offset = 0

        for col_idx, clause_text in enumerate(clauses):
            clause_len = len(clause_text)
            start_bound = current_char_offset
            end_bound = start_bound + clause_len
            
            kana_tokens = []
            
            for token in full_sentence_doc:
                token_start = token.idx
                token_end = token_start + len(token.text)
                
                if token_start >= start_bound and token_end <= end_bound:
                    reading = ""
                    
                    if token.tag_ and ',' in token.tag_:
                        features = token.tag_.split(',')
                        if len(features) >= 7 and features[6] != '*':
                            reading = features[6]
                    
                    if not reading:
                        if hasattr(token._, 'reading') and token._.reading:
                            reading = token._.reading
                        elif hasattr(token._, 'sudachi_morph') and token._.sudachi_morph:
                            try:
                                reading = token._.sudachi_morph.reading()
                            except Exception:
                                pass
                                
                    if not reading and token.morph and token.morph.get("Reading"):
                        reading_list = token.morph.get("Reading")
                        if reading_list:
                            reading = reading_list[0]
                    
                    if reading:
                        hiragana_reading = "".join([
                            chr(ord(char) - 0x60) if 0x30A1 <= ord(char) <= 0x30F6 else char 
                            for char in reading
                        ])
                        kana_tokens.append(hiragana_reading)
                    else:
                        kana_tokens.append(token.text)
            
            kana_reading = "".join(kana_tokens) if kana_tokens else clause_text
            
            if kana_reading == clause_text:
                fallback_doc = nlp(clause_text)
                fresh_tokens = []
                for t in fallback_doc:
                    feat = t.tag_.split(',') if (t.tag_ and ',' in t.tag_) else []
                    r = feat[6] if len(feat) >= 7 and feat[6] != '*' else ""
                    if not r and t.morph and t.morph.get("Reading"):
                        r = t.morph.get("Reading")[0]
                    
                    if r:
                        h = "".join([chr(ord(c) - 0x60) if 0x30A1 <= ord(c) <= 0x30F6 else c for c in r])
                        fresh_tokens.append(h)
                    else:
                        fresh_tokens.append(t.text)
                kana_reading = "".join(fresh_tokens)

            clause_node = {
                "clause_id": (row_idx * 5) + col_idx + 1,
                "grid_coordinates": {
                    "row": row_idx + 1,
                    "column": col_idx + 1
                },
                "parent_sentence_id": sentence_id,
                "clause_text": clause_text,
                "furigana": kana_reading
            }
            puzzle_grid.append(clause_node)
            all_extracted_clauses.append(clause_text)
            current_char_offset += clause_len
            
    # --- STEP 3: ASSEMBLE GAME UNIFIED PAYLOAD ---
    game_payload = {
        "target_level_requested": target_level,
        "passage_extraction_strategy": "Incremental On-The-Fly Tokenization Slicing",
        "total_grid_clauses": len(puzzle_grid),
        "puzzle_solution_flow": {
            "description": "To solve, rebuild the story line by line from Row 1 to Row 5, joining Columns 1-5 in order.",
            "ordered_sentence_ids": [i + 1 for i in range(len(selected_sentences))]
        },
        "grid_matrix": puzzle_grid
    }

    # Optional: If you want to dump copies of the intermediate json maps, 
    # force them to save inside the temporary directory too!
    try:
        base_id = os.path.basename(raw_txt_path).replace(".txt", "")
        debug_output_path = os.path.join(output_dir, f"{base_id}_incremental_debug.json")
        with open(debug_output_path, "w", encoding="utf-8") as dbg_out:
            json.dump(game_payload, dbg_out, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Skipped saving secondary temporary artifact: {e}")

    return game_payload

from clausify import decompose_into_clauses_fallback 

def build_puzzle_from_news_tokens(five_sentences_list: list, furigana_dict: dict, target_level: str) -> dict:
    target_level = target_level.upper().strip()
    puzzle_grid = []
    
    for row_idx, sentence_text in enumerate(five_sentences_list):
        sentence_id = row_idx + 1
        
        # 1. Let GiNZa slice the purely clean text into 5 logical blocks!
        clauses = decompose_into_clauses_fallback(sentence_text)
        
        # 2. Build the grid nodes
        for col_idx, clause_text in enumerate(clauses):
            
            clause_furigana = clause_text
            
            # 3. Dynamically inject the correct Furigana over any matching Kanji
            # (Sorted by length so compound words replace before single characters)
            for kanji in sorted(furigana_dict.keys(), key=len, reverse=True):
                if kanji in clause_furigana:
                    clause_furigana = clause_furigana.replace(kanji, furigana_dict[kanji])
            
            clause_node = {
                "clause_id": (row_idx * 5) + col_idx + 1,
                "grid_coordinates": {
                    "row": row_idx + 1,
                    "column": col_idx + 1
                },
                "parent_sentence_id": sentence_id,
                "clause_text": clause_text,
                "furigana": clause_furigana
            }
            puzzle_grid.append(clause_node)
            
    game_payload = {
        "target_level_requested": target_level,
        "passage_extraction_strategy": "Preserved Sequential News Matrix Layout",
        "total_grid_clauses": len(puzzle_grid),
        "puzzle_solution_flow": {
            "description": "To solve, rebuild the story line by line from Row 1 to Row 5, joining Columns 1-5 in order.",
            "ordered_sentence_ids": [1, 2, 3, 4, 5]
        },
        "grid_matrix": puzzle_grid
    }
    
    return game_payload
