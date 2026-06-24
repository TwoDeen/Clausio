import sys
import os
import json
import spacy

# Load the JSON Database globally so it doesn't repeatedly read from disk
DB_PATH = os.path.join(os.path.dirname(__file__), "jlpt_grammar_database.json")
GRAMMAR_DB = {}
if os.path.exists(DB_PATH):
    with open(DB_PATH, "r", encoding="utf-8") as f:
        GRAMMAR_DB = json.load(f)
else:
    print(f"Warning: '{DB_PATH}' not found. JSON string-matching will be skipped.", file=sys.stderr)


def check_json_rules(level: str, full_text_string: str, full_lemma_string: str, text_tokens: list, lemmas: list):
    """Iterates through the JSON database for the specific JLPT level."""
    if level not in GRAMMAR_DB:
        return None
        
    for rule in GRAMMAR_DB[level]:
        pattern = rule["pattern"]
        m_type = rule["match_type"]
        
        if m_type == "text" and pattern in full_text_string:
            return level, rule["desc"]
        elif m_type == "lemma" and pattern in full_lemma_string:
            return level, rule["desc"]
        elif m_type == "text_list" and pattern in text_tokens:
            return level, rule["desc"]
        elif m_type == "lemma_list" and pattern in lemmas:
            return level, rule["desc"]
            
    return None


def analyze_sentence_grammar(doc) -> tuple:
    """
    Hybrid Analyzer: 
    1. Checks the scalable JSON database for standard string patterns.
    2. Runs deep morphological loops for complex conjugation patterns.
    """
    lemmas = [token.lemma_ for token in doc]
    pos_tags = [token.pos_ for token in doc]
    text_tokens = [token.text for token in doc]

    full_lemma_string = "".join(lemmas)
    full_text_string = "".join(text_tokens)

    # ----------------------------------------------------------------------
    # LEVEL N1
    # ----------------------------------------------------------------------
    json_match = check_json_rules("N1", full_text_string, full_lemma_string, text_tokens, lemmas)
    if json_match: return json_match

    # ----------------------------------------------------------------------
    # LEVEL N2
    # ----------------------------------------------------------------------
    json_match = check_json_rules("N2", full_text_string, full_lemma_string, text_tokens, lemmas)
    if json_match: return json_match

    # ----------------------------------------------------------------------
    # LEVEL N3
    # ----------------------------------------------------------------------
    json_match = check_json_rules("N3", full_text_string, full_lemma_string, text_tokens, lemmas)
    if json_match: return json_match

    # Complex N3 Morphology Rules (Cannot be handled by JSON safely)
    if "はず" in lemmas:
        hazu_idx = lemmas.index("はず")
        if pos_tags[hazu_idx] in ["NOUN", "PRON"]:
            return "N3", "はずだ / Strong logical expectation"
    if "ばかり" in lemmas:
        bakari_idx = lemmas.index("ばかり")
        if bakari_idx > 0 and text_tokens[bakari_idx - 1] in ["た", "だ", "つた"]:
            return "N3", "たばかり / Just completed executing an action moments ago"
    if "おわる" in lemmas or "終る" in lemmas:
        return "N3", "〜終わる / Completing the execution of a continuous action"
    if "決して" in lemmas and any(t in full_text_string for t in ["ない", "ぬ", "ません"]):
        return "N3", "決して〜ない / Absolute negation / By no means"
    if "たとえ" in lemmas and any(t in full_text_string for t in ["ても", "でも"]):
        return "N3", "たとえ〜ても / Even if a condition is met"

    # ----------------------------------------------------------------------
    # LEVEL N4
    # ----------------------------------------------------------------------
    json_match = check_json_rules("N4", full_text_string, full_lemma_string, text_tokens, lemmas)
    if json_match: return json_match

    # Complex N4 Morphology Rules
    if "おく" in lemmas and "て" in text_tokens:
        return "N4", "ておく / Performing an action in advance preparation"
    if "しまう" in lemmas and any(t in text_tokens for t in ["て", "で"]):
        return "N4", "てしまう / Regret / Definitively completed state"
    if "やすい" in lemmas and any(p == "VERB" for p in pos_tags):
        return "N4", "〜やすい / High tendency / Exceptionally easy to perform"
    if "にくい" in lemmas and any(p == "VERB" for p in pos_tags):
        return "N4", "〜にくい / Resistant / Exceptionally difficult to perform"
    if "たら" in text_tokens or "だら" in text_tokens:
        return "N4", "〜たら / Conditional connection / Past-based if-then context"

    # Deep morphological token loop (Combines N3/N4 inflection checks)
    for i, token in enumerate(doc):
        # N3 Formal stem-conjunctions (連用中止) e.g., 発達し、
        if token.pos_ == "VERB" and token.text in ["し", "り", "き", "み", "ち", "ぎ", "び", "に", "い"]:
            if i + 1 < len(doc) and doc[i+1].pos_ == "PUNCT" and doc[i+1].text in ["、", "，", ","]:
                return "N3", "連用中止 (Stem Conjunction) / Formal written 'and'"
        # N4 Potential forms (Can do: 読める, 出来る)
        if "れる" in token.lemma_ and token.pos_ == "AUX" and "受動" not in token.tag_:
            return "N4", "可能形 (Potential Form) / Possesses capability to execute"
        # N4 Causative forms (Make/Let do: させる, せる)
        if "せる" in token.lemma_ and token.pos_ == "AUX" and "使役" in token.tag_:
            return "N4", "使役形 (Causative Form) / Inducing or permitting an action"
        # N4 Passive voice markers (Was done to: 倒れる, 食べられる)
        if "れる" in token.lemma_ and token.pos_ == "AUX" and "受動" in token.tag_:
            return "N4", "受動形 (Passive Voice) / Subject undergoes action consequence"
        # N4 Volitional intentional plans (〜ようと思う)
        if token.lemma_ == "思う" and "よう" in text_tokens:
            return "N4", "意向形+と思う / Expressing personal volitional intention"

    # ----------------------------------------------------------------------
    # LEVEL N5
    # ----------------------------------------------------------------------
    json_match = check_json_rules("N5", full_text_string, full_lemma_string, text_tokens, lemmas)
    if json_match: return json_match

    # Base N5 Check
    if "いる" in lemmas and any(t in text_tokens for t in ["て", "で"]):
        return "N5", "ている / Progressive continuous state / Habitual ongoing action"
    if "ください" in lemmas or "下さる" in lemmas:
        return "N5", "てください / Courteous request directive"
    if "ます" in lemmas:
        return "N5", "ます・ました / Formal polite clausal framework"
    if "たい" in lemmas:
        return "N5", "たい / Expressing immediate desire to execute"
    if "から" in text_tokens and any(p == "VERB" for p in pos_tags):
        return "N5", "から (Conjunction) / Explaining cause / Because"

    return "N5", "Basic foundational sentence / Particle-linked base clause"


def execute_comprehensive_analysis(input_filename: str):
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
            
        doc = nlp(clean_text)
        level, rule_description = analyze_sentence_grammar(doc)
        
        entry = {
            "sentence_id": index + 1,
            "raw_text": clean_text,
            "assigned_jlpt": level,
            "detected_grammar_rule": rule_description
        }
        analyzed_payload.append(entry)

    print(f"Compiling complete analytical output to: {output_filename}")
    with open(output_filename, "w", encoding="utf-8") as json_out:
        json.dump(analyzed_payload, json_out, ensure_ascii=False, indent=4)

    # Print out summary matrix to verify change dynamics instantly
    levels = [item["assigned_jlpt"] for item in analyzed_payload]
    print("\n--- NEW RULEBASE GRAMMAR DISTRIBUTION ---")
    print(f"N1: {levels.count('N1')} sentences")
    print(f"N2: {levels.count('N2')} sentences")
    print(f"N3: {levels.count('N3')} sentences")
    print(f"N4: {levels.count('N4')} sentences")
    print(f"N5: {levels.count('N5')} sentences")
    print("------------------------------------------")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python complete_jlpt_analyzer.py <your_sentences.txt>")
    else:
        execute_comprehensive_analysis(sys.argv[1])
