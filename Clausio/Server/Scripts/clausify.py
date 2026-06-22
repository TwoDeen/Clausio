import sys
import spacy
import re

def split_longest_clause(clauses, nlp):
    longest_idx = max(range(len(clauses)), key=lambda i: len(clauses[i]))
    text_to_split = clauses[longest_idx]
    
    doc = nlp(text_to_split)
    best_split_idx = -1
    min_dist_to_mid = float('inf')
    mid_point = len(text_to_split) / 2
    
    for token in doc:
        if token.pos_ == "ADP" or "助詞" in token.tag_:
            split_idx = token.idx + len(token.text)
            
            # Ensure we don't split right before punctuation
            while split_idx < len(text_to_split) and text_to_split[split_idx] in "、。！？）」":
                split_idx += 1
            
            if split_idx < len(text_to_split):
                dist = abs(split_idx - mid_point)
                if dist < min_dist_to_mid:
                    min_dist_to_mid = dist
                    best_split_idx = split_idx
                    
    if best_split_idx != -1:
        part1 = text_to_split[:best_split_idx]
        part2 = text_to_split[best_split_idx:]
    else:
        mid = max(1, len(text_to_split) // 2)
        while mid < len(text_to_split) and text_to_split[mid] in "、。！？）」":
            mid += 1
            
        if mid >= len(text_to_split): 
            mid = max(1, len(text_to_split) // 2)
            
        part1 = text_to_split[:mid]
        part2 = text_to_split[mid:]
        
    clauses[longest_idx:longest_idx+1] = [part1, part2]
    return clauses

def merge_shortest_adjacent(clauses):
    min_len = float('inf')
    merge_idx = -1
    
    for i in range(len(clauses) - 1):
        combined_len = len(clauses[i]) + len(clauses[i+1])
        if combined_len < min_len:
            min_len = combined_len
            merge_idx = i
            
    clauses[merge_idx] = clauses[merge_idx] + clauses[merge_idx + 1]
    del clauses[merge_idx + 1]
    return clauses

def decompose_into_clauses_fallback(text):
    try:
        nlp = spacy.load("ja_ginza")
    except OSError:
        print("Error: GiNZA model not found. Please install it using: pip install ja-ginza", file=sys.stderr)
        return []

    # 🚀 THE FIX 1: Destroy all sneaky HTML whitespace that confuses the tokenizer
    text = re.sub(r'\s+', '', text)
    
    doc = nlp(text)
    initial_clauses = []
    
    # 🚀 THE FIX 2: Use native Japanese Bunsetsu blocks! 
    # This guarantees natural grammatical phrasing and zero orphaned particles.
    try:
        for span in doc._.bunsetsus:
            initial_clauses.append(span.text)
    except AttributeError:
        # Safety fallback if you are running an older version of GiNZA
        for token in doc:
            initial_clauses.append(token.text)

    if not initial_clauses:
        initial_clauses = [text]

    # Adjust the number of clauses to be exactly 5
    clauses = initial_clauses.copy()
    
    while len(clauses) > 5:
        clauses = merge_shortest_adjacent(clauses)
        
    while len(clauses) < 5:
        clauses = split_longest_clause(clauses, nlp)

    return clauses

if __name__ == "__main__":
    sample_text = "雨が降っていたので、傘を買って家に帰りました。"
    if len(sys.argv) > 1:
        sample_text = sys.argv[1]

    result_clauses = decompose_into_clauses_fallback(sample_text)
    
    print(f"Original Text: {sample_text}\n")
    print("--- Final 5 Clauses ---")
    for i, clause in enumerate(result_clauses, 1):
        print(f"{i}: {clause}")
