import sys
import os
import json
import spacy

def analyze_sentence_grammar(doc) -> tuple:
    """
    Analyzes the parsed token sequence of a sentence using GiNZa/spaCy.
    Evaluates morphological structures from N1 down to N5.
    Returns: (JLPT_Level, Grammar_Pattern_Description)
    """
    # Create structural tracking lists for token attributes
    lemmas = [token.lemma_ for token in doc]
    pos_tags = [token.pos_ for token in doc]
    text_tokens = [token.text for token in doc]

    # Join sequential elements to evaluate multi-token compound blocks smoothly
    full_lemma_string = "".join(lemmas)
    full_text_string = "".join(text_tokens)

    # ----------------------------------------------------------------------
    # 1. CRITICAL HIGHEST LEVEL: N1 GRAMMAR CONDITIONS
    # ----------------------------------------------------------------------
    if "んがため" in full_lemma_string or "がために" in full_text_string:
        return "N1", "んがために / For the explicit purpose of"
    if "まじき" in full_lemma_string:
        return "N1", "まじき / Impermissible / Crucial moral restriction"
    if "極まりない" in full_lemma_string or "きわまりない" in full_lemma_string:
        return "N1", "極まりない / Extremely / Boundless state"
    if "ともなると" in full_text_string:
        return "N1", "ともなると / Once a condition progresses to..."
    if "ずにはすまない" in full_lemma_string:
        return "N1", "ずにはすまない / Cannot avoid executing an action"

    # ----------------------------------------------------------------------
    # 2. LEVEL N2: FORMAL ARGUMENTS, CONDITIONALS & COMPULSIONS
    # ----------------------------------------------------------------------
    if "わけにはいかない" in full_lemma_string or "わけには行かない" in full_lemma_string:
        return "N2", "わけにはいかない / Cannot afford to execute due to social code"
    if "にちがいない" in full_lemma_string or "に違い無い" in full_lemma_string:
        return "N2", "に違いない / Without a single shred of doubt"
    if "をめぐって" in full_lemma_string or "を巡って" in full_lemma_string:
        return "N2", "をめぐって / Concerning / Centering surrounding a debate"
    if "にかかわらず" in full_lemma_string or "に関わらず" in full_lemma_string:
        return "N2", "にかかわらず / Regardless of the condition"
    if "かねない" in full_lemma_string:
        return "N2", "かねない / Highly prone to a negative consequence"
    if "がちだ" in full_lemma_string or "がち" in lemmas:
        return "N2", "がち / Frequent / Unfavorable trend tendency"

    # ----------------------------------------------------------------------
    # 3. LEVEL N3: EXPECTATIONS, MODIFIERS & RECENT INTENTIONS
    # ----------------------------------------------------------------------
    if "はず" in lemmas:
        # Cross-verify if it functions as an expectation context noun
        hazu_idx = lemmas.index("はず")
        if pos_tags[hazu_idx] in ["NOUN", "PRON"]:
            return "N3", "はずだ / Strong logical expectation"
            
    if "ばかり" in lemmas:
        bakari_idx = lemmas.index("ばかり")
        # If preceded closely by past tense markers 'た', it implies recent action completion
        if bakari_idx > 0 and text_tokens[bakari_idx - 1] in ["た", "だ", "つた"]:
            return "N3", "たばかり / Just completed executing an action moments ago"
            
    if "おわる" in lemmas or "終る" in lemmas:
        return "N3", "〜終わる / Completing the execution of a continuous action"
    if "うちに" in full_text_string:
        return "N3", "うちに / While a temporary condition holds true"
    if "決して" in lemmas and any(t in full_text_string for t in ["ない", "ぬ", "ません"]):
        return "N3", "決して〜ない / Absolute negation / By no means"

    # ----------------------------------------------------------------------
    # 4. LEVEL N4: DISCOVERY, REGRETS & SUFFIX INFLECTIONS (Exhaustive Flags)
    # ----------------------------------------------------------------------
    # Check for the continuous execution modifier 'ながら'
    if "ながら" in lemmas:
        return "N4", "ながら / Simulataneous execution / While performing another action"
        
    # Check for the preparation modifier 'おく' (e.g., ておいた, て置く)
    if "おく" in lemmas and "て" in text_tokens:
        return "N4", "ておく / Performing an action in advance preparation"
        
    # Check for regret/completed suffix configurations (e.g., てしまう, ちまう)
    if "しまう" in lemmas and any(t in text_tokens for t in ["て", "で"]):
        return "N4", "てしまう / Regret / Definitively completed state"

    # Deep morphological structural check across active positional elements
    for token in doc:
        # Identify Potential Forms dynamically via inner verbal suffix values
        if "れる" in token.lemma_ and token.pos_ == "AUX" and "受動" not in token.tag_:
            return "N4", "可能形 (Potential Form) / Possesses the capability to execute"
            
        # Identify Causative Forms dynamically (e.g., させる, せる)
        if "せる" in token.lemma_ and token.pos_ == "AUX" and "使役" in token.tag_:
            return "N4", "使役形 (Causative Form) / Forcing or permitting an action"
            
        # Catch volitional future decisions (e.g., 〜ようと思う)
        if token.lemma_ == "思う" and "よう" in text_tokens:
            return "N4", "意向形+と思う / Expressing personal volitional intention"

    # ----------------------------------------------------------------------
    # 5. LEVEL N5: BASE COGNITIVE STRUCTURES & CONTINUOUS SYSTEM MARKERS
    # ----------------------------------------------------------------------
    if "いる" in lemmas and any(t in text_tokens for t in ["て", "で"]):
        return "N5", "ている / Progressive continuous state / Habitual ongoing action"
    if "ください" in lemmas or "下さる" in lemmas:
        return "N5", "てください / Courteous request directive"
    if "ます" in lemmas:
        return "N5", "ます・ました / Formal polite clausal framework"
    if "たい" in lemmas:
        return "N5", "たい / Expressing basic immediate desire to execute"

    # Universal structural fallback boundary
    return "N5", "Basic foundational sentence / Particle-linked base clause"


def execute_exhaustive_analysis(input_filename: str):
    if not os.path.exists(input_filename):
        print(f"Error: Target file '{input_filename}' not found.")
        return

    output_filename = f"{os.path.splitext(input_filename)[0]}_comprehensive_tagged.json"

    print("Initializing GiNZa deep language analytics framework...")
    nlp = spacy.load("ja_ginza")
    
    analyzed_payload = []

    print(f"Reading target file contents: {input_filename}")
    with open(input_filename, "r", encoding="utf-8") as f:
        lines = f.readlines()

    print(f"Processing {len(lines)} structured items across full dependency matrices...")
    for index, line in enumerate(lines):
        clean_text = line.strip()
        if not clean_text:
            continue
            
        # Pass the plain sentence line through the AI parsing engine
        doc = nlp(clean_text)
        
        # Determine the grammatical tag attributes
        level, rule_description = analyze_sentence_grammar(doc)
        
        # Build out token debugging data to help you see exactly what the engine saw
        token_debug_info = [
            {"token": t.text, "base_lemma": t.lemma_, "pos": t.pos_, "tag": t.tag_}
            for t in doc
        ]
        
        entry = {
            "sentence_id": index + 1,
            "raw_text": clean_text,
            "assigned_jlpt": level,
            "detected_grammar_rule": rule_description,
            "linguistic_tokens_metadata": token_debug_info  # Invaluable debug layer
        }
        analyzed_payload.append(entry)

    print(f"Compiling comprehensive analytical output to: {output_filename}")
    with open(output_filename, "w", encoding="utf-8") as json_out:
        json.dump(analyzed_payload, json_out, ensure_ascii=False, indent=4)

    print("\nExhaustive structural grading sequence finished successfully!")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python exhaustive_jlpt_analyzer.py <your_sentences.txt>")
    else:
        execute_exhaustive_analysis(sys.argv[1])
