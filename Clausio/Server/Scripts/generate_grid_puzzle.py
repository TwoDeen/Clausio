import sys
import os
import json

# Cleanly import the required functions from your previous scripts
try:
    from export_consecutive_sentences import export_reading_passage
    from clausify import decompose_into_clauses_fallback
except ImportError as e:
    print(f"Error: Missing dependency script. {e}", file=sys.stderr)
    print("Please ensure 'export_consecutive_sentences.py' and 'clausify.py' are in this root folder.", file=sys.stderr)
    sys.exit(1)

def build_puzzle_json(tagged_json_path: str, target_level: str):
    """
    1. Extracts the optimal 5-sentence passage for the requested level.
    2. Decomposes those 5 sentences into exactly 25 clauses (5 each).
    3. Generates a master 5x5 grid puzzle configuration JSON file with accurate readings.
    """
    # 1. Initialize Spacy NLP locally inside the function scope
    import spacy
    
    # 🔑 Safe initialization config: Overrides the broken 'None' parameter to prevent crashes 
    # natively on modern versions of spaCy (>=3.8.x) and ja-ginza (>=5.2.x)
    config = {
        "components": {
            "compound_splitter": {
                "split_mode": "C"
            }
        }
    }
    
    try:
        nlp = spacy.load("ja_ginza", config=config)
    except Exception as nlp_err:
        print(f"Error loading GiNZa pipeline config layer: {nlp_err}", file=sys.stderr)
        return
    
    target_level = target_level.upper().strip()
    
    # --- STEP 1: Extract the 5-sentence passage via export_consecutive_sentences ---
    print(f"--- Step 1: Extracting 5-sentence passage for level {target_level} ---")
    export_reading_passage(tagged_json_path, target_level, window_size=5)
    
    # Formulate the passage filename that export_consecutive_sentences generated
    just_the_filename = os.path.basename(tagged_json_path).replace(".json", "")
    passage_filename = f"{just_the_filename}_{target_level}_passage.json"
    
    if not os.path.exists(passage_filename):
        print(f"Error: Expected passage file '{passage_filename}' was not generated.", file=sys.stderr)
        return

    # --- STEP 2: Load the extracted 5-sentence passage data ---
    with open(passage_filename, "r", encoding="utf-8") as f:
        passage_data = json.load(f)

    sentences = passage_data.get("reading_passage", [])
    output_filename = f"{just_the_filename}_5x5_puzzle.json"

    puzzle_grid = []
    all_extracted_clauses = []

    print(f"\n--- Step 2: Decomposing sentences into 5x5 Matrix Grid Chunks ---")

    # --- STEP 3: Map sentences to rows and decompose them into columns ---
    for row_idx, sentence_entry in enumerate(sentences):
        sentence_text = sentence_entry["text"]
        sentence_id = sentence_entry["sentence_id"]
        grammar_level = sentence_entry["grammar_jlpt_level"]

        # Run NLP tokenization on the WHOLE unbroken sentence to guarantee full context readings
        full_sentence_doc = nlp(sentence_text)

        # Call the clausify.py script to get exactly 5 clause strings back
        clauses = decompose_into_clauses_fallback(sentence_text)
        print(f"  -> Line #{sentence_id} ({grammar_level}) sliced cleanly into 5 game clauses.")

        # Track character indexing offset over the full sentence to extract readings cleanly
        current_char_offset = 0

        # Allocate 25-element matrix grid layout positioning coordinates
        for col_idx, clause_text in enumerate(clauses):
            clause_len = len(clause_text)
            start_bound = current_char_offset
            end_bound = start_bound + clause_len
            
            kana_tokens = []
            
            # Map tokens belonging to this specific clause slice position
            for token in full_sentence_doc:
                # Find if the token falls within the character coordinates of the current clause slice
                token_start = token.idx
                token_end = token_start + len(token.text)
                
                if token_start >= start_bound and token_end <= end_bound:
                    reading = ""
                    
                    # 1. Parse cross-version spaCy tag/feature list strings (Comma separation fallback)
                    if token.tag_:
                        if ',' in token.tag_:
                            features = token.tag_.split(',')
                            if len(features) >= 7 and features[6] != '*':
                                reading = features[6]
                    
                    # 2. Directly query internal custom extension attributes if feature tags are dash-split
                    if not reading:
                        if hasattr(token._, 'reading') and token._.reading:
                            reading = token._.reading
                        elif hasattr(token._, 'sudachi_morph') and token._.sudachi_morph:
                            # Safely fallback to reading extraction hooks on the underlying morpheme data
                            try:
                                reading = token._.sudachi_morph.reading()
                            except Exception:
                                pass
                                
                    # 3. Third line of defense: Check spaCy morphological features dictionary mapping
                    if not reading and token.morph and token.morph.get("Reading"):
                        reading_list = token.morph.get("Reading")
                        if reading_list:
                            reading = reading_list[0]
                    
                    # 4. Convert Katakana reading output to native Hiragana for UI rendering
                    if reading:
                        hiragana_reading = "".join([
                            chr(ord(char) - 0x60) if 0x30A1 <= ord(char) <= 0x30F6 else char 
                            for char in reading
                        ])
                        kana_tokens.append(hiragana_reading)
                    else:
                        # Revert back to literal characters if no definition was processed
                        kana_tokens.append(token.text)
            
            # Assemble our extracted characters 
            kana_reading = "".join(kana_tokens) if kana_tokens else clause_text
            
            # Integrity check: If the calculated furigana completely mirrors the kanji string, 
            # execute a target search context directly on the isolated clause string fragment
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
            
            # Increment character sequence tracking boundary
            current_char_offset += clause_len
            
    # --- STEP 4: Build the Unified UI Game Engine Payload ---
    game_payload = {
        "target_level_requested": target_level,
        "passage_extraction_strategy": passage_data.get("passage_extraction_strategy"),
        "total_grid_clauses": len(puzzle_grid),
        "puzzle_solution_flow": {
            "description": "To solve, rebuild the story line by line from Row 1 to Row 5, joining Columns 1-5 in order.",
            "ordered_sentence_ids": [s["sentence_id"] for s in sentences]
        },
        "grid_matrix": puzzle_grid
    }

    # --- STEP 5: Integrity Verification Check ---
    original_combined_text = "".join([s["text"] for s in sentences])
    reconstructed_combined_text = "".join(all_extracted_clauses)
    integrity_match = original_combined_text == reconstructed_combined_text

    print(f"\n--- Step 3: Verifying Matrix Integrity ---")
    print(f"Sentence-to-Clause Continuity Match: {integrity_match}")

    if not integrity_match:
        print("Warning: Reconstructed clause text string mismatch detected!", file=sys.stderr)

    # Save directly to the current working root folder
    print(f"Exporting game puzzle matrix file out to: {output_filename}")
    with open(output_filename, "w", encoding="utf-8") as json_out:
        json.dump(game_payload, json_out, ensure_ascii=False, indent=4)
        
    # Clean-up intermediate file to keep root folder immaculate
    if os.path.exists(passage_filename):
        os.remove(passage_filename)

    print(f"\nMaster 5x5 Grid Puzzle configuration initialized successfully!")
    
if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python generate_grid_puzzle.py <tagged_json_file.json> <JLPT_LEVEL>")
        print("Example: python generate_grid_puzzle.py selected_ditto_cleaned_sentences_comprehensive_tagged.json N4")
    else:
        tagged_file_arg = sys.argv[1]
        level_arg = sys.argv[2]
        build_puzzle_json(tagged_file_arg, level_arg)
