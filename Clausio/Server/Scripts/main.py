import sys
import os
import json
import subprocess
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Clausio Engine", 
    description="Dynamic 5x5 Japanese structural clause grid puzzle compiler from pre-fetched local assets."
)

# Enable iOS App connectivity across local network boundaries
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_target_story_path() -> str:
    """Reads story_name.txt to identify the pre-fetched local text file."""
    meta_file = "story_name.txt"
    if not os.path.exists(meta_file):
        raise HTTPException(status_code=500, detail=f"Meta configuration '{meta_file}' missing.")
    
    with open(meta_file, "r", encoding="utf-8") as f:
        content = f.read().strip()
        
    # Cleans up file pointer signatures if embedded
    if "" in content:
        content = content.replace("", "").strip()
        
    if not content:
        raise HTTPException(status_code=500, detail="Meta configuration file is empty.")
    return content

@app.post("/api/puzzle/generate/\u007bjlpt_level\u007d")
def generate_live_puzzle(jlpt_level: str):
    level = jlpt_level.upper().strip()
    if level not in ["N1", "N2", "N3", "N4", "N5"]:
        raise HTTPException(status_code=400, detail="Invalid target JLPT level parameter requested.")

    try:
        raw_story_path = get_target_story_path()
        if not os.path.exists(raw_story_path):
            raise HTTPException(status_code=404, detail=f"Pre-fetched file '{raw_story_path}' not found locally.")

        base_dir = os.path.dirname(raw_story_path)
        filename_raw = os.path.basename(raw_story_path)
        name_no_ext = os.path.splitext(filename_raw)[0]

        # --- PRECISE FILENAME COUPLING MATCHING ---
        # 1. Output from cleanup_ditto.py (Appends '_ditto_cleaned.txt')
        cleaned_file = os.path.join(base_dir, f"{name_no_ext}_ditto_cleaned.txt")
        
        # 2. Output from tokenise_into_sentences.py (Appends '_sentences.txt' to its input file base)
        sentences_file = os.path.join(base_dir, f"{name_no_ext}_ditto_cleaned_sentences.txt")
        
        # 3. Output from complete_jlpt_analyzer.py (Appends '_comprehensive_tagged.json' to its input file base)
        tagged_json = os.path.join(base_dir, f"{name_no_ext}_ditto_cleaned_sentences_comprehensive_tagged.json")

        print(f"Executing step-by-step pipeline on pre-fetched asset: \u007braw_story_path\u007d...")

        # Step 1: Expand traditional vertical/horizontal repetition marks
        subprocess.run(["python3", "cleanup_ditto.py", str(raw_story_path)], check=True)
        
        # Step 2: Stitch lines into clean structural sentences
        subprocess.run(["python3", "tokenise_into_sentences.py", cleaned_file], check=True)
        
        # Step 3: Run NLP analytical processing using GiNZa
        subprocess.run(["python3", "complete_jlpt_analyzer.py", sentences_file], check=True)
        
        # Step 4: Extract the passage and build the 5x5 matrix
        subprocess.run([sys.executable, "generate_grid_puzzle.py", tagged_json, level], check=True)

        # --- UPDATED: Added '_comprehensive_tagged' to match exact script behavior ---
        output_filename = f"{name_no_ext}_ditto_cleaned_sentences_comprehensive_tagged_5x5_puzzle.json"
        
        if not os.path.exists(output_filename):
            raise HTTPException(status_code=500, detail="Matrix puzzle building task terminated unexpectedly.")

        with open(output_filename, "r", encoding="utf-8") as out_f:
            payload_data = json.load(out_f)

        return payload_data
        
        # Step 5: Read the final generated grid config file output (generate_grid_puzzle saves to your active working directory)
        output_filename = f"{name_no_ext}_ditto_cleaned_sentences_5x5_puzzle.json"
        
        if not os.path.exists(output_filename):
            raise HTTPException(status_code=500, detail="Matrix puzzle building task terminated unexpectedly.")

        with open(output_filename, "r", encoding="utf-8") as out_f:
            payload_data = json.load(out_f)

        return payload_data

    except subprocess.CalledProcessError as sub_err:
        raise HTTPException(status_code=500, detail=f"Pipeline execution step failure: \u007bstr(sub_err)\u007d")
    except Exception as err:
        #raise HTTPException(status_code=500, detail=f"Internal compilation error: \u007bstr(err)\u007d")
        raise HTTPException(status_code=500, detail=f"Internal compilation error: {str(err)}")
        
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
