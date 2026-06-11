import sys
import os
import re

def clean_and_tokenize(text: str) -> list:
    """
    Strips metadata headers and accurately merges dialogue quotes 
    with their trailing narrative descriptions into single-line sentences.
    """
    # 1. Strip out the metadata headers added during download
    if "--------------------------------------------------" in text:
        text = text.split("--------------------------------------------------", 1)[1]
    elif "--------------------" in text:
        text = text.split("--------------------", 1)[1]

    text = text.strip()

    # 2. Pre-processing string formatting
    text = re.sub(r'\r\n', '\n', text)
    
    # Bridge sentences where a line ends with a quote, but the next line immediately
    # continues with particles like と, が, を, に, も, or verbs.
    text = re.sub(r'」\n+([とがをにもの低変そはだ])', r'」\1', text)

    # 3. Splitting and Recombining Logic
    # Split text globally at periods, exclamation marks, or question marks
    raw_blocks = re.split(r'([。！？]」?)', text)
    
    sentences = []
    current_sentence = ""
    
    # Iterate through the chunks and stitch punctuation back to its sentence body
    for i in range(0, len(raw_blocks)-1, 2):
        block = raw_blocks[i].replace("\n", "").strip()
        punctuation = raw_blocks[i+1].replace("\n", "").strip()
        
        combined = block + punctuation
        
        if current_sentence:
            current_sentence += combined
        else:
            current_sentence = combined
            
        # LOOKAHEAD: Check the next index block to see if the sentence actually ends
        next_index = i + 2
        if next_index < len(raw_blocks):
            next_block = raw_blocks[next_index].strip()
            # If the next block starts with 'と' (quoting particle) or a comma, 
            # it belongs to the current sentence. Do NOT save yet, keep looping!
            if next_block.startswith('と') or next_block.startswith('、') or next_block.startswith('言ひました'):
                continue
        
        # Save the fully built sentence line
        if current_sentence:
            final_str = current_sentence.strip()
            if final_str:
                sentences.append(final_str)
            current_sentence = ""
            
    # Clean up any remaining trailing blocks
    if current_sentence:
        sentences.append(current_sentence.strip())
    elif len(raw_blocks) % 2 != 0 and raw_blocks[-1].strip():
        sentences.append(raw_blocks[-1].strip().replace("\n", ""))

    return sentences

def run_sentence_tokenizer(input_filename: str):
    if not os.path.exists(input_filename):
        print(f"Error: The file '{input_filename}' does not exist.")
        return

    base_name, _ = os.path.splitext(input_filename)
    output_filename = f"{base_name}_sentences.txt"

    with open(input_filename, "r", encoding="utf-8") as f:
        raw_story_content = f.read()

    sentence_list = clean_and_tokenize(raw_story_content)

    print(f"Writing {len(sentence_list)} perfectly joined lines to: {output_filename}")
    with open(output_filename, "w", encoding="utf-8") as f:
        for sentence in sentence_list:
            f.write(f"{sentence}\n")
            
    print("Tokenizer update successful!")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python tokenize_sentences.py <your_cleaned_story.txt>")
    else:
        target_file = sys.argv[1]
        run_sentence_tokenizer(target_file)
