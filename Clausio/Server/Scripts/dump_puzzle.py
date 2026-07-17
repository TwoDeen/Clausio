import sys
import json
import argparse

def process_file(filename):
    """Reads a JSON file and prints the required fields using diff formatting."""
    print(f"@@ ================================================== @@")
    print(f"@@ Processing File: {filename} @@")
    print(f"@@ ================================================== @@")
    
    try:
        with open(filename, 'r', encoding='utf-8') as file:
            data = json.load(file)
    except FileNotFoundError:
        print(f" Error: The file '{filename}' was not found.")
        print()
        return
    except json.JSONDecodeError:
        print(f" Error: The file '{filename}' is not a valid JSON.")
        print()
        return
    except Exception as e:
        print(f" Error: An unexpected error occurred reading '{filename}': {e}")
        print()
        return

    sentence_translations = data.get("sentence_translations", [])
    grid_matrix = data.get("grid_matrix", [])

    if not sentence_translations:
        print(" No sentence translations found in this file.")
        print()
        return

    # Process and print the requested fields
    for sentence in sentence_translations:
        sentence_id = sentence.get("sentence_id")
        japanese = sentence.get("japanese")
        english = sentence.get("english_translation")

        # @@ triggers the chunk header color (usually blue/cyan)
        print(f"@@ Sentence {sentence_id} @@")
        
        # - triggers the "deleted" color (usually red)
        print(f"- {japanese}")
        
        # + triggers the "added" color (usually green)
        print(f"+ {english}")
        
        # A leading space keeps this the default color (white/grey)
        print("  Clauses:")

        # Find all clauses belonging to the current sentence_id
        # Sorting by clause_id ensures they are printed in the correct sequential order
        clauses = [
            item for item in grid_matrix 
            if item.get("parent_sentence_id") == sentence_id
        ]
        clauses.sort(key=lambda x: x.get("clause_id"))

        for clause in clauses:
            clause_text = clause.get("clause_text")
            # The '!' prefix triggers the "changed" color in .diff files (usually bright blue)
            print(f"!     {clause_text}")
        
        print()


def extract_corpus_paths(data):
    """Recursively finds all 'corpus_json_path' values in a nested JSON structure."""
    paths = []
    if isinstance(data, dict):
        for key, value in data.items():
            if key == "corpus_json_path" and isinstance(value, str):
                paths.append(value)
            else:
                paths.extend(extract_corpus_paths(value))
    elif isinstance(data, list):
        for item in data:
            paths.extend(extract_corpus_paths(item))
    return paths


def main():
    parser = argparse.ArgumentParser(description="Extract puzzle fields from JSON file(s).")
    parser.add_argument("filename", nargs="?", help="A specific JSON file to process.")
    parser.add_argument("--index", nargs="?", const="precomputed/corpus_index.json", 
                        help="Process all files listed in the specified index JSON (defaults to precomputed/corpus_index.json).")
    
    args = parser.parse_args()

    if args.index:
        index_file = args.index
        
        try:
            with open(index_file, 'r', encoding='utf-8') as f:
                index_data = json.load(f)
        except FileNotFoundError:
            print(f"Error: The index file '{index_file}' was not found.")
            sys.exit(1)
        except json.JSONDecodeError:
            print(f"Error: The index file '{index_file}' is not a valid JSON.")
            sys.exit(1)
            
        paths = extract_corpus_paths(index_data)
        
        if not paths:
            print("No 'corpus_json_path' entries found in the index.")
            sys.exit(0)
            
        for path in paths:
            process_file(path)
            
    elif args.filename:
        # Process the single file provided
        process_file(args.filename)
        
    else:
        # No arguments provided, show help
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()
