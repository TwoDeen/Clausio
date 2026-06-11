import sys
import os
import re

def expand_ditto_marks(text: str) -> str:
    """
    Finds traditional Japanese vertical and single-character repetition marks 
    (／＼, ／″＼, ゝ, and ゞ) and dynamically replaces them with the correct word.
    """
    
    # ----------------------------------------------------------------------
    # Pattern 1: Match the standard vertical repetition sign ／＼
    # ----------------------------------------------------------------------
    while "／＼" in text:
        match = re.search(r'([一-龠ぁ-んァ-ヶ々]+)／＼', text)
        if not match:
            match = re.search(r'(.{2})／＼', text)
            
        if match:
            original_word = match.group(1)
            text = text.replace(f"{original_word}／＼", f"{original_word}{original_word}", 1)
        else:
            text = text.replace("／＼", "", 1)

    # ----------------------------------------------------------------------
    # Pattern 2: Match the voiced vertical repetition sign ／″＼ or ／゛＼
    # ----------------------------------------------------------------------
    while "／″＼" in text or "／゛＼" in text:
        text = text.replace("／゛＼", "／″＼")
        
        match = re.search(r'([一-龠ぁ-んァ-ヶ々]+)／″＼', text)
        if not match:
            match = re.search(r'(.{2})／″＼', text)
            
        if match:
            original_word = match.group(1)
            repeated_part = original_word
            first_char = repeated_part[0]
            
            unvoiced_to_voiced = {
                'か': 'が', 'き': 'ぎ', 'く': 'ぐ', 'け': 'げ', 'こ': 'ご',
                'さ': 'ざ', 'し': 'じ', 'す': 'ず', 'せ': 'ぜ', 'そ': 'ぞ',
                'た': 'だ', 'ち': 'ぢ', 'つ': 'づ', 'て': 'で', 'と': 'ど',
                'は': 'ば', 'ひ': 'び', 'ふ': 'ぶ', 'へ': 'べ', 'ほ': 'ぼ',
                'カ': 'ガ', 'キ': 'ギ', 'ク': 'グ', 'ケ': 'ゲ', 'コ': 'ゴ',
                'サ': 'ザ', 'シ': 'ジ', 'ス': 'ズ', 'セ': 'ゼ', 'ソ': 'ゾ',
                'タ': 'ダ', 'チ': 'ヂ', 'ツ': 'ヅ', 'テ': 'デ', 'ト': 'ド',
                'ハ': 'バ', 'ひ': 'び', 'ふ': 'ぶ', 'へ': 'べ', 'ほ': 'ぼ'
            }
            
            if first_char in unvoiced_to_voiced:
                voiced_char = unvoiced_to_voiced[first_char]
                repeated_part = voiced_char + repeated_part[1:]
                
            text = text.replace(f"{original_word}／″＼", f"{original_word}{repeated_part}", 1)
        else:
            text = text.replace("／″＼", "", 1)

    # ----------------------------------------------------------------------
    # NEW Pattern 3: Match Hiragana Repetition Marks ゝ (Standard) and ゞ (Voiced)
    # ----------------------------------------------------------------------
    # A dictionary to transform the preceding character when encountering a voiced 'ゞ'
    hiragana_voicing = {
        'か': 'が', 'き': 'ぎ', 'く': 'ぐ', 'け': 'げ', 'こ': 'ご',
        'さ': 'ざ', 'し': 'じ', 'す': 'ず', 'せ': 'ぜ', 'そ': 'ぞ',
        'た': 'だ', 'ち': 'ぢ', 'つ': 'づ', 'て': 'で', 'と': 'ど',
        'は': 'ば', 'ひ': 'び', 'ふ': 'ぶ', 'へ': 'べ', 'ほ': 'ぼ'
    }

    # Clean up standard Hiragana repeat (ゝ)
    while "ゝ" in text:
        # Look for a single Hiragana character immediately to the left of 'ゝ'
        match = re.search(r'([ぁ-ん])ゝ', text)
        if match:
            target_char = match.group(1)
            # Replace 'ここゝ' -> 'こここ'
            text = text.replace(f"{target_char}ゝ", f"{target_char}{target_char}", 1)
        else:
            # Safe boundary check: pull any single character if regex misses it
            match_fallback = re.search(r'(.)ゝ', text)
            if match_fallback:
                target_char = match_fallback.group(1)
                text = text.replace(f"{target_char}ゝ", f"{target_char}{target_char}", 1)
            else:
                text = text.replace("ゝ", "", 1)

    # Clean up voiced Hiragana repeat (ゞ)
    while "ゞ" in text:
        match = re.search(r'([ぁ-ん])ゞ', text)
        if match:
            target_char = match.group(1)
            # If the character can be voiced (e.g., ひ -> び), do the transformation
            voiced_char = hiragana_voicing.get(target_char, target_char)
            text = text.replace(f"{target_char}ゞ", f"{target_char}{voiced_char}", 1)
        else:
            match_fallback = re.search(r'(.)ゞ', text)
            if match_fallback:
                target_char = match_fallback.group(1)
                voiced_char = hiragana_voicing.get(target_char, target_char)
                text = text.replace(f"{target_char}ゞ", f"{target_char}{voiced_char}", 1)
            else:
                text = text.replace("ゞ", "", 1)
            
    return text

def run_cleanup(input_filename: str):
    if not os.path.exists(input_filename):
        print(f"Error: The file '{input_filename}' does not exist.")
        return

    base_name, _ = os.path.splitext(input_filename)
    output_filename = f"{base_name}_ditto_cleaned.txt"

    print(f"Reading: {input_filename}...")
    with open(input_filename, "r", encoding="utf-8") as f:
        raw_text = f.read()

    print("Processing all repetition marks (／＼, ／″＼, ゝ, ゞ) and rebuilding words...")
    cleaned_text = expand_ditto_marks(raw_text)

    print(f"Saving cleaned copy out to: {output_filename}")
    with open(output_filename, "w", encoding="utf-8") as f:
        f.write(cleaned_text)
        
    print("Cleanup completely successful!")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python cleanup_ditto.py <your_story_file.txt>")
    else:
        target_file = sys.argv[1]
        run_cleanup(target_file)
