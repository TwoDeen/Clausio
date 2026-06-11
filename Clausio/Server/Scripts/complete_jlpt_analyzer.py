import sys
import os
import json
import spacy

def analyze_sentence_grammar(doc) -> tuple:
    """
    Analyzes the parsed token sequence of a sentence using GiNZa/spaCy.
    Evaluates an expansive matrix of morphological rules from N1 down to N5.
    Returns: (JLPT_Level, Grammar_Pattern_Description)
    """
    lemmas = [token.lemma_ for token in doc]
    pos_tags = [token.pos_ for token in doc]
    text_tokens = [token.text for token in doc]

    full_lemma_string = "".join(lemmas)
    full_text_string = "".join(text_tokens)

    # ----------------------------------------------------------------------
    # 1. LEVEL N1: LITERARY CONJUNCTIONS & CLASSICAL EXPRESSIONS
    # ----------------------------------------------------------------------
    if "んがため" in full_lemma_string or "がために" in full_text_string:
        return "N1", "んがために / For the explicit purpose of"
    if "まじき" in full_lemma_string:
        return "N1", "まじき / Impermissible / Crucial moral restriction"
    if "極まりない" in full_lemma_string or "きわまりない" in full_lemma_string:
        return "N1", "極まりない / Extremely / Boundless state"
    if "ともなると" in full_text_string or "ともなれば" in full_text_string:
        return "N1", "ともなると / Once a condition progresses to an extreme"
    if "ずにはすまない" in full_lemma_string:
        return "N1", "ずにはすまない / Cannot avoid executing an action"
    if "を限りに" in full_text_string or "をかぎりに" in full_text_string:
        return "N1", "を限りに / Starting from / Until the very end of"
    if "が早いか" in full_lemma_string:
        return "N1", "が早いか / As soon as / Immediately after"
    if "にかたくない" in full_lemma_string or "に難くない" in full_lemma_string:
        return "N1", "にかたくない / Not difficult to (imagine/comprehend)"

    # ----------------------------------------------------------------------
    # 2. LEVEL N2: FORMAL ARGUMENTS, CONDITIONALS & SPECIAL COMPULSIONS
    # ----------------------------------------------------------------------
    if "わけにはいかない" in full_lemma_string or "わけには行かない" in full_lemma_string:
        return "N2", "わけにはいかない / Cannot afford to due to social code"
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
    if "によって" in full_text_string or "により" in full_text_string:
        return "N2", "によって / Depending on / By means of / Due to"
    if "最中に" in full_text_string or "最中だ" in full_text_string:
        return "N2", "最中に / In the middle of an ongoing action"
    if "反面" in lemmas or "半面" in lemmas:
        return "N2", "反面 / On the other hand / Contrasting aspect"
    if "つつある" in full_text_string or "つつあつ" in full_text_string:
        return "N2", "つつある / In the process of continuous change"

    # ----------------------------------------------------------------------
    # 3. LEVEL N3: EXPECTATIONS, COMPLEX MODIFIERS & MODAL ENDINGS
    # ----------------------------------------------------------------------
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
    if "うちに" in full_text_string:
        return "N3", "うちに / While a temporary condition holds true"
    if "決して" in lemmas and any(t in full_text_string for t in ["ない", "ぬ", "ません"]):
        return "N3", "決して〜ない / Absolute negation / By no means"
    if "みたいだ" in full_lemma_string or "みたい" in lemmas:
        return "N3", "みたいだ / Looks like / Resembles a state"
    if "代わりに" in full_text_string or "かわりに" in full_text_string:
        return "N3", "代わりに / In exchange for / Instead of"
    if "たとえ" in lemmas and any(t in full_text_string for t in ["ても", "でも"]):
        return "N3", "たとえ〜ても / Even if a condition is met"

    # ----------------------------------------------------------------------
    # 4. LEVEL N4: COMPLEX SUFFIX INFLECTIONS, INTENTIONS & TRANSITIONS
    # ----------------------------------------------------------------------
    if "ながら" in lemmas:
        return "N4", "ながら / Simultaneous execution / Performing two tasks at once"
        
    if "おく" in lemmas and "て" in text_tokens:
        return "N4", "ておく / Performing an action in advance preparation"
        
    if "しまう" in lemmas and any(t in text_tokens for t in ["て", "で"]):
        return "N4", "てしまう / Regret / Definitively completed state"
        
    if "やすい" in lemmas and any(p == "VERB" for p in pos_tags):
        return "N4", "〜やすい / High tendency / Exceptionally easy to perform"
        
    if "にくい" in lemmas and any(p == "VERB" for p in pos_tags):
        return "N4", "〜にくい / Resistant / Exceptionally difficult to perform"

    # Look for compound conditional junctions (e.g., 〜たら, 〜ば)
    if "たら" in text_tokens or "だら" in text_tokens:
        return "N4", "〜たら / Conditional connection / Past-based if-then context"

    # Deep morphological check for stacked functional auxiliary suffixes
    for token in doc:
        # Potential forms (Can do: 読める, 出来る)
        if "れる" in token.lemma_ and token.pos_ == "AUX" and "受動" not in token.tag_:
            return "N4", "可能形 (Potential Form) / Possesses capability to execute"
            
        # Causative forms (Make/Let do: させる, せる)
        if "せる" in token.lemma_ and token.pos_ == "AUX" and "使役" in token.tag_:
            return "N4", "使役形 (Causative Form) / Inducing or permitting an action"
            
        # Passive voice markers (Was done to: 倒れる, 食べられる)
        if "れる" in token.lemma_ and token.pos_ == "AUX" and "受動" in token.tag_:
            return "N4", "受動形 (Passive Voice) / Subject undergoes action consequence"
            
        # Volitional intentional plans (〜ようと思う)
        if token.lemma_ == "思う" and "よう" in text_tokens:
            return "N4", "意向形+と思う / Expressing personal volitional intention"

    # ----------------------------------------------------------------------
    # 5. LEVEL N5: PRIMARY PARTICLES, POLITE FORMS & CONTINUOUS ACTIONS
    # ----------------------------------------------------------------------
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
