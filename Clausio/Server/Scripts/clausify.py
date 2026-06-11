import sys
import spacy

def split_longest_clause(clauses, nlp):
    # Find the index of the longest clause
    longest_idx = max(range(len(clauses)), key=lambda i: len(clauses[i]))
    text_to_split = clauses[longest_idx]
    
    # Parse the longest clause to find particles
    doc = nlp(text_to_split)
    best_split_idx = -1
    min_dist_to_mid = float('inf')
    mid_point = len(text_to_split) / 2
    
    for token in doc:
        # Check if the token is a particle (ADP or tagged as 助詞)
        if token.pos_ == "ADP" or "助詞" in token.tag_:
            split_idx = token.idx + len(token.text)
            
            # Ensure we don't split at the very end of the string
            if split_idx < len(text_to_split):
                dist = abs(split_idx - mid_point)
                # Favor the particle closest to the middle for a balanced split
                if dist < min_dist_to_mid:
                    min_dist_to_mid = dist
                    best_split_idx = split_idx
                    
    if best_split_idx != -1:
        part1 = text_to_split[:best_split_idx]
        part2 = text_to_split[best_split_idx:]
    else:
        # Fallback: if no particle is found, split exactly in half
        mid = max(1, len(text_to_split) // 2)
        part1 = text_to_split[:mid]
        part2 = text_to_split[mid:]
        
    # Replace the longest clause with its two halves
    clauses[longest_idx:longest_idx+1] = [part1, part2]
    return clauses

def merge_shortest_adjacent(clauses):
    min_len = float('inf')
    merge_idx = -1
    
    # Find the shortest adjacent pair
    for i in range(len(clauses) - 1):
        combined_len = len(clauses[i]) + len(clauses[i+1])
        if combined_len < min_len:
            min_len = combined_len
            merge_idx = i
            
    # Merge them together
    clauses[merge_idx] = clauses[merge_idx] + clauses[merge_idx + 1]
    # Remove the second part of the merged pair
    del clauses[merge_idx + 1]
    return clauses

def decompose_into_clauses_fallback(text):
    try:
        nlp = spacy.load("ja_ginza")
    except OSError:
        print(
            "Error: GiNZA model not found. Please install it using: pip install ja-ginza",
            file=sys.stderr,
        )
        return []

    doc = nlp(text)
    
    # 1. Collect the character end-points of each structural clause
    end_indices = set()
    for sent in doc.sents:
        for token in sent:
            if token.dep_ in ("ROOT", "advcl", "acl"):
                if token.pos_ in ("VERB", "ADJ", "AUX", "NOUN", "PRON"):
                    clause_tokens = sorted(list(token.subtree), key=lambda x: x.i)
                    last_token = clause_tokens[-1]
                    # Calculate the exact character offset where this clause ends
                    end_idx = last_token.idx + len(last_token.text)
                    end_indices.add(end_idx)

    # Always ensure the absolute end of the text is included
    end_indices.add(len(text))
    
    # 2. Slice the original string using the sorted boundaries
    sorted_indices = sorted(list(end_indices))
    initial_clauses = []
    start = 0
    for end in sorted_indices:
        if end > start:
            initial_clauses.append(text[start:end])
            start = end

    # Fallback if text is entirely empty or fails
    if not initial_clauses:
        initial_clauses = [text]

    # 3. Adjust the number of clauses to be exactly 5
    clauses = initial_clauses.copy()
    
    while len(clauses) > 5:
        clauses = merge_shortest_adjacent(clauses)
        
    while len(clauses) < 5:
        clauses = split_longest_clause(clauses, nlp)

    # UPDATED: Return the list of 5 clauses instead of printing them out to stdout, 
    # making it importable into our master puzzle generation grid script!
    return clauses

if __name__ == "__main__":
    # Keeps your standalone execution logic completely intact for quick testing
    sample_text = "雨が降っていたので、傘を買って家に帰りました。"

    if len(sys.argv) > 1:
        sample_text = sys.argv[1]

    result_clauses = decompose_into_clauses_fallback(sample_text)
    
    print(f"Original Text: {sample_text}\n")
    print("--- Final 5 Clauses ---")
    for i, clause in enumerate(result_clauses, 1):
        print(f"{i}: {clause}")

    final_string = "".join(result_clauses)
    print(f"\n--- Verification ---")
    print(f"Match: {final_string == sample_text}")
