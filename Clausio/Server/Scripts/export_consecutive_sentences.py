import sys
import os
import json

def export_reading_passage(json_path: str, target_level: str, window_size: int = 5):
    """
    Searches the tagged JSON dataset for a 5-sentence reading block.
    Saves the targeted reading passage to a clean output JSON file in the root directory.
    """
    if not os.path.exists(json_path):
        print(f"Error: The file '{json_path}' does not exist.")
        return

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    total_sentences = len(data)
    target_level = target_level.upper().strip()
    
    # Strips out directory path prefixes to force the output file 
    # to save directly inside your current active root folder.
    just_the_filename = os.path.basename(json_path).replace(".json", "")
    output_filename = f"{just_the_filename}_{target_level}_passage.json"

    passage_window = []
    selection_type = ""

    # --- STRATEGY 1: Search for an unbroken, consecutive streak ---
    for i in range(total_sentences - window_size + 1):
        window = data[i : i + window_size]
        if all(item["assigned_jlpt"] == target_level for item in window):
            passage_window = window
            selection_type = f"UNBROKEN_STREAK_OF_{target_level}"
            print(f"==> Success: Found an unbroken streak of {target_level} sentences!")
            break

    # --- STRATEGY 2: Fallback to a smart contextual window ---
    if not passage_window:
        print(f"Note: Unbroken streak of {target_level} not found. Executing contextual fallback...")
        best_start_idx = -1
        max_target_count = 0

        for i in range(total_sentences - window_size + 1):
            window = data[i : i + window_size]
            target_count = sum(1 for item in window if item["assigned_jlpt"] == target_level)
            
            if target_count > max_target_count:
                max_target_count = target_count
                best_start_idx = i

        if best_start_idx != -1:
            passage_window = data[best_start_idx : best_start_idx + window_size]
            selection_type = f"CONTEXT_WINDOW_FOR_{target_level}"
            print(f"==> Success: Gathered dense context block containing {max_target_count} '{target_level}' markers.")
        else:
            print(f"Error: No sentences matching level '{target_level}' exist in this dataset.")
            return

    # --- BUILD THE STRUCTURED JSON PAYLOAD ---
    output_payload = {
        "target_level_requested": target_level,
        "passage_extraction_strategy": selection_type,
        "total_sentences_included": len(passage_window),
        "reading_passage": []
    }

    # Clean up fields for the final curriculum output export
    for item in passage_window:
        # RENAMED KEY: Changed from 'jlpt_level' to 'grammar_jlpt_level'
        sentence_entry = {
            "sentence_id": item.get("sentence_id") or item.get("id"),
            "grammar_jlpt_level": item["assigned_jlpt"] if "assigned_jlpt" in item else item["jlpt_level"],
            "grammar_target": item.get("detected_grammar_rule") or item.get("detected_grammar"),
            "text": item.get("raw_text") or item.get("text")
        }
        output_payload["reading_passage"].append(sentence_entry)

    # --- WRITE OUT DIRECTLY TO A FILE ---
    print(f"Writing selected passage payload cleanly to: {output_filename}")
    with open(output_filename, "w", encoding="utf-8") as json_out:
        json.dump(output_payload, json_out, ensure_ascii=False, indent=4)
        
    print("Export completely successful!")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python export_consecutive_sentences.py <tagged_json_file.json> <JLPT_LEVEL>")
    else:
        json_file = sys.argv[1]
        level_arg = sys.argv[2]
        export_reading_passage(json_file, level_arg)
