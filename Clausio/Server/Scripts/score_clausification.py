import pandas as pd
import numpy as np

# Define input and output file names
input_file = "sentence-clauses.txt"
output_file = "sentence_split_scores.csv"

results = []

# Particles and punctuation that usually indicate a natural grammatical break in Japanese
good_endings = ('は', 'が', 'を', 'に', 'へ', 'と', 'から', 'より', 'で', 'や', 'の', 'て', '。', '、', '？', '！', 'ね', 'よ', 'か', 'し', 'ば', 'たら', 'なら', 'けど', 'つつ', 'ながら', 'だ', 'です', 'ます', 'た', 'ない', 'ず', 'ぬ', 'る')

# Open and read the text file line by line
with open(input_file, 'r', encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if not line or ':' not in line:
            continue
            
        sentence, splits = line.split(':', 1)
        clauses = splits.split('/')
        
        # Ensure we have exactly 5 clauses (pad with empty strings if there are fewer, truncate if more)
        clauses_padded = clauses + [''] * (5 - len(clauses))
        clauses_padded = clauses_padded[:5]
        
        # Metric 1: Length balance score (0 to 50)
        # The smaller the standard deviation of lengths, the higher the score.
        lengths = [len(c) for c in clauses if c]
        if lengths:
            mean_len = np.mean(lengths)
            std_len = np.std(lengths)
            length_score = max(0, 50 - (std_len / (mean_len + 1e-5)) * 50)
        else:
            length_score = 0
            
        # Metric 2: Boundary / chunking quality (0 to 50)
        boundary_score = 0
        if len(clauses) > 1:
            good_boundaries = 0
            # Ignore the last segment since it just ends the sentence naturally
            for c in clauses[:-1]:
                c_stripped = c.strip()
                if any(c_stripped.endswith(ending) for ending in good_endings):
                    good_boundaries += 1
            boundary_score = (good_boundaries / (len(clauses) - 1)) * 50
        else:
            boundary_score = 50

        total_score = round(length_score + boundary_score, 2)
        
        # Append the row dictionary
        results.append({
            'Sentence': sentence,
            'Clause_1': clauses_padded[0],
            'Clause_2': clauses_padded[1],
            'Clause_3': clauses_padded[2],
            'Clause_4': clauses_padded[3],
            'Clause_5': clauses_padded[4],
            'Length_Score': round(length_score, 2),
            'Boundary_Score': round(boundary_score, 2),
            'Total_Score': total_score
        })

# Convert the results to a pandas DataFrame
df = pd.DataFrame(results)

# Save the DataFrame to a CSV file (using utf-8-sig to ensure Excel reads Japanese characters correctly)
df.to_csv(output_file, index=False, encoding='utf-8-sig')

print(f"Processed {len(df)} sentences and saved to {output_file}.")
