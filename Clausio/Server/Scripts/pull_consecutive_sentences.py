import sys
import os
import json

def fetch_reading_passage(json_path: str, target_level: str, window_size: int = 5):
    """
    Searches the tagged JSON dataset for a reading block of consecutive sentences.
    Prioritizes an unbroken streak of the target level. 
    Falls back to a dense contextual window if an unbroken streak doesn't exist.
    """
    if not os.path.exists(json_path):
        print(f"Error: The file '{json_path}' does not exist.")
        return

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    total_sentences = len(data)
    target_level = target_level.upper().strip()

    # --- STRATEGY 1: Search for an unbroken, consecutive streak ---
    for i in range(total_sentences - window_size + 1):
        window = data[i : i + window_size]
        # Check if every single sentence in this 5-sentence block matches the level
        if all(item["assigned_jlpt"] == target_level for item in window):
            print(f"==> Found an UNBROKEN streak of {window_size} consecutive {target_level} sentences!\n")
            print_passage(window)
            return

    # --- STRATEGY 2: Fallback to a smart contextual window ---
    print(f"Note: An unbroken streak of {window_size} consecutive {target_level} sentences wasn't found.")
    print(f"Scanning for the densest contextual reading window containing {target_level}...\n")

    best_start_idx = -1
    max_target_count = 0

    # Slide a 5-sentence window across the text to find where the target level clusters closest together
    for i in range(total_sentences - window_size + 1):
        window = data[i : i + window_size]
        target_count = sum(1 for item in window if item["assigned_jlpt"] == target_level)
        
        if target_count > max_target_count:
            max_target_count = target_count
            best_start_idx = i

    # If the level exists anywhere in the file, pull its surrounding window
    if best_start_idx != -1:
        best_window = data[best_start_idx : best_start_idx + window_size]
        print(f"==> Displaying a {window_size}-sentence context block (Contains {max_target_count} target {target_level} tokens):\n")
        print_passage(best_window)
    else:
        print(f"Error: No sentences matching level '{target_level}' exist in this dataset.")

def print_passage(window_data):
    """Prints out the reading block cleanly with ID and grammar metadata."""
    print("=" * 60)
    for item in window_data:
        print(f"[{item['assigned_jlpt']}] Line #{item['sentence_id']}: {item['raw_text']}")
        print(f"      ↳ Grammar Target: {item['detected_grammar_rule']}\n")
    print("=" * 60)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python pull_consecutive_sentences.py <tagged_json_file.json> <JLPT_LEVEL>")
        print("Example: python pull_consecutive_sentences.py miyazawa_kenji_stories/selected_ditto_cleaned_sentences_comprehensive_tagged.json N4")
    else:
        json_file = sys.argv[1]
        level_arg = sys.argv[2]
        fetch_reading_passage(json_file, level_arg)
